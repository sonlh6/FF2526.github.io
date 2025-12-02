from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from api_views import (
    test_connection,
    add_manager,
    get_manager_stats,
    compare_managers,
    remove_manager,
)

urlpatterns = [
    # Frontend View
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='fantasy_dashboard.html'), name='home'),

    # API Endpoints
    path('api/test-connection', test_connection),
    path('api/add-manager', add_manager),
    path('api/manager/<int:manager_id>/stats', get_manager_stats),
    path('api/compare-managers', compare_managers),
    path('api/remove-manager/<int:manager_id>', remove_manager),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)    