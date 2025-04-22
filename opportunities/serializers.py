from rest_framework import serializers
from core.serializers import ContactSerializer
from .models import Pipeline, Opportunity
from core .models import Contact


class PipelineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pipeline
        fields = [ "ghl_id", "name", "date_added", "date_updated"]


class OpportunitySerializer(serializers.ModelSerializer):
    pipeline = PipelineSerializer(read_only=True)
    pipeline_id = serializers.PrimaryKeyRelatedField(
        queryset=Pipeline.objects.all(), source="pipeline", write_only=True
    )
    contact = ContactSerializer(read_only=True)
    contact_id = serializers.PrimaryKeyRelatedField(
        queryset=Contact.objects.all(), source="contact", write_only=True, allow_null=True
    )

    class Meta:
        model = Opportunity
        fields = [
           
            "ghl_id",
            "name",
            "pipeline",
            "pipeline_id",
            "contact",
            "contact_id",
            "status",
            "created_at",
            "updated_at",
        ]


