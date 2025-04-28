
from django_filters import widgets
from django_filters.rest_framework import filters, FilterSet
from .models import Opportunity
from core.models import GHLUser, Contact


class OpportunityFilter(FilterSet):
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


    class Meta:
        model = Opportunity
        fields = ['status', 'assigned_to', 'created_at', 'opp_value', 'opp_value']
