import logging
from django.core.management.base import BaseCommand
from opportunities.services import OpportunityServices
from opportunities.models import Pipeline, Opportunity
from core.models import Contact,GHLUser
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
        
        query = {"pipeline_id": pipeline.ghl_id}  # Initial query param
        batch_size = 100  # Control batch size to optimize DB writes

        while True:
            opp_data, meta = OpportunityServices.get_opportunity(pipeline.LocationId,query=query)

            if not opp_data:
                break  # Exit if no more data

            print(f"Fetched {len(opp_data)} opportunities from API.")

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


                if contact:
                    opp_id = item["id"]
                    assigned_user = None
                    assigned_id = item.get("assignedTo")
                    if assigned_id:
                        assigned_user = GHLUser.objects.filter(id=assigned_id).first()
                    Opportunity.objects.update_or_create(
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
                            "stage_id": item["pipelineStageId"]
                        }
                    )
                    existing_opportunity_ids.add(opp_id)


            print(f"Total opportunities stored: {Opportunity.objects.count()}")
            print(f"Total contacts stored: {Contact.objects.count()}")


            next_page_url = meta.get("nextPageUrl")
            if not next_page_url:
                break 

            query.update({
                "startAfter": meta.get("startAfter", ""),
                "startAfterId": meta.get("startAfterId", ""),
            })
