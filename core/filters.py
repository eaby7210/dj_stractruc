# filters.py
from django_filters import rest_framework as filters
from core.models import Contact, GHLUser
from opportunities.models import Pipeline, PipelineStage

class ContactFilter(filters.FilterSet):

    
    pipeline = filters.ModelMultipleChoiceFilter(
        queryset=Pipeline.objects.all(),
        field_name='opportunity__pipeline',
        to_field_name='ghl_id',
        label="Pipelines",
        conjoined=False 
    )
    

    
    stage_name = filters.ModelMultipleChoiceFilter(
        queryset=PipelineStage.objects.all(),
        field_name="opportunity__stage",
        to_field_name='name',
        label="Stage Name",
        conjoined=False 
    )
    
    assigned_to = filters.ModelMultipleChoiceFilter(
        queryset=GHLUser.objects.all(),
        field_name='opportunity__assigned_to',
        to_field_name='id',
        label="Assigned Users",
        conjoined=False 
    )


    class Meta:
        model = Contact
        fields = ['pipeline', 'stage_name', 'assigned_to']


class GHLuserFilter(filters.FilterSet):

    
    pipeline = filters.ModelMultipleChoiceFilter(
        queryset=Pipeline.objects.all(),
        field_name='opportunity__pipeline',
        to_field_name='ghl_id',
        label="Pipelines",
        conjoined=False 
    )
    

    stage_name = filters.ModelMultipleChoiceFilter(
        queryset=PipelineStage.objects.all(),
        field_name="opportunity__stage",
        to_field_name='name',
        label="Stage Name",
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
        model = GHLUser
        fields = ['pipeline', 'stage_name', 'contact']