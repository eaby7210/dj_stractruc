from django.db import models
from django.utils.timezone import now


class Contact(models.Model):
    id = models.CharField(max_length=50, primary_key=True)  # Contact ID from API
    first_name = models.CharField(max_length=100,null=True)
    last_name = models.CharField(max_length=100,null=True)
    email = models.EmailField(unique=True,null=True, blank=True)
    phone = models.CharField(max_length=100,null=True, blank=True)
    country = models.CharField(max_length=10,null=True, blank=True)
    location_id = models.CharField(max_length=50, null=True, blank=True)
    type = models.CharField(max_length=20, choices=[("lead", "Lead"), ("customer", "Customer")],null=True, blank=True)
    date_added = models.DateTimeField(default=now )  
    date_updated = models.DateTimeField(auto_now=True)  
    dnd = models.BooleanField(default=False)


 
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

class WebhookLog(models.Model):
    webhook_id = models.CharField(max_length=255, unique=True)
    received_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.webhook_id} : {self.received_at}"




# class DNDSettings(models.Model):
#     contact = models.OneToOneField(Contact, related_name="dnd_settings", on_delete=models.CASCADE)
#     call = models.JSONField(default=dict)
#     sms = models.JSONField(default=dict)
#     email = models.JSONField(default=dict)
#     whatsapp = models.JSONField(default=dict)
#     fb = models.JSONField(default=dict)
#     gmb = models.JSONField(default=dict)

#     def __str__(self):
#         return f"DND Settings for {self.contact.email}"
