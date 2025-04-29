import requests
from django.utils.timezone import now
from datetime import timedelta
from .models import OAuthToken, ContactCustomFieldValue
from django.conf import settings
from django.db import transaction
import requests 
from datetime import datetime
from .models import Contact, CustomField, GHLUser
import json
from django.contrib.contenttypes.models import ContentType
from django.apps import apps
from core import helpers



TOKEN_URL = 'https://services.leadconnectorhq.com/oauth/token'
LIMIT_PER_PAGE = 100
BASE_URL = 'https://services.leadconnectorhq.com'
API_VERSION = "2021-07-28"

class OAuthTokenError(Exception):
    '''Custom exeption for Oauth token-related errors'''

class OAuthServices:
    
    @staticmethod
    def get_valid_access_token_obj(location_id=None):
       
        from django.conf import settings
        if location_id:
            token_obj = OAuthToken.objects.get(LocationId=location_id)  # Assuming one OAuth record, change if one per user
        else:
            token_obj = OAuthToken.objects.first()
        if not token_obj:
            raise OAuthTokenError("OAuth token not found. Please authenticate first")
        
        if token_obj.is_expired():
            token_obj = OAuthServices.refresh_access_token(location_id)
            
        return token_obj
    
    @staticmethod
    def get_fresh_token(auth_code):
        '''Exchange authorization code for a fresh access token'''
        print("reached hereee")
        from django.conf import settings
        
        headers = {
        "Content-Type": "application/x-www-form-urlencoded"
        }
        payload = {
            'client_id': settings.CLIENT_ID,
            'client_secret' : settings.CLIENT_SECRET,
            'grant_type' : 'authorization_code',
            'code' : auth_code,
        }
        # print(payload)
        response =requests.post(TOKEN_URL,headers=headers,data=payload)
        token_data = response.json()

        
        if response.status_code == 200:
            # company_data = fetch_company_data(token_data['access_token'], token_data['locationId'])
            # print("company data:",company_data)
            print("success response")
            token_obj, created = OAuthToken.objects.update_or_create(
                LocationId=token_data["locationId"],
                defaults={
                    "access_token": token_data["access_token"],
                    "token_type": token_data["token_type"],
                    "expires_at": (now() + timedelta(seconds=token_data["expires_in"])).date(),
                    "refresh_token": token_data["refresh_token"],
                    "scope": token_data["scope"],
                    "userType": token_data["userType"],
                    "companyId": token_data["companyId"],
                    "userId": token_data["userId"],
                    
                }
            )
            return token_obj
        else:
            print("errror response")
            raise ValueError(f"Failed to get fresh access token: {token_data}")
    
    
    @staticmethod
    def refresh_access_token(location_id):
        """
        Refresh the access token using the refresh token.
        """
        
        token_obj = OAuthToken.objects.get(LocationId=location_id)
        payload = {
            'grant_type': 'refresh_token',
            'client_id': settings.CLIENT_ID,
            'client_secret': settings.CLIENT_SECRET,
            'refresh_token': token_obj.refresh_token
        }
        print(f"payload: {payload}")
        response = requests.post(TOKEN_URL, data=payload)

        if response.status_code != 200:
            raise OAuthTokenError(f"Failed to refresh access token: {response.json()}")

        new_tokens = response.json()
        print("New Tokens:", new_tokens)

        token_obj.access_token = new_tokens.get("access_token")
        token_obj.refresh_token = new_tokens.get("refresh_token")
        token_obj.expires_at = now() + timedelta(seconds=new_tokens.get("expires_in"))

        token_obj.scope = new_tokens.get("scope")
        token_obj.userType = new_tokens.get("userType")
        token_obj.companyId = new_tokens.get("companyId")
        # token_obj.LocationId = new_tokens.get("locationId")
        token_obj.userId = new_tokens.get("userId")

        token_obj.save()
        return token_obj


class ContactServiceError(Exception):
    "Exeption for Contact api's"
    pass

