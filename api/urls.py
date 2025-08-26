from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    path('test-connection', views.test_connection, name='test_connection'),
    path('add-manager', views.add_manager, name='add_manager'),
    path('manager/<int:manager_id>/stats', views.get_manager_stats, name='get_manager_stats'),
    path('compare-managers', views.compare_managers, name='compare_managers'),
    path('remove-manager/<int:manager_id>', views.remove_manager, name='remove_manager'),
    path('clear-all-managers', views.clear_all_managers, name='clear_all_managers'),
]
