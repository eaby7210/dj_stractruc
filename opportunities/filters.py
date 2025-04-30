
from django.db.models import Q
from django.utils import timezone
from django_filters import widgets
from django_filters.rest_framework import filters, FilterSet
from .models import Opportunity, PipelineStage, Pipeline,OpportunityCustomFieldValue
from core.models import GHLUser, Contact


def get_chances_of_closing_choices():
    
    field_key = 'opportunity.chances_of_closing_the_deal'
    values_qs = OpportunityCustomFieldValue.objects.filter(
        custom_field__field_key=field_key
    ).exclude(value__isnull=True).values_list('value', flat=True).distinct()

    choices = [(v, v) for v in values_qs if v is not None]

    choices.append(('null', 'No Value'))
    return choices


class OpportunityFilter(FilterSet):
    FISCAL_PERIOD_CHOICES = (
        ('Q1', 'Q1 (Feb - Apr)'),
        ('Q2', 'Q2 (May - Jul)'),
        ('Q3', 'Q3 (Aug - Oct)'),
        ('Q4', 'Q4 (Nov - Jan)'),
    )
    STATE_CHOICES = (
        ('open', 'Open'),
        ('close', 'Close'),
    )
       
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filters['chances'].extra['choices'] = get_chances_of_closing_choices()
        
        qs = kwargs.get("queryset", Opportunity.objects.all())
        values_qs = OpportunityCustomFieldValue.objects.filter(
            opportunity__in=qs,
            custom_field__field_key="opportunity.opportunity_source"
        ).values_list("value", flat=True)

        sources = set()
        for val in values_qs:
            if isinstance(val, list):
                sources.update(val)
            elif val:
                sources.add(val)

        self.filters['opportunity_source'].extra['choices'] = [(v, v) for v in sorted(sources)]

    
    chances = filters.ChoiceFilter(
        method='filter_chances_of_closing',
        label='Chance of Closing the Deal'
    )

    opportunity_source = filters.ChoiceFilter(
        method='filter_by_opportunity_source',
        label='Opportunity Source',
        choices=[]  
    )
    
    state = filters.ChoiceFilter(
        choices=STATE_CHOICES,
        method='filter_state',
        label='Opportunity State'
    )
    created_at = filters.DateFromToRangeFilter(
        field_name='created_at',
        label="Created Date (range)",
        widget=widgets.RangeWidget(attrs={'type': 'date'})
    )
   
    opp_value = filters.RangeFilter(
        field_name="opp_value",
        label="Opportunity Value (range)",
        widget=widgets.RangeWidget(attrs={'type': 'number'})
    )
    
    assigned_to = filters.ModelMultipleChoiceFilter(
        queryset=GHLUser.objects.all(),
        field_name='assigned_to__id',
        to_field_name='id',
        label="Assigned Users",
        conjoined=False 
    )
    
    contact = filters.ModelMultipleChoiceFilter(
        queryset=Contact.objects.all(),  # import Contact model if not already
        field_name='contact__id',
        to_field_name='id',
        label="Contacts",
        conjoined=False
    )
    
    fiscal_period = filters.ChoiceFilter(
        choices=FISCAL_PERIOD_CHOICES,
        method='filter_fiscal_period',
        label='Fiscal Period'
    )
    
    # WORKS IF ITS POSTGRES
    # def filter_by_opportunity_source(self, queryset, name, value):
    #     return queryset.filter(
    #         custom_field_values__custom_field__field_key="opportunity.opportunity_source",
    #         custom_field_values__value__contains=[value]
    #     )
    
    def filter_by_opportunity_source(self, queryset, name, value):
        # First narrow to only relevant rows
        qs = queryset.filter(
            custom_field_values__custom_field__field_key="opportunity.opportunity_source"
        )

        # Apply manual filter if DB doesn't support __contains on JSONField
        filtered_ids = [
            item.ghl_id for item in qs if any(
                isinstance(val.value, list) and value in val.value
                for val in item.custom_field_values.all()
                if val.custom_field.field_key == "opportunity.opportunity_source"
            )
        ]

        return queryset.filter(ghl_id__in=filtered_ids)
    
    def filter_chances_of_closing(self, queryset, name, value):
        if value == 'null':
            return queryset.exclude(
                custom_field_values__custom_field__field_key='opportunity.chances_of_closing_the_deal'
            )
        return queryset.filter(
            custom_field_values__custom_field__field_key='opportunity.chances_of_closing_the_deal',
            custom_field_values__value=value
        )
            
    def filter_state(self, queryset, name, value):
        if value == 'open':
            return queryset.filter(status='open')
        if value == 'close':
            return queryset.exclude(status='open')
        return queryset
    
    def filter_fiscal_period(self, queryset, name, value):
        today = timezone.now().date()
        cy, cm = today.year, today.month

        if value == 'Q1':
            return queryset.filter(
                created_at__month__in=[2, 3, 4],
                created_at__year=cy
            )

        if value == 'Q2':
            return queryset.filter(
                created_at__month__in=[5, 6, 7],
                created_at__year=cy
            )

        if value == 'Q3':
            return queryset.filter(
                created_at__month__in=[8, 9, 10],
                created_at__year=cy
            )

        # Q4 is Nov–Dec + Jan
        if value == 'Q4':
            if cm == 1:
                # In January → treat Jan as part of last fiscal year's Q4
                return queryset.filter(
                    Q(created_at__month__in=[11, 12], created_at__year=cy - 1) |
                    Q(created_at__month=1, created_at__year=cy)
                )
            else:
                # Any other month → we're in fiscal year cy, so Jan belongs to next calendar year
                return queryset.filter(
                    Q(created_at__month__in=[11, 12], created_at__year=cy) |
                    Q(created_at__month=1, created_at__year=cy + 1)
                )

        return queryset


    class Meta:
        model = Opportunity
        fields = [
            'status', 'state', 'assigned_to',
            'created_at', 'opp_value', 'opp_value',
            'fiscal_period', 'stage', 'pipeline',
            ]
        
        
class PipelineStagesFilter(FilterSet):
    class Meta:
        model = PipelineStage
        fields = [
            'pipeline'
        ]
        
class PipelineFilter(FilterSet):
    stage_name = filters.ChoiceFilter(label="Stage Name",field_name="stages__name")
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        stage_names = PipelineStage.objects.values_list('name', flat=True).distinct()
        self.filters['stage_name'].extra['choices'] = [(name, name) for name in stage_names]


    class Meta:
        model = Pipeline
        fields = ['stage_name']