class ContactServices:
    
    @staticmethod
    def get_contacts(location_id,query=None, url=None, limit=LIMIT_PER_PAGE):
        """
        Fetch contacts from GoHighLevel API with given parameters.
        """
        token_obj = OAuthServices.get_valid_access_token_obj(location_id)
        headers = {
            "Authorization": f"Bearer {token_obj.access_token}",
            "Content-Type": "application/json",
            "Version": API_VERSION,
        }

        if url:
            response = requests.get(url, headers=headers)
        else:
            url = f"{BASE_URL}/contacts/"
            params = {
                "locationId": token_obj.LocationId,
                "limit": limit,
            }
            if query:
                params["query"] = query
            response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            return response.json()
        else:
            raise ContactServiceError(f"API request failed: {response.status_code}")

    @staticmethod
    def push_contact(contact_obj :Contact, data):
        token_obj = OAuthServices.get_valid_access_token_obj(contact_obj.location_id)
        headers = {
            "Authorization": f"Bearer {token_obj.access_token}",
            "Content-Type": "application/json",
            "Version": API_VERSION,
        }

        url = f"{BASE_URL}/contacts/{contact_obj.id}"
      

        response = requests.put(url, headers=headers, json=data)

        if response.status_code == 200:
            return response.json()
        else:
            raise ContactServiceError(f"API request failed: {response.status_code}")

    
    @staticmethod
    def pull_contacts(query=None):
        """
        Fetch all contacts using nextPageURL-based pagination and save them to the database.
        """
        imported_contacts_summary = []
        location_ids = list(OAuthToken.objects.values_list('LocationId', flat=True))
        for location_id in location_ids:
            tokenobj :OAuthToken = OAuthServices.get_valid_access_token_obj(location_id)
            all_contacts = []
            url = None
            i = 0

            while True:
                response_data = ContactServices.get_contacts(location_id=tokenobj.LocationId,query=query, url=url)
                contacts = response_data.get("contacts", [])
                all_contacts.extend(contacts)

                # print(json.dumps(contacts,indent=4))
                print(len(all_contacts), i, end='\n\n')
                if not response_data.get("meta", {}).get("nextPageURL"):
                    break  # No next page

                url = response_data["meta"]["nextPageURL"]
                i += 1

            ContactServices._save_contacts(all_contacts)
            imported_contacts_summary.append(f"{location_id}: Imported {len(all_contacts)} contacts")
        return imported_contacts_summary
        

    @staticmethod
    def _save_contacts(contacts):
        """
        Bulk save contacts to the database along with their custom fields.
        """
        unique_contacts = {contact["id"]: contact for contact in contacts}.values()  # Remove duplicates

        contact_objects = []
        custom_field_values = []

        # Step 1: Prepare Contact objects
        for contact in unique_contacts:
            contact_obj = Contact(
                id=contact["id"],
                first_name=contact.get("firstName", ""),
                last_name=contact.get("lastName", ""),
                email=contact.get("email", ""),
                phone=contact.get("phone", ""),
                country=contact.get("country", ""),
                location_id=contact.get("locationId", ""),
                type=contact.get("type", "lead"),
                date_added=datetime.fromisoformat(contact["dateAdded"].replace("Z", "+00:00")) if contact.get("dateAdded") else None,
                date_updated=datetime.fromisoformat(contact["dateUpdated"].replace("Z", "+00:00")) if contact.get("dateUpdated") else None,
                dnd=contact.get("dnd", False),
            )
            contact_objects.append(contact_obj)

        # Step 2: Bulk insert or update contacts
        Contact.objects.bulk_create(
            contact_objects,
            update_conflicts=True,
            unique_fields=["id"],
            update_fields=[
                "first_name", "last_name", "email", "phone", "country", "location_id", "type",
                "date_added", "date_updated", "dnd"
            ],
        )

        # Step 3: Prepare CustomFieldValues
        for contact in unique_contacts:
            custom_fields_data = contact.get("customFields", [])
            print(json.dumps(custom_fields_data, indent=4))
            if custom_fields_data and isinstance(custom_fields_data, list):
                for field in custom_fields_data:
                    custom_field_id = field.get("id")
                    field_value = (
                        field.get("fieldValueString") or
                        field.get("fieldValueArray") or
                        field.get("fieldValue") or
                        field.get("value")
                    )

                    if not custom_field_id or field_value is None:
                        continue  # Skip invalid fields

                    try:
                        custom_field = CustomField.objects.get(id=custom_field_id)
                    except CustomField.DoesNotExist:
                        print(f"CustomField with id {custom_field_id} not found, skipping...")
                        continue

                    custom_field_values.append(
                        ContactCustomFieldValue(
                            contact_id=contact["id"],  # using id to avoid hitting DB again
                            custom_field=custom_field,
                            value=field_value,
                        )
                    )

        # Step 4: Bulk insert custom field values (upsert manually)
        for cfv in custom_field_values:
            ContactCustomFieldValue.objects.update_or_create(
                contact_id=cfv.contact_id,
                custom_field=cfv.custom_field,
                defaults={"value": cfv.value}
            )
            
    @staticmethod
    def add_customfields( data, locatioId):
        cf_dict={}
        if data and locatioId:
            for cf in data:
                cf_obj = helpers.map_to_customfield(cf["id"],locatioId)
                cf_dict[cf_obj.name.lower()]=cf["value"]
        # print("added custom fields: ", cf_dict)     
        return cf_dict

