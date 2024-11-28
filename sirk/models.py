from django.db import models
from django.utils import timezone
import datetime

from admins.models import APPInfo, Member

# Create your models here.
class Issue(models.Model):
    name = models.CharField(max_length=20)
    online_start_date = models.DateTimeField()
    online_end_date = models.DateTimeField()
    online_double_pts_end_date = models.DateTimeField()
    # manual_start_date = models.DateTimeField()
    # manual_end_date = models.DateTimeField()
    # manual_double_pts_end_date = models.DateTimeField()
    folder_id = models.CharField(max_length=40, null=True, default=None)
    app_info = models.ForeignKey(APPInfo, on_delete=models.DO_NOTHING)
    parent_folder_id = models.CharField(max_length=40)
    is_complete_online = models.BooleanField(default=False)

    def is_online_ongoing(self) : return self.online_start_date <= timezone.now() <= self.online_end_date
    
    def is_online_over(self) : return timezone.now() > self.online_start_date

    def is_final_online_date(self) : return self.online_end_date.date() + datetime.timedelta(days=1) == timezone.now().date()

class OnlinePoints(models.Model):
    rule = models.CharField(max_length=40)
    value = models.IntegerField()
    is_active = models.BooleanField(default=True)

# class SirkRecords(models.Model):
#     issue = models.ForeignKey(Issue, on_delete=models.DO_NOTHING)
#     member = models.ForeignKey(Member, on_delete=models.DO_NOTHING)
#     value = models.IntegerField()