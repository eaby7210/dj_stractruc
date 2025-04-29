
from django.db.models import Q
from django.utils import timezone
from django_filters import widgets
from django_filters.rest_framework import filters, FilterSet
from .models import Opportunity
from core.models import GHLUser, Contact


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
            'fiscal_period'
            ]
