# d:\sonlh6\Fantasy\views.py
from django.shortcuts import render
from api.models import Manager

def dashboard_view(request):
    # Lấy tất cả manager từ database
    managers_from_db = Manager.objects.all()
    # Truyền danh sách manager vào template
    context = {
        'managers': managers_from_db
    }
    return render(request, 'fantasy_dashboard.html', context)
