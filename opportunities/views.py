from django.apps import apps
from rest_framework.views import APIView
from django.utils.dateparse import parse_datetime
from datetime import datetime, timezone, timedelta
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.response import Response
from rest_framework import viewsets,status
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from core.services import ContactServices
from .services import PipelineServices
from .serializers import OpportunitySerializer, PipelineSerializer
from .models import Opportunity, Pipeline




class OpportunityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Opportunity.objects.all()
    serializer_class = OpportunitySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filter_fields = ['status']
    search_fields = ['ghl_id', 'name']
    lookup_field = "ghl_id"
    

