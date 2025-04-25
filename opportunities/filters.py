import django_filters
from .models import Opportunity
from core.models import GHLUser

class OpportunityFilter(django_filters.FilterSet):
    created_at__gte = django_filters.DateFilter(field_name="created_at", lookup_expr='gte')
    created_at__lte = django_filters.DateFilter(field_name="created_at", lookup_expr='lte')
    opp_value__gte = django_filters.NumberFilter(field_name="opp_value", lookup_expr='gte')
    opp_value__lte = django_filters.NumberFilter(field_name="opp_value", lookup_expr='lte')
    assigned_to = django_filters.rest_framework.ModelChoiceFilter(
        queryset=GHLUser.objects.all(),
        field_name='assigned_to',
        to_field_name='id',  # If you want to filter by ID
        label="Assigned User"
    )

    class Meta:
        model = Opportunity
        fields = ['status', 'assigned_to', 'created_at__gte', 'created_at__lte', 'opp_value__gte', 'opp_value__lte']
