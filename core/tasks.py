from celery import shared_task
# from .services import OAuthServices
from management.commands.refresh_all_token import Command

@shared_task
def refresh_token_task():
    Command.handle()
    print("Token refresh task executed.")