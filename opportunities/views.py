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
from django.db.models import Sum, Count
from core.services import ContactServices
from .services import PipelineServices
from .serializers import OpportunityReadSerializer, PipelineSerializer
from .models import Opportunity, Pipeline
from .filters import OpportunityFilter
from rest_framework.pagination import PageNumberPagination


class OpportunityPagination(PageNumberPagination):
    page_size = 10  
    page_size_query_param = "page_size"
    max_page_size = 50  

class OpportunityViewSet(viewsets.ReadOnlyModelViewSet):
    pagination_class = OpportunityPagination
    queryset = Opportunity.objects.select_related("assigned_to", "pipeline", "contact").prefetch_related("custom_field_values").all()
    serializer_class = OpportunityReadSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = OpportunityFilter
    search_fields = [
        'name',                     
        'assigned_to__first_name',
        'assigned_to__last_name',
        'pipeline__name',
        'contact__first_name',
        'contact__last_name',
    ]
    ordering_fields = ['created_at', 'opp_value', 'name']
    lookup_field = "ghl_id"
    
    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        
        queryset = self.filter_queryset(self.get_queryset())
        
        open_queryset = queryset.filter(status='open')
        closed_queryset = queryset.exclude(status='open')

        total_value_by_status = queryset.values('status').annotate(total_value=Sum('opp_value'))

        amount_closed = closed_queryset.aggregate(total=Sum('opp_value'))['total'] or 0
        amount_open = open_queryset.aggregate(total=Sum('opp_value'))['total'] or 0

        open_ops_count = open_queryset.count()
        closed_ops_count = closed_queryset.count()
        
        # total_value_by_status = queryset.values('status').annotate(total_value=Sum('opp_value'))
        # status_wise_totals = {item['status']: item['total_value'] or 0 for item in total_value_by_status}


        response.data['aggregations'] = {
            'amount_closed': amount_closed,
            'amount_open': amount_open,
            'open_ops_count': open_ops_count,
            'closed_ops_count': closed_ops_count,
            # 'total_value_by_status': status_wise_totals,
        }
        
        return response