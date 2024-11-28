from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.utils import timezone

from admins.models import Member
from . models import Residency

# Create your views here.

def render_residency(request):

    daily_records = Residency.get_daily_records()

    return render(request, 'residency/residency.html', { 'daily_records' : daily_records })

def get_current_time(request):
    current_time = timezone.localtime().strftime('%H:%M:%S')
    return JsonResponse({'time': current_time})

def run(request):
    if request.method == 'POST':
        id_num = request.POST.get('input')
        now = timezone.localtime()
        print("test")
        try:
            member = Member.objects.get(id_num=id_num)

            # Use get_or_create to retrieve or create the record in one go
            residency, created = Residency.objects.get_or_create(
                member=member,
                date=now,
                defaults={
                    'clock_in': now,
                }
            )

            if not created:
                print("not created")
                # Update the existing record to set the clock_out time
                residency.clocking_out()
        except Member.DoesNotExist:
            print("Member not found.")
        except Exception as e:
            print(f"An error occurred: {e}")

    return redirect('/')
    