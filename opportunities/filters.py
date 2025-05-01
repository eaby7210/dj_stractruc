
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

    
    chances = filters.MultipleChoiceFilter(
        method='filter_chances_of_closing',
        label='Chance of Closing the Deal'
    )

    opportunity_source = filters.MultipleChoiceFilter(
        method='filter_by_opportunity_source',
        label='Opportunity Source',
        choices=[]
    )
    
    state = filters.MultipleChoiceFilter(
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
    
    
    pipeline = filters.ModelMultipleChoiceFilter(
        queryset=Pipeline.objects.all(),
        field_name='pipeline__ghl_id',
        to_field_name='ghl_id',
        label="Pipelines",
        conjoined=False 
    )
    

    stage_name = filters.ModelMultipleChoiceFilter(
        queryset=PipelineStage.objects.all(),
        field_name="stage__name",
        to_field_name='name',
        label="Stage Name",
        conjoined=False 
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
    
    fiscal_period = filters.MultipleChoiceFilter(
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
    
    def filter_by_opportunity_source(self, queryset, name, values):
        qs = queryset.filter(
            custom_field_values__custom_field__field_key="opportunity.opportunity_source"
        )

        filtered_ids = [
            item.ghl_id for item in qs if any(
                isinstance(val.value, list) and any(v in val.value for v in values)
                for val in item.custom_field_values.all()
                if val.custom_field.field_key == "opportunity.opportunity_source"
            )
        ]

        return queryset.filter(ghl_id__in=filtered_ids)
    
    def filter_chances_of_closing(self, queryset, name, values):
        if 'null' in values:
            queryset = queryset.exclude(
                custom_field_values__custom_field__field_key='opportunity.chances_of_closing_the_deal'
            )
            values = [v for v in values if v != 'null']

        if values:
            queryset = queryset.filter(
                custom_field_values__custom_field__field_key='opportunity.chances_of_closing_the_deal',
                custom_field_values__value__in=values
            )
        return queryset

            
    def filter_state(self, queryset, name, values):
        if 'open' in values and 'close' in values:
            return queryset
        elif 'open' in values:
            return queryset.filter(status='open')
        elif 'close' in values:
            return queryset.exclude(status='open')
        return queryset
    
    def filter_fiscal_period(self, queryset, name, values):
        today = timezone.now().date()
        cy, cm = today.year, today.month
        q_filters = Q()

        for value in values:
            if value == 'Q1':
                q_filters |= Q(created_at__month__in=[2, 3, 4], created_at__year=cy)
            elif value == 'Q2':
                q_filters |= Q(created_at__month__in=[5, 6, 7], created_at__year=cy)
            elif value == 'Q3':
                q_filters |= Q(created_at__month__in=[8, 9, 10], created_at__year=cy)
            elif value == 'Q4':
                if cm == 1:
                    q_filters |= Q(created_at__month__in=[11, 12], created_at__year=cy - 1)
                    q_filters |= Q(created_at__month=1, created_at__year=cy)
                else:
                    q_filters |= Q(created_at__month__in=[11, 12], created_at__year=cy)
                    q_filters |= Q(created_at__month=1, created_at__year=cy + 1)

        return queryset.filter(q_filters)
    class Meta:
        model = Opportunity
        fields = [
            'status', 'state', 'assigned_to',
            'created_at', 'opp_value', 'opp_value',
            'fiscal_period', 'stage_name', 'pipeline',
            ]
            
            
class PipelineStagesFilter(FilterSet):
    pipeline = filters.ModelMultipleChoiceFilter(
        queryset=Pipeline.objects.all(),
        field_name='pipeline__ghl_id',
        to_field_name='ghl_id',
        label="Pipelines",
        conjoined=False 
    )
    
    contact = filters.ModelMultipleChoiceFilter(
        queryset=Contact.objects.all(),  # import Contact model if not already
        field_name='opportunities__contact__id',
        to_field_name='id',
        label="Contacts",
        conjoined=False
    )
    
    assigned_to = filters.ModelMultipleChoiceFilter(
        queryset=GHLUser.objects.all(),
        field_name='opportunities__assigned_to__id',
        to_field_name='id',
        label="Assigned Users",
        conjoined=False 
    )
    
    class Meta:
        model = PipelineStage
        fields = [
            'pipeline','contact', 'assigned_to'
        ]
        
class PipelineFilter(FilterSet):
    # stage = filters.ModelMultipleChoiceFilter(
    #     queryset=PipelineStage.objects.all(),
    #     field_name='stages__id',
    #     to_field_name='id',
    #     label="Pipeline Stages",
    #     conjoined=False 
    # )
    stage_name = filters.ModelMultipleChoiceFilter(
        queryset=PipelineStage.objects.all(),
        field_name="stages__name",
        to_field_name='name',
        label="Stage Name",
        conjoined=False 
    )
    
    contact = filters.ModelMultipleChoiceFilter(
        queryset=Contact.objects.all(),  # import Contact model if not already
        field_name='opportunities__contact__id',
        to_field_name='id',
        label="Contacts",
        conjoined=False
    )
    assigned_to = filters.ModelMultipleChoiceFilter(
        queryset=GHLUser.objects.all(),
        field_name='opportunities__assigned_to__id',
        to_field_name='id',
        label="Assigned Users",
        conjoined=False 
    )
    # stage_name = filters.ChoiceFilter(label="Stage Name",field_name="stages__name")
    
    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     stage_names = PipelineStage.objects.values_list('name', flat=True).distinct()
    #     self.filters['stage_name'].extra['choices'] = [(name, name) for name in stage_names]


    class Meta:
        model = Pipeline
        fields = [ 'stage_name', 'contact', 'assigned_to']
