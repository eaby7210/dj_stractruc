import requests
import os
import json
from .models import Pipeline,TermSheet
from django.conf import settings
from core.services import OAuthServices


LIMIT_PER_PAGE = 100
BASE_URL = 'https://services.leadconnectorhq.com'
API_VERSION = "2021-07-28"

class PipeLinesError(Exception):
    "exeption for pipeline"
    pass

class OpportunityError(Exception):
    "exeption for pipeline"
    pass


class PipelineServices:
    
    @staticmethod
    def get_pipelines(query=None):
        
        url = f"{BASE_URL}/opportunities/pipelines"
        token_obj = OAuthServices.get_valid_access_token_obj()
        headers = {
            "Authorization": f"Bearer {token_obj.access_token}",
            "Content-Type": "application/json",
            "Version": API_VERSION,
        }
        params = {
            "locationId": token_obj.LocationId
        }
        response = requests.get(url, headers=headers, params=params)
        print(response.status_code)
        if response.status_code == 200:
            return response.json().get("pipelines",[])
        else:
            raise PipeLinesError(f"Faile to fetch pipelines: {response.json().get('pipelines',[])}")
    
    @staticmethod
    def pull_pipelines():
        """Fetches pipelines from GHL and stores them in the local database"""
        pipelines = PipelineServices.get_pipelines()
        
        if not pipelines:
            print("No pipelines found or API request failed.")
            return
        
        for pipeline_data in pipelines:
            ghl_id = pipeline_data.get("id")
            name = pipeline_data.get("name")
            
            if ghl_id and name:
                # Create or update the pipeline
                pipeline, created = Pipeline.objects.update_or_create(
                    ghl_id=ghl_id,
                    defaults={"name": name}
                )
                if created:
                    print(f"Pipeline '{name}' added.")
                else:
                    print(f"Pipeline '{name}' updated.")
    


class OpportunityServices:
    
    @staticmethod
    def get_opportunity(url=None,query :dict =None, limit=LIMIT_PER_PAGE):
        '''
        Fetch opportunities
        '''
        token_obj = OAuthServices.get_valid_access_token_obj()
        
        headers = {
            "Authorization": f"Bearer {token_obj.access_token}",
            "Content-Type": "application/json",
            "Version": API_VERSION,
        }
        params ={
            'limit':limit,
            'location_id':token_obj.LocationId
        }
        if url:
            req_url = url
        else:
            req_url = f"{BASE_URL}/opportunities/search"
        if query:
            params.update(query)
        response = requests.get(req_url, headers=headers, params=params)
        if response.status_code == 200:
            with open(os.path.join(settings.BASE_DIR,"opp_response.json"),"a") as file:
                file.write(json.dumps(response.json().get("opportunities",[]), indent=4))
            
            # return response.json().get("opportunities",[])
            # res = dict(filter(lambda res : res[0]!= "opportunities",response.json().items()))
            with open(os.path.join(settings.BASE_DIR,"opp_filter.json"),"a") as file:
                file.write(json.dumps(response.json().get("meta",[]),indent=4))
                file.write(json.dumps(params,indent=4))
          
            return response.json().get("opportunities", []),response.json().get("meta",[])
        else:
            
            print(f"Opportunity service Error: {json.dumps(response.json(), indent=4)}")
            return None,None
    
    
 
    