import json
import time
import base64
import logging
from django.apps import apps
from django.db import transaction
from django.utils.timezone import now
from rest_framework.views import APIView
from rest_framework import viewsets, status
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.pagination import PageNumberPagination
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from datetime import datetime, timezone, timedelta
# from cryptography.hazmat.primitives.asymmetric import padding
# from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from .models import Contact, WebhookLog, GHLUser
from .serializers import (
    ContactSerializer,ContactWithOpportunitiesSerializer,
    GHLUserSerializer
    )
from .filters import ContactFilter, GHLuserFilter
from .services import ContactServices, UserServices
from opportunities.services import PipelineServices
Pipeline= apps.get_model('opportunities', 'Pipeline')
PipelineStage= apps.get_model('opportunities', 'PipelineStage')
Opportunity= apps.get_model('opportunities', 'Opportunity')
WebhookLog = apps.get_model('core', 'WebhookLog')

PUBLIC_KEY='''-----BEGIN PUBLIC KEY-----
MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAokvo/r9tVgcfZ5DysOSC
Frm602qYV0MaAiNnX9O8KxMbiyRKWeL9JpCpVpt4XHIcBOK4u3cLSqJGOLaPuXw6
dO0t6Q/ZVdAV5Phz+ZtzPL16iCGeK9po6D6JHBpbi989mmzMryUnQJezlYJ3DVfB
csedpinheNnyYeFXolrJvcsjDtfAeRx5ByHQmTnSdFUzuAnC9/GepgLT9SM4nCpv
uxmZMxrJt5Rw+VUaQ9B8JSvbMPpez4peKaJPZHBbU3OdeCVx5klVXXZQGNHOs8gF
3kvoV5rTnXV0IknLBXlcKKAQLZcY/Q9rG6Ifi9c+5vqlvHPCUJFT5XUGG5RKgOKU
J062fRtN+rLYZUV+BjafxQauvC8wSWeYja63VSUruvmNj8xkx2zE/Juc+yjLjTXp
IocmaiFeAO6fUtNjDeFVkhf5LNb59vECyrHD2SQIrhgXpO4Q3dVNA5rw576PwTzN
h/AMfHKIjE4xQA1SZuYJmNnmVZLIZBlQAF9Ntd03rfadZ+yDiOXCCs9FkHibELhC
HULgCsnuDJHcrGNd5/Ddm5hxGQ0ASitgHeMZ0kcIOwKDOzOU53lDza6/Y09T7sYJ
PQe7z0cvj7aE4B+Ax1ZoZGPzpJlZtGXCsu9aTEGEnKzmsFqwcSsnw3JB31IGKAyk
T1hhTiaCeIY/OwwwNUY2yvcCAwEAAQ==
-----END PUBLIC KEY-----'''

# Create your views here.
logger = logging.getLogger(__name__)
class ContactPagination(PageNumberPagination):
    page_size = 10  # Default page size
    page_size_query_param = "page_size"
    max_page_size = 50  # Limit max page size

# Contact ViewSet
class ContactViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Contact.objects.all()
    pagination_class = ContactPagination  
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ContactFilter
    search_fields = ["first_name", "last_name", "email","id"]    

    def get_serializer_class(self):
        if self.action == 'list':
            return ContactSerializer
        elif self.action == 'retrieve':
            return ContactWithOpportunitiesSerializer
        return ContactSerializer




class GHLUserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GHLUser.objects.all().order_by('first_name', 'last_name')
    serializer_class = GHLUserSerializer
    lookup_field = 'id'
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = GHLuserFilter
    search_fields = ['first_name', 'last_name', 'email']

