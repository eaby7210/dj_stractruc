from core.models import CustomField, OAuthToken
import requests
from datetime import datetime


def map_to_customfield(custom_field_id, location_id):
    custom_field = CustomField.objects.get(id = custom_field_id, location_id = location_id)
    if custom_field:
        return custom_field
    else:
        custom_field = save_custom_field_to_db(custom_field_id, location_id)
        return custom_field


def save_custom_field_to_db(custom_field_id, location_id):
    token = OAuthToken.objects.filter(LocationId=location_id).first()
    
    if not token:
        print("No token found for location.")
        return None

    response = get_custom_field(location_id, custom_field_id, token.access_token)

    if response and response.get("customField"):
        data = response["customField"]
        
        custom_field, created = CustomField.objects.update_or_create(
            id=data["id"],
            defaults={
                "name": data["name"],
                "model_name": data["model"],
                "field_key": data["fieldKey"],
                "placeholder": data.get("placeholder", ""),
                "data_type": data["dataType"],
                "parent_id": data["parentId"],
                "location_id": data["locationId"],
                "date_added": datetime.fromisoformat(data["dateAdded"].replace("Z", "+00:00")),
            }
        )

        if created:
            print(f"Custom field '{custom_field.name}' created.")
        else:
            print(f"Custom field '{custom_field.name}' updated.")

        return custom_field
    else:
        print("Custom field data not found.")
        return None


def get_custom_field(location_id, field_id, access_token):

    url = f"https://services.leadconnectorhq.com/locations/{location_id}/customFields/{field_id}"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Version": "2021-07-28"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raises HTTPError for bad responses
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None
