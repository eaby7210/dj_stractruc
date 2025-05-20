from rest_framework import serializers
from .models import Contact,GHLUser
from opportunities.models import Opportunity



class ContactSerializer(serializers.ModelSerializer):
    custom_fields = serializers.SerializerMethodField()
    class Meta:
        model = Contact
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "phone",
            "country",
            "location_id",
            "type",
            "date_added",
            "date_updated",
            "dnd",
            'company_name',
            'custom_fields',
        ]
    def get_custom_fields(self, obj):
        custom_fields = {}
        for custom_value in obj.custom_field_values.all():
            field_key = custom_value.custom_field.field_key
            value = custom_value.value
            custom_fields[field_key.split('.')[1]] = value
        return custom_fields


class OpportunityMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Opportunity
        fields = [
            'ghl_id',
            'name',
            'opp_value',
            'status',
            'created_at',
            'updated_at',
        ]    
        


class ContactWithOpportunitiesSerializer(serializers.ModelSerializer):
    opportunities = OpportunityMinimalSerializer(many=True, read_only=True, source='opportunity_set')
    custom_fields = serializers.SerializerMethodField()

    class Meta:
        model = Contact
        fields = [
            'id',
            'first_name',
            'last_name',
            'email',
            'phone',
            'country',
            'location_id',
            'type',
            'date_added',
            'date_updated',
            'dnd',
            'opportunities',
            'custom_fields'
        ]
    
    def get_custom_fields(self, obj):
        custom_fields = {}
        for custom_value in obj.custom_field_values.all():
            field_key = custom_value.custom_field.field_key
            value = custom_value.value
            custom_fields[field_key.split('.')[1]] = value
        return custom_fields
     

class GHLUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = GHLUser
        fields = ['id', 'first_name', 'last_name', 'email', 'phone', 'role_type', 'role']
