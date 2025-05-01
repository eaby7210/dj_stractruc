# filters.py
from django_filters import rest_framework as filters
from core.models import Contact, GHLUser
from opportunities.models import Pipeline, PipelineStage

class ContactFilter(filters.FilterSet):
    pipeline = filters.ModelChoiceFilter(
        field_name='opportunity__pipeline',
        queryset=Pipeline.objects.all(),
        label='Pipeline',
        to_field_name='ghl_id'
    )
    
    stage = filters.ModelChoiceFilter(
        field_name='opportunity__stage',
        queryset=PipelineStage.objects.all(),
        label='Stage',
        to_field_name='id'
    )
    assigned_to = filters.ModelChoiceFilter(
        field_name='opportunity__assigned_to',
        queryset=GHLUser.objects.all(),
        label='Assigned User',
        to_field_name='id'  
    )

    class Meta:
        model = Contact
        fields = ['pipeline', 'stage', 'assigned_to']
