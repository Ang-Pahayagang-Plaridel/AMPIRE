from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from collections import Counter
from datetime import datetime

from django.db.models import Q

from . models import APPInfo, Member, Section
from residency.models import Residency

from .task import create_APP_folder, update_db

from .forms import DateRangeForm, MembersFilterForm, AddMemberForm, EditMemberForm #, SectionForm
from .utils import get_default_dates, lighten_color
from gsheets.utils import extract_sheet_id

# Create your views here.

def auth(request):
    if request.method == 'POST':
        data = request.POST
        username = data.get("username")
        password = data.get("password")
        
        user = authenticate(request, username=username, password=password)
            
        if user is not None:
            # Log in the user
            login(request, user)
            return redirect('admin:dashboard')
        else:
            # Handle invalid login
            return redirect('login')
            return render(request, 'admin/login.html', {'error': 'Invalid username or password'})

@login_required
def render_admin(request):
    form = DateRangeForm(request.GET or None)
    return render(request, 'admin/admin.html', { 'form': form })

@login_required
def render_members(request):
    context = {
        'member_filter_form': MembersFilterForm(request.GET or None),
        'add_member_form': AddMemberForm(),
        'edit_member_form': EditMemberForm()
    }
    return render(request, 'admin/members.html', context)

def add_members(request):
    if request.method == 'POST':
        form = AddMemberForm(request.POST, request.FILES)  # Include request.FILES to handle file uploads
        if form.is_valid():
            form.save()
    return redirect('admin:members')

def edit_member(request, member_id):
    if request.method == "POST":
        member = get_object_or_404(Member, id_num=member_id)
        form = EditMemberForm(request.POST, instance=member)
        if form.is_valid():
            form.save()
    return redirect('admin:members')

# def render_sections(request):
#     sections = Section.objects.all()
#     return render(request, 'admin/sections.html', { 
#         'form': SectionForm(),
#         'sections': sections,
#     })

# def create_section(request):
#     if request.method == 'POST':
#         form = SectionForm(request.POST)
#         if form.is_valid() : form.save()

#     # TODO: celery task to add a new section in tracker

#     return redirect('admin:sections')

# def edit_online_sirk_points(request, section_id):
#     if request.method == 'POST':
#         section = get_object_or_404(Section, pk=section_id)
#         form = SectionForm(request.POST, instance=section)
#         if form.is_valid() : form.save()

#     return redirect('admin:sections')

# def delete_online_sirk_points(request, section_id):
#     if request.method == 'POST':
#         section = get_object_or_404(Section, pk=section_id)
#         section.is_active = False
#         section.save()

#     return redirect('admin:sections')

def new_APP(request):
    if request.method == 'POST':
        data = request.POST
        app_year = data.get("app_year")
        gmail = data.get("gmail")

        try:
            app_info = APPInfo.objects.create(
                year=app_year,
            )
            create_APP_folder.delay(app_info.pk, gmail)
        except Exception as e:
            print(f"An error occurred: {e}")

    return redirect('/admin')

def fetch_reports(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    section_ids = request.GET.getlist('sections')

    if not start_date or not end_date:
        start_date, end_date = get_default_dates()

    sections = Section.objects.filter(is_active=True)

    if not section_ids:
        section_ids = sections.values_list('id', flat=True)

    residencies = Residency.objects.filter(
        date__range=(start_date, end_date),
        member__section__in=section_ids
    ).filter(
        Q(member__position="Kasapi") | Q(member__position="Korespondente")
    ).exclude(clock_out=None)

    reports = []
    section_reports = []

    for section in sections:
        section_residencies = residencies.filter(member__section=section)
        total_residency_minutes = 0

        for residency in section_residencies:
            if residency.clock_out and residency.clock_in:
                residency_time = datetime.combine(residency.date, residency.clock_out) - datetime.combine(residency.date, residency.clock_in)
                residency_minutes = residency_time.total_seconds() // 60
                if residency_minutes > 0:
                    total_residency_minutes += residency_minutes

                    reports.append({
                        # 'id': residency.member.id,
                        'id': residency.member.id_num,
                        'name': residency.member.get_name(),
                        # 'name': f"{residency.member.first_name} {residency.member.last_name}",
                        'position': residency.member.get_position(),
                        'section': residency.member.section.name,
                        'residency': residency_minutes
                    })

        section_reports.append({
            'name': section.name,
            'primary_color': section.section_color,
            'secondary_color': lighten_color(section.section_color),
            # 'primary_color': section.primary_color,
            # 'secondary_color': section.secondary_color,
            'residency': total_residency_minutes
        })

    return JsonResponse({
        'reports': reports,
        'section_reports': section_reports,
    })

def get_members(request):
    section_ids = request.GET.getlist('sections')

    if not section_ids:
        section_ids = Section.objects.filter(is_active=True).values_list('id', flat=True)

    member_list = []
    members = Member.objects.filter(is_active=1, section__in=section_ids).order_by('last_name', 'first_name')
    for member in members:
        member_list.append({
            'pk': member.pk,
            'id': member.id_num,
            'name': member.get_name(),
            'position': member.position,
            'section': member.section.name,
        })
    return JsonResponse({ 'members' : member_list })

# def update_members(request):

#     if request.method == 'POST':
#         gsheet_link = request.POST.get('gsheet_link')
#         is_update_sirk_tracker = request.POST.get('update_sirk_tracker')

#         # TODO: Input Validation
#         spread_sheet_id = extract_sheet_id(gsheet_link)
#         update_db.delay(spread_sheet_id, is_update_sirk_tracker)

#     return redirect('/admin')

def update_members(request):

    if request.method == 'POST':



        return redirect('/admin')
