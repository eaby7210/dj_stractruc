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
from .filters import ContactFilter
from .services import ContactServices
from opportunities.services import PipelineServices
Pipeline= apps.get_model('opportunities', 'Pipeline')
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
class ContactViewSet(viewsets.ModelViewSet):
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
    queryset = GHLUser.objects.all().order_by('first_name')
    serializer_class = GHLUserSerializer
    lookup_field = 'id'
    filter_backends = [SearchFilter]
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


            # signature = request.headers.get("x-wh-signature")  To verify signature
            # if not self.verify_signature(payload, signature, timestamp):   
            #     return Response({"error": "Invalid Signature or Expired timestamp"})

            ghl_id = data.get("id")
            name = data.get("name")
            pipeline_id = data.get("pipelineId")
            contact_id = data.get("contactId")
            status_value = data.get("status")
            created_at = data.get("dateAdded")
            event_type = data.get("event_type")
            created_at_dt = parse_datetime(created_at)
            created_at_dt = created_at_dt.replace(tzinfo=timezone.utc)
            
            if event_type == "ContactCreate":
                self.create_contact(data)
            elif event_type == "ContactDelete":
                self.delete_contact(data)
            elif event_type == "ContactUpdate":
                self.update_contact(data)
            # elif event_type == "ContactDndUpdate":
            #     self.update_contact_dnd(data)
            # elif event_type == "ContactTagUpdate":
            #     self.update_contact_tags(data)
          
            if all([ghl_id, name, pipeline_id, status_value]):

                with transaction.atomic():  # Prevent database locking issues
                    # Log the webhook ID to prevent duplicate processing
                    WebhookLog.objects.create(webhook_id=webhook_id)

                    # Get or pull the pipeline
                    pipeline = Pipeline.objects.filter(ghl_id=pipeline_id).first()
                    if not pipeline:
                        PipelineServices.pull_pipelines()
                        pipeline = Pipeline.objects.filter(ghl_id=pipeline_id).first()
                        if not pipeline:
                            return Response({"error": "Pipeline not found"}, status=status.HTTP_400_BAD_REQUEST)

                    # Get or create the contact
                    
                    contact = None
                    if contact_id:
                        contact = Contact.objects.filter(id=contact_id).first()
                        if not contact:
                            contact_data = ContactServices.retrieve_contact(contact_id)
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
                            "status": status_value,
                            "created_at": created_at_dt,
                        },
                    )
                print(f"Opportunity {name} processed")
            return Response({"message": "Opportunity processed", "created": created}, status=status.HTTP_200_OK)

     


            
        except Exception as e:
            print(f"error: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        
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


