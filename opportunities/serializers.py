from rest_framework import serializers
from core.serializers import ContactSerializer,GHLUserSerializer
from .models import Pipeline, Opportunity, PipelineStage
from core .models import Contact


class PipelineStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PipelineStage
        fields = ['id', 'name', 'position']

class PipelineSerializer(serializers.ModelSerializer):
    stages = PipelineStageSerializer(many=True, read_only=True)

    class Meta:
        model = Pipeline
        fields = ['ghl_id', 'name', 'LocationId', 'date_added', 'date_updated', 'stages']

class PipelineSubSerializer(serializers.ModelSerializer):


    class Meta:
        model = Pipeline
        fields = ['ghl_id', 'name', 'LocationId', 'date_added', 'date_updated']


class OpportunityReadSerializer(serializers.ModelSerializer):
    assigned_to = GHLUserSerializer(read_only=True)
    contact = ContactSerializer(read_only=True)
    pipeline = PipelineSubSerializer(read_only=True)
    custom_fields = serializers.SerializerMethodField()
    stage = PipelineStageSerializer()
    next_step = serializers.SerializerMethodField()

    class Meta:
        model = Opportunity
        fields = [
            'ghl_id',
            'name',
            'opp_value',
            'assigned_to',
            'pipeline',
            'contact',
            'stage',
            'status',
            'created_at',
            'updated_at',
            'custom_fields','next_step',
        ]
        
    def get_custom_fields(self, obj):
        custom_fields = {}
        for custom_value in obj.custom_field_values.all():
            field_key = custom_value.custom_field.field_key
            value = custom_value.value
            custom_fields[field_key.split('.')[1]] = value
        return custom_fields
    
    def get_next_step(self, obj):
        if not obj.stage or not obj.pipeline:
            return None
        current_position = obj.stage.position
        next_stage = obj.pipeline.stages.filter(position__gt=current_position).order_by('position').first()
        if next_stage:
            return PipelineStageSerializer(next_stage).data
        return None