@method_decorator(csrf_exempt, name='dispatch')
class WebhookView(APIView):
    """
    Handles incoming webhook events from GoHighLevel.
    """

    def verify_signature(self, signature, timestamp):
        """Verify webhook signature"""
        if not signature or not timestamp:
            return False
        
    def post(self, request):
        try:
            data = request.data
            webhook_id = data.get("webhookId")  
            print(f"Received webhook data: {json.dumps(data, indent=2)}")
            if not webhook_id:
                print("Missing webhook ID")
                return Response({"error": "Missing webhook ID"}, status=status.HTTP_400_BAD_REQUEST)
            
            if WebhookLog.objects.filter(webhook_id=webhook_id).exists():
                print("Duplicate webhook ID")
                return Response({"error": "Duplicate webhook ID"}, status=status.HTTP_400_BAD_REQUEST)

            
            timestamp_at = data.get("timestamp")
            if not timestamp_at:
                print("Missing timestamp")
                return Response({"error": "Missing timestamp"}, status=status.HTTP_400_BAD_REQUEST)
            
            timestamp_at_dt = parse_datetime(timestamp_at)
            if not timestamp_at_dt:
                return Response({"error": "Invalid timestamp format"}, status=status.HTTP_400_BAD_REQUEST)

            timestamp_at_dt = timestamp_at_dt.replace(tzinfo=timezone.utc)
            time_difference = datetime.now(timezone.utc) - timestamp_at_dt
            if time_difference > timedelta(minutes=5):
                return Response({"error": "Webhook request is too old"}, status=status.HTTP_400_BAD_REQUEST)

            WebhookLog.objects.create(webhook_id=webhook_id)
            # signature = request.headers.get("x-wh-signature")  To verify signature
            # if not self.verify_signature(payload, signature, timestamp):   
            #     return Response({"error": "Invalid Signature or Expired timestamp"})
            event_type = data.get("type")
            if event_type == "ContactCreate":
                self.create_contact(data)
            elif event_type == "ContactDelete":
                self.delete_contact(data)
            elif event_type == "ContactUpdate":
                self.update_contact(data)
            elif event_type in ["OpportunityCreate", "OpportunityUpdate"]:
                self.create_or_update_opportunity(data)
            elif event_type == "OpportunityDelete":
                self.delete_opportunity(data)
            
            
            
            # elif event_type == "ContactDndUpdate":
            #     self.update_contact_dnd(data)
            # elif event_type == "ContactTagUpdate":
            #     self.update_contact_tags(data)
            msg ={"message": f"Webhook processed {event_type}"}
            print(msg)
            return Response(msg, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"error: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def create_or_update_opportunity(self, data):
        ghl_id = data.get("id")
        name = data.get("name")
        pipeline_id = data.get("pipelineId")
        contact_id = data.get("contactId")
        status_value = data.get("status")
        created_at = data.get("dateAdded")
        assigned_to = data.get("assignedTo")
        opp_value = data.get("monetaryValue")
        stage_id = data.get("pipelineStageId")
        updated_at = data.get("timestamp")
        updated_at = parse_datetime(updated_at).replace(tzinfo=timezone.utc) if updated_at else now() # type: ignore
        
        created_at_dt = parse_datetime(created_at)
        created_at_dt = created_at_dt.replace(tzinfo=timezone.utc) if created_at_dt else now()
        
        created =False
        if all([ghl_id, name, pipeline_id, status_value]):
            
            with transaction.atomic():  # Prevent database locking issues
                # Log the webhook ID to prevent duplicate processing
                # Get or pull the pipeline
                pipeline = Pipeline.objects.filter(ghl_id=pipeline_id).first()
                if not pipeline:
                    PipelineServices.pull_pipelines()
                    pipeline = Pipeline.objects.filter(ghl_id=pipeline_id).first()
                    if not pipeline:
                        return Response({"error": "Pipeline not found"}, status=status.HTTP_400_BAD_REQUEST)

                assigned = GHLUser.objects.filter(id=assigned_to).first()
                if not assigned:
                    UserServices.pull_users()
                    assigned = GHLUser.objects.filter(id=assigned_to).first()
                    if not assigned:
                        return Response({"error": "Pipeline not found"}, status=status.HTTP_400_BAD_REQUEST)
                
                stage = PipelineStage.objects.filter(id=stage_id).first()
                if not stage:
                    PipelineServices.pull_pipelines()
                    stage = PipelineStage.objects.filter(id=stage_id).first()
                    if not stage:
                        return Response({"error": "Pipeline not found"}, status=status.HTTP_400_BAD_REQUEST)
                    
                
                contact = None
                if contact_id:
                    contact = Contact.objects.filter(id=contact_id).first()
                    if not contact:
                        contact_data = ContactServices.retrieve_contact(contact_id, location_id=pipeline.LocationId) # type: ignore
                        if contact_data:
                            contact = Contact.objects.create(
                                id=contact_data.get("id"),
                                first_name=contact_data.get("firstName", ""),
                                last_name=contact_data.get("lastName", ""),
                                email=contact_data.get("email", ""),
                                phone=contact_data.get("phone", ""),
                                country=contact_data.get("country", ""),
                                location_id=contact_data.get("locationId", ""),
                                type=contact_data.get("type", "lead"),
                                date_added=parse_datetime(contact_data.get("dateAdded")),
                                date_updated=parse_datetime(contact_data.get("dateUpdated")),
                                dnd=contact_data.get("dnd", False),
                            )

                # Create or update the Opportunity
                opportunity, created = Opportunity.objects.update_or_create(
                    ghl_id=ghl_id,
                    defaults={
                        "name": name,
                        "pipeline": pipeline,
                        "contact": contact,
                        "assigned_to":assigned,
                        "status": status_value,
                        "created_at": created_at_dt,
                        "opp_value":opp_value,
                        "updated_at":updated_at,
                        "stage":stage
                    },
                )
            print(f"Opportunity {name} processed")
        
        return created
    
    def delete_opportunity(self, data):
        ghl_id = data.get("id")
        Opportunity.objects.filter(ghl_id=ghl_id).delete()
        
        
    def create_contact(self, data):
        """ Creates a new contact """
        Contact.objects.create(
            id=data["id"],
            first_name=data.get("firstName", ""),
            last_name=data.get("lastName", ""),
            email=data.get("email", ""),
            phone=data.get("phone", ""),
        )
    
    def update_contact(self, data):
        """ Updates a contact """
        contact = Contact.objects.filter(id=data["id"]).first()
        print(f"found contact {contact}")
        if contact:
            contact.first_name = data.get("firstName", contact.first_name)
            contact.last_name = data.get("lastName", contact.last_name)
            contact.email = data.get("email", contact.email)
            contact.phone = data.get("phone", contact.phone)
            contact.save()
            logger.info(f"Updated contact: {data['id']}")
        else:
            logger.warning(f"Contact {data['id']} not found for update")

    def delete_contact(self, data):
        """ Deletes a contact """
        Contact.objects.filter(id=data["id"]).delete()


