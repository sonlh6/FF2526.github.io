# d:\sonlh6\Fantasy\api\models.py
from django.db import models

class Manager(models.Model):
    # FPL ID sẽ là khóa chính
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    team_name = models.CharField(max_length=255)
    # Tự động lưu thời điểm manager được thêm vào
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.team_name} ({self.name})"

    class Meta:
        # Sắp xếp các manager theo thứ tự được thêm vào
        ordering = ['created_at']
