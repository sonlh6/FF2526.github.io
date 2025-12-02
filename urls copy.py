from django.urls import path
import views

urlpatterns = [
    # Frontend View
    path('', views.dashboard_view, name='dashboard'),

    # API Endpoints
    path('api/test-connection', views.test_connection, name='api_test_connection'),
    path('api/add-manager', views.add_manager, name='api_add_manager'),
    path('api/manager/<int:manager_id>/stats', views.get_manager_stats, name='api_get_manager_stats'),
    path('api/compare-managers', views.compare_managers, name='api_compare_managers'),
    path('api/remove-manager/<int:manager_id>', views.remove_manager, name='api_remove_manager'),
]

    