from django.shortcuts import render

def dashboard_view(request):
    # View này chỉ đơn giản là render template chính của bạn.
    # Trong tương lai, bạn có thể truyền dữ liệu từ database vào template tại đây.
    return render(request, 'fantasy_dashboard.html')

