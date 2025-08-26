from django.urls import path, include
import views


urlpatterns = [
    # View để hiển thị trang chính
    path('', views.dashboard_view, name='dashboard'),

    # Tất cả các API endpoint sẽ được quản lý bởi app 'api'
    path('api/', include('api.urls', namespace='api')),
]
