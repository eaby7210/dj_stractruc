from django.apps import apps
from rest_framework.views import APIView
from django.utils.dateparse import parse_datetime
from datetime import datetime, timezone, timedelta
from django.db import transaction
from collections import defaultdict
from decimal import Decimal
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.response import Response
from rest_framework import viewsets,status
from rest_framework.generics import GenericAPIView
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum,Func,F, Count,Count, Q, OuterRef,CharField, Subquery, Value as V
from django.db.models.functions import Coalesce
from core.services import ContactServices
from core.models import CustomField
from .services import PipelineServices
from .serializers import (
    OpportunityReadSerializer, PipelineSerializer,
    PipelineStageSerializer
    )
from .models import Opportunity, Pipeline, PipelineStage, OpportunityCustomFieldValue
from .filters import OpportunityFilter, PipelineStagesFilter, PipelineFilter
from rest_framework.pagination import PageNumberPagination


class OpportunityPagination(PageNumberPagination):
    page_size = 10  
    page_size_query_param = "page_size"
    max_page_size = 50  

class OpportunityDashView(GenericAPIView):
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
    
    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        open_queryset = queryset.filter(status='open')
        closed_queryset = queryset.exclude(status='open')

        # total_value_by_status = queryset.values('status').annotate(total_value=Sum('opp_value'))

        amount_closed = closed_queryset.aggregate(total=Sum('opp_value'))['total'] or 0
        amount_open = open_queryset.aggregate(total=Sum('opp_value'))['total'] or 0

        open_ops_count = open_queryset.count()
        closed_ops_count = closed_queryset.count()
        CUSTOM_FIELD_KEY = 'opportunity.chances_of_closing_the_deal'
        
        try:
            custom_field = CustomField.objects.get(field_key=CUSTOM_FIELD_KEY)
        except CustomField.DoesNotExist:
            chance_counts = []
        else:

            class StripQuotes(Func):
                function = 'REPLACE'
                template = "%(function)s(%(expressions)s, '\"', '')"
                output_field = CharField()

            # Subquery stays the same
            subquery = OpportunityCustomFieldValue.objects.filter(
                opportunity=OuterRef('pk'),
                custom_field=custom_field
            ).values('value')[:1]

            # Annotate and clean the string value
            annotated_queryset = queryset.annotate(
                raw_chances_value=Coalesce(Subquery(subquery), V('Unknown'), output_field=CharField()),
                chances_value=StripQuotes(F('raw_chances_value'))
            )
            
            source_cfvs = OpportunityCustomFieldValue.objects.filter(
                    opportunity__in=queryset,
                    custom_field__field_key="opportunity.opportunity_source"
                ).select_related('opportunity')

            # Dictionary to hold aggregation results
            source_data = defaultdict(lambda: {"count": 0, "total_value": Decimal('0')})

            # Process each value manually
            for cfv in source_cfvs:
                source_list = cfv.value if isinstance(cfv.value, list) else []
                for source in source_list:
                    if source:
                        source_data[source]["count"] += 1
                        source_data[source]["total_value"] += cfv.opportunity.opp_value or 0

            # Calculate average values
            for source in source_data:
                count = source_data[source]["count"]
                total = source_data[source]["total_value"]
                source_data[source]["average_value"] = total / count if count else 0

            # Convert to list format for response
            opp_source_stats = [
                {
                    "source": source,
                    "count": data["count"],
                    "total_value": float(data["total_value"]),
                    "average_value": float(data["average_value"])
                }
                for source, data in source_data.items()
            ]
            # Count grouped by that annotated field
            chance_counts = (
                annotated_queryset.values('chances_value')
                .annotate(count=Count('ghl_id'))
                .order_by('chances_value')
            )

        data = {
            'amount_closed': amount_closed,
            'amount_open': amount_open,
            'open_ops_count': open_ops_count,
            'closed_ops_count': closed_ops_count,
            'chances':chance_counts,
            'opp_source':opp_source_stats

        }

        return Response(data)

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

class PipelineViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Pipeline.objects.all().prefetch_related('stages')
    serializer_class = PipelineSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = PipelineFilter
    search_fields = [
        'name'
    ]
    ordering_fields = ['date_added']

class PipelineStageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PipelineStage.objects.select_related('pipeline')
    serializer_class = PipelineStageSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = PipelineStagesFilter
    search_fields = [
        'name'
    ]
    ordering_fields = ['position']