class CustomfieldServices:

    @staticmethod
    def get_customfields(location_id, model=None):
        """
        Fetch custom fields from GoHighLevel API for a specific location_id.
        """
        model = model or "all"
        print(f"getting custom fields of {model}")
        token_obj = OAuthServices.get_valid_access_token_obj(location_id)
        headers = {
            "Authorization": f"Bearer {token_obj.access_token}",
            "Content-Type": "application/json",
            "Version": API_VERSION,
        }

        url = f"{BASE_URL}/locations/{token_obj.LocationId}/customFields"
        params = {
            "model": model,
        }

        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            return response.json()
        else:
            raise ContactServiceError(f"API request failed: {response.status_code}")

    @staticmethod
    def pull_customfields(model):
        """
        Pull custom fields for all locations and save them.
        """
        location_ids = OAuthToken.objects.values_list('LocationId', flat=True)
        import_summary = []

        for location_id in location_ids:
            try:
                response_data = CustomfieldServices.get_customfields(location_id=location_id, model=model)
                custom_fields = response_data.get("customFields", [])
                CustomfieldServices._save_customfields(custom_fields)
                import_summary.append(f"{location_id}: Imported {len(custom_fields)} custom fields")
            except ContactServiceError as e:
                import_summary.append(f"{location_id}: Failed to import custom fields - {str(e)}")

        return import_summary

    @staticmethod
    def _save_customfields(fields):
        """
        Save or update custom fields in the database.
        """
        for field in fields:
            CustomField.objects.update_or_create(
                id=field["id"],
                defaults={
                    "name": field["name"],
                    "model_name": field["model"],
                    "field_key": field["fieldKey"],
                    "placeholder": field.get("placeholder", ""),
                    "data_type": field["dataType"],
                    "parent_id": field["parentId"],
                    "location_id": field["locationId"],
                    "date_added": datetime.fromisoformat(field["dateAdded"].replace("Z", "+00:00")),
                }
            )

class UserServicesError(Exception):
    "Exeption for Contact api's"
    pass


class UserServices:
    
    @staticmethod
    def get_users(limit=LIMIT_PER_PAGE):
        token_obj = OAuthServices.get_valid_access_token_obj()
        headers = {
            "Authorization": f"Bearer {token_obj.access_token}",
            "Version": API_VERSION,
        }

       
        url = f"{BASE_URL}/users/"
        params = {
            # "limit": limit,
            # "companyId":token_obj.companyId
            "locationId":token_obj.LocationId
            
        }
        response = requests.get(url, headers=headers, params=params)
        print(json.dumps(response.json(), indent=4))
        if response.status_code == 200:
            return response.json()
        else:
            raise UserServicesError(f"API request failed: {response.status_code}")

    @staticmethod
    @transaction.atomic
    def pull_users():
        data = UserServices.get_users()
        UserServices.save_users(data)
        return data.get("users", [])

    @staticmethod
    @transaction.atomic
    def save_users(data):
        for user in data.get("users", []):
            GHLUser.objects.update_or_create(
                id=user["id"],
                defaults={
                    "first_name": user.get("firstName"),
                    "last_name": user.get("lastName"),
                    "email": user.get("email"),
                    "phone": user.get("phone"),
                    "role_type": user.get("roles", {}).get("type"),
                    "role": user.get("roles", {}).get("role"),
                }
            )

def safe_int(val):
    try:
        return int(val)
    except (TypeError, ValueError):
        return None
    


def fetch_company_data(token, locationID):
    url = f"https://services.leadconnectorhq.com/companies/{locationID}"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
        "Version": "2021-07-28"
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch company data. Status code: {response.status_code}")
        print(f"Response: {response.text}")
        return None
    
