from django.urls import path, include
from .views import (
  OpportunityViewSet,

    )
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'opportunities',OpportunityViewSet, basename= 'opportunity')


urlpatterns = [
    path('',include(router.urls)),

]