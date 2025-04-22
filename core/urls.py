from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ContactViewSet,WebhookView

router = DefaultRouter()
router.register(r"contacts", ContactViewSet, basename="contact")


urlpatterns = [
    path("webhook",WebhookView.as_view(),name ="contact-webhook"),
    path("", include(router.urls)),  
]