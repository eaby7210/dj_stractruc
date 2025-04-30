from django.urls import path, include
from .views import (
  OpportunityViewSet,PipelineViewSet,
  PipelineStageViewSet, OpportunityDashView

    )
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'opportunities',OpportunityViewSet, basename= 'opportunity')
router.register(r'pipelines', PipelineViewSet, basename='pipeline')
router.register(r'pipeline-stages', PipelineStageViewSet, basename='pipeline-stage')


urlpatterns = [
    path('',include(router.urls)),
    path('opportunity_dash', OpportunityDashView.as_view(), name='opportunity_dashboard')

]