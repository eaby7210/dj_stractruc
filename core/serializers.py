from rest_framework import serializers
from .models import Contact,GHLUser


from rest_framework import serializers
from .models import Contact


class ContactSerializer(serializers.ModelSerializer):
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
        ]
        

class GHLUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = GHLUser
        fields = ['id', 'first_name', 'last_name', 'email', 'phone', 'role_type', 'role']
