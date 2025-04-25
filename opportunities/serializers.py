from rest_framework import serializers
from core.serializers import ContactSerializer,GHLUserSerializer
from .models import Pipeline, Opportunity
from core .models import Contact


class PipelineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pipeline
        fields = [ "ghl_id", "name", "date_added", "date_updated"]


class OpportunityReadSerializer(serializers.ModelSerializer):
    assigned_to = GHLUserSerializer(read_only=True)
    contact = ContactSerializer(read_only=True)
    pipeline = PipelineSerializer(read_only=True)

    class Meta:
        model = Opportunity
        fields = [
            'ghl_id',
            'name',
            'opp_value',
            'assigned_to',
            'pipeline',
            'contact',
            'stage_id',
            'status',
            'created_at',
            'updated_at',
        ]

