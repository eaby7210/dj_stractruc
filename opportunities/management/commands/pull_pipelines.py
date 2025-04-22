from django.core.management.base import BaseCommand
from opportunities.services import PipelineServices

class Command(BaseCommand):
    help ="for getting pipelines"
    
    def add_arguments(self, parser):
        return super().add_arguments(parser)
    
    def handle(self, *args, **options):
        PipelineServices.pull_pipelines()