from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
import views

urlpatterns = [
    # Frontend View
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='fantasy_dashboard.html'), name='home'),

    # API Endpoints
    path('api/test-connection', views.test_connection, name='api_test_connection'),
    path('api/add-manager', views.add_manager, name='api_add_manager'),
    path('api/manager/<int:manager_id>/stats', views.get_manager_stats, name='api_get_manager_stats'),
    path('api/compare-managers', views.compare_managers, name='api_compare_managers'),
    path('api/remove-manager/<int:manager_id>', views.remove_manager, name='api_remove_manager'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)    