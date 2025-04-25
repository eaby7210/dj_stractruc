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
from .serializers import OpportunityReadSerializer, PipelineSerializer
from .models import Opportunity, Pipeline
from .filters import OpportunityFilter
from rest_framework.pagination import PageNumberPagination


class OpportunityPagination(PageNumberPagination):
    page_size = 10  # Default page size
    page_size_query_param = "page_size"
    max_page_size = 50  # Limit max page size

class OpportunityViewSet(viewsets.ReadOnlyModelViewSet):
    pagination_class = OpportunityPagination
    queryset = Opportunity.objects.select_related("assigned_to", "pipeline", "contact").all()
    serializer_class = OpportunityReadSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = OpportunityFilter
    search_fields = [
        'name',                      # Opportunity name
        'assigned_to__first_name',
        'assigned_to__last_name',
        'pipeline__name',
        'contact__first_name',
        'contact__last_name',
    ]
    ordering_fields = ['created_at', 'opp_value', 'name']
    lookup_field = "ghl_id"
