from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ContactViewSet,WebhookView,GHLUserViewSet

router = DefaultRouter()
router.register(r"contacts", ContactViewSet, basename="contact")
router.register(r"ghlusers", GHLUserViewSet, basename="ghlusers")


urlpatterns = [
    path("webhook",WebhookView.as_view(),name ="contact-webhook"),
    path("", include(router.urls)),  
]