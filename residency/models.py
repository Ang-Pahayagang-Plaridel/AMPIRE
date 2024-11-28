from django.db import models
from django.utils import timezone
from datetime import date
from django.db.models import F, Max, Case, When, Value, DateTimeField
from django.db.models.functions import Coalesce
from admins.models import Member

# Create your models here.

class Residency(models.Model):
    member = models.ForeignKey(Member, on_delete=models.DO_NOTHING)
    date = models.DateField()
    clock_in = models.TimeField()
    clock_out = models.TimeField(null=True)

    def clocking_in(self):
        self.date = timezone.localtime()
        self.clock_in = timezone.localtime().time()
        self.save()

    def clocking_out(self):
        self.clock_out = timezone.localtime().time()
        self.save()

    def get_daily_records():
        target_date = date.today()
    
        # Query the Residency records for the target date
        records = Residency.objects.filter(date=target_date).select_related('member').annotate(
        latest_update=Coalesce(
            Case(
                When(clock_out__isnull=False, then=F('clock_out')),
                default=F('clock_in'),
                output_field=DateTimeField()
            ),
            F('clock_in'),
            output_field=DateTimeField()
            )
        ).order_by('-latest_update', '-clock_in')
        
        return records

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['member', 'date'], name='unique_member_date'),
        ]