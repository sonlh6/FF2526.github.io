from django.urls import path
import views

urlpatterns = [
    # Map URL gốc ('/') tới dashboard_view của bạn
    path('', views.dashboard_view, name='dashboard'),
]

