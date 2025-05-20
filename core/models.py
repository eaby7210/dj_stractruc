from django.db import models
from django.utils.timezone import now


class OAuthToken(models.Model):
    access_token = models.TextField()
    token_type = models.CharField(max_length=100, default="Brearer")
    expires_at = models.DateField()
    refresh_token = models.TextField()
    scope = models.TextField()
    userType = models.CharField(max_length=100)
    companyId = models.CharField(max_length=100)
    company_name = models.CharField(max_length=200, null=True, blank=True)
    LocationId = models.CharField(max_length=100,unique=True)
    userId = models.CharField(max_length=100)
    
    def is_expired(self):
        """Check if the access token is expired"""
        return now().date() >= self.expires_at
    
    def __str__(self):
        return f"{self.LocationId} - {self.token_type}"
    
class GHLUser(models.Model):
    id = models.CharField(max_length=50, primary_key=True)  # UserID from API
    first_name = models.CharField(max_length=100,null=True)
    last_name = models.CharField(max_length=100,null=True)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=100,null=True, blank=True)
    role_type = models.CharField(max_length=50, null=True, blank=True)
    role = models.CharField(max_length=50, null=True, blank=True)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"   

class Contact(models.Model):
    id = models.CharField(max_length=50, primary_key=True)  # Contact ID from API
    first_name = models.CharField(max_length=100,null=True)
    last_name = models.CharField(max_length=100,null=True)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=100,null=True, blank=True)
    country = models.CharField(max_length=10,null=True, blank=True)
    location_id = models.CharField(max_length=50, null=True, blank=True)
    type = models.CharField(max_length=20, choices=[("lead", "Lead"), ("customer", "Customer")],null=True, blank=True)
    date_added = models.DateTimeField(null=True, blank=True)  
    date_updated = models.DateTimeField(null=True, blank=True)  
    dnd = models.BooleanField(default=False)
    company_name = models.CharField(max_length=100, null=True, blank=True)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

class ContactCustomFieldValue(models.Model):
    contact = models.ForeignKey('Contact', on_delete=models.CASCADE, related_name='custom_field_values')
    custom_field = models.ForeignKey('core.CustomField', on_delete=models.CASCADE)
    value = models.JSONField( null=True, blank=True)

    class Meta:
        unique_together = ('contact', 'custom_field')

    def __str__(self):
        return f"{self.contact.name} - {self.custom_field.name}: {self.value}"


class WebhookLog(models.Model):
    webhook_id = models.CharField(max_length=255, unique=True)
    received_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.webhook_id} : {self.received_at}"


class CustomField(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=255)
    model_name = models.CharField(max_length=50)
    field_key = models.CharField(max_length=255)
    placeholder = models.CharField(max_length=255, blank=True)
    data_type = models.CharField(max_length=50)
    parent_id = models.CharField(max_length=100)
    location_id = models.CharField(max_length=100)
    date_added = models.DateTimeField()

    def __str__(self):
        return self.name

