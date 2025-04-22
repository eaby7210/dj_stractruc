from django.db import models

class Pipeline(models.Model):
    ghl_id = models.CharField(max_length=50, unique=True, db_index=True,primary_key=True)
    name = models.CharField(max_length=255)
    date_added = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Pipeline {self.ghl_id} - {self.name}"


class Opportunity(models.Model):
    ghl_id = models.CharField(max_length=50, unique=True, db_index=True,primary_key=True)  # GHL Opportunity ID
    name = models.CharField(max_length=255)
    pipeline = models.ForeignKey(Pipeline, on_delete=models.PROTECT, related_name="opportunities", null=True, blank=True)
    contact = models.ForeignKey('core.Contact', on_delete=models.SET_DEFAULT, null=True, blank=True,default=None)
    status = models.CharField(max_length=50, db_index=True)
    created_at = models.DateTimeField(db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Opportunity id:{self.ghl_id} - {self.name}"

