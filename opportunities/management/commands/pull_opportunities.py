import logging
import json
from django.core.management.base import BaseCommand
from opportunities.services import OpportunityServices
from opportunities.models import Pipeline, Opportunity, OpportunityCustomFieldValue, PipelineStage
from core.models import Contact,GHLUser, CustomField
from decimal import Decimal

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Fetch and store opportunities sequentially"

    def handle(self, *args, **options):
        pipelines = Pipeline.objects.all()
        
        for pipeline in pipelines:
            print(f"Processing pipeline: {pipeline.ghl_id} - {pipeline.name}")
            self.fetch_all_opportunities(pipeline)

    def fetch_all_opportunities(self, pipeline:Pipeline):
        """Fetch opportunities using a loop and store in the DB."""
        
        query = {"pipeline_id": pipeline.ghl_id}  
        batch_size = 100  

        while True:
            opp_data, meta = OpportunityServices.get_opportunity(pipeline.LocationId,query=query)

            if not opp_data:
                break  # Exit if no more data

            print(f"Fetched {len(opp_data)} opportunities from API.")
            # print(f"sample data :\n{json.dumps(opp_data[-1],indent=4)}")
            existing_contact_ids = set(Contact.objects.values_list("id", flat=True))
            existing_opportunity_ids = set(Opportunity.objects.values_list("ghl_id", flat=True))

            for item in opp_data:
                contact = None
                contact_id = None

                if "contact" in item and item["contact"]:
                    contact_data = item["contact"]
                    contact_id = str(contact_data["id"])  
                    name = contact_data.get("name", "")

                    first_name, last_name = "", ""
                    if name:
                        parts = name.strip().split(" ", 1)
                        first_name = parts[0]
                        last_name = parts[1] if len(parts) > 1 else ""

                    if contact_id not in existing_contact_ids:
                        contact, created = Contact.objects.update_or_create(
                            id=contact_id,
                            defaults={
                                "first_name": first_name,
                                "last_name": last_name,
                                "email": contact_data.get("email", ""),
                                "phone": contact_data.get("phone", ""),
                            }
                        )
                        existing_contact_ids.add(contact_id)  
                    else:
                        contact = Contact.objects.filter(id=contact_id).first()
                    
                try:
                    if contact:
                        opp_id = item["id"]
                        assigned_user = None
                        assigned_id = item.get("assignedTo")
                        if assigned_id:
                            assigned_user = GHLUser.objects.filter(id=assigned_id).first()
                        
                        stage_id = item.get("pipelineStageId")
                        stage = PipelineStage.objects.filter(id=stage_id).first()                        
                        opportunity, created =Opportunity.objects.update_or_create(
                            ghl_id=opp_id,
                            defaults={
                                "name": item["name"],
                                "pipeline": pipeline,
                                "status": item["status"],
                                "opp_value": Decimal(item.get("monetaryValue", 0)),
                                "contact": contact,
                                "assigned_to": assigned_user,
                                "created_at": item["createdAt"],
                                "updated_at": item["updatedAt"],
                                "stage": stage or None
                            }
                        )
                        existing_opportunity_ids.add(opp_id)

                        custom_fields_data = item.get("customFields", [])
                        if custom_fields_data and isinstance(custom_fields_data, list):
                            for field in custom_fields_data:
                                custom_field_id = field.get("id")
                                field_value = (
                                    field.get("fieldValueString") or
                                    field.get("fieldValueArray") or
                                    field.get("fieldValue")
                                )

                                if not custom_field_id:
                                    continue 
                                
                                try:
                                    custom_field = CustomField.objects.get(id=custom_field_id)
                                except CustomField.DoesNotExist:
                                    # print(f"sample data :\n{json.dumps(item,indent=4)}")
                                    print(f"CustomField with id {custom_field_id} not found, skipping...")
                                    continue

                                # Save or update custom field value
                                OpportunityCustomFieldValue.objects.update_or_create(
                                    opportunity=opportunity,
                                    custom_field=custom_field,
                                    defaults={"value": field_value}
                                    )
                except Exception as e:
                    print(e)
                    print(stage, pipeline, contact, assigned_user)
                    print(json.dumps(item, indent=4))
                    raise Exception('Error occured')
            print(f"Total opportunities stored: {Opportunity.objects.count()}")
            print(f"Total contacts stored: {Contact.objects.count()}")


            next_page_url = meta.get("nextPageUrl")
            if not next_page_url:
                break 

            query.update({
                "startAfter": meta.get("startAfter", ""),
                "startAfterId": meta.get("startAfterId", ""),
            })
            
    def get_custom_field_obj(self, location_id, key ):
        return CustomField.objects.get(location_id=location_id,field_key=key)
