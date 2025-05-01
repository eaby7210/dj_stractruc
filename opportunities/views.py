from django.apps import apps
from rest_framework.views import APIView
from django.utils.dateparse import parse_datetime
from datetime import datetime, timezone, timedelta
from django.db import transaction
from collections import defaultdict,OrderedDict
from django.db.models.functions import TruncDate
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
    # pagination_class = OpportunityPagination
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
    
    def get_queryset(self):
        return super().get_queryset()

    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # Total opportunity amount and count
        total_count = queryset.count()
        amout_total = queryset.aggregate(total=Sum('opp_value'))['total'] or 0

        # Split into open/closed once for reuse
        open_qs = queryset.filter(status='open')
        closed_qs = queryset.exclude(status='open')

        # Amount and count breakdown
        amount_open = open_qs.aggregate(total=Sum('opp_value'))['total'] or 0
        amount_closed = closed_qs.aggregate(total=Sum('opp_value'))['total'] or 0
        open_ops_count = open_qs.count()
        closed_ops_count = closed_qs.count()

        # GRAPH: Daily total of open/closed opportunity value
        aggregated_by_date = (
            queryset
            .annotate(date=TruncDate('created_at'))
            .values('date', 'status')
            .annotate(total=Sum('opp_value'), count=Count('ghl_id'))
            .order_by('date')
        )

        date_set = sorted({entry['date'] for entry in aggregated_by_date})
        open_amounts = OrderedDict((date, 0) for date in date_set)
        closed_amounts = OrderedDict((date, 0) for date in date_set)
        
        open_counts = OrderedDict((date, 0) for date in date_set)
        closed_counts = OrderedDict((date, 0) for date in date_set)

        for entry in aggregated_by_date:
            date = entry['date']
            amount = float(entry['total'] or 0)
            count = entry['count'] or 0

            if entry['status'] == 'open':
                open_amounts[date] += amount
                open_counts[date] += count
            else:
                closed_amounts[date] += amount
                closed_counts[date] += count

        graph_data = {
            "labels": [d.strftime('%Y-%m-%d') for d in date_set],
            "open": list(open_amounts.values()),
            "closed": list(closed_amounts.values()),
            "open_counts": list(open_counts.values()),
            "closed_counts": list(closed_counts.values())
        }

        # CHANCE OF CLOSING FIELD
        CUSTOM_FIELD_KEY = 'opportunity.chances_of_closing_the_deal'
        try:
            custom_field = CustomField.objects.get(field_key=CUSTOM_FIELD_KEY)

            class StripQuotes(Func):
                function = 'REPLACE'
                template = "%(function)s(%(expressions)s, '\"', '')"
                output_field = CharField()

            subquery = OpportunityCustomFieldValue.objects.filter(
                opportunity=OuterRef('pk'),
                custom_field=custom_field
            ).values('value')[:1]

            annotated = queryset.annotate(
                raw_chances_value=Coalesce(Subquery(subquery), V('Unknown'), output_field=CharField()),
                chances_value=StripQuotes(F('raw_chances_value'))
            )

            chance_counts = (
                annotated.values('chances_value')
                .annotate(count=Count('ghl_id'))
                .order_by('chances_value')
            )
        except CustomField.DoesNotExist:
            chance_counts = []

        user_aggregation = (
            queryset
            .values('assigned_to__id', 'assigned_to__first_name', 'assigned_to__last_name')
            .annotate(
                total_opps=Count('ghl_id'),
                total_value=Sum('opp_value'),
            )
            .order_by( '-total_value', '-total_opps')  # Optional: sort by most opportunities
        )

        assigned_user_stats = [
            {
                "user_id": entry["assigned_to__id"],
                "user_name": f"{entry['assigned_to__first_name']} {entry['assigned_to__last_name']}".strip(),
                "total_opps": entry["total_opps"],
                "total_value": float(entry["total_value"] or 0),
            }
            for entry in user_aggregation if entry["assigned_to__id"]  # Skip unassigned
        ]       
        
        # OPPORTUNITY SOURCE FIELD AGGREGATION
        source_data = defaultdict(lambda: {"count": 0, "total_value": Decimal('0')})
        source_cfvs = OpportunityCustomFieldValue.objects.filter(
            opportunity__in=queryset,
            custom_field__field_key="opportunity.opportunity_source"
        ).select_related('opportunity')

        for cfv in source_cfvs:
            sources = cfv.value if isinstance(cfv.value, list) else []
            for source in sources:
                if source:
                    source_data[source]["count"] += 1
                    source_data[source]["total_value"] += cfv.opportunity.opp_value or 0

        opp_source_stats = [
            {
                "source": source,
                "count": data["count"],
                "total_value": float(data["total_value"]),
                "average_value": float(data["total_value"] / data["count"]) if data["count"] else 0
            }
            for source, data in source_data.items()
        ]

        # FINAL RESPONSE
        data = {
            'amout_total': amout_total,
            'total_count': total_count,
            'amount_closed': amount_closed,
            'amount_open': amount_open,
            'open_ops_count': open_ops_count,
            'closed_ops_count': closed_ops_count,
            'chances': chance_counts,
            'opp_source': opp_source_stats,
            'graph_data': graph_data,
            'assigned_user_stats':assigned_user_stats
        }

        return Response(data)



class OpportunityViewSet(viewsets.ReadOnlyModelViewSet):
    pagination_class = OpportunityPagination
    queryset = Opportunity.objects.select_related("assigned_to", "pipeline", "contact").prefetch_related("custom_field_values").all().order_by('-created_at')
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
