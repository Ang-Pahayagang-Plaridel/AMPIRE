from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404

from gsheets.sheets import get_sheet_names
from .task import create_folders

from admins.models import APPInfo, Section, Member
from .models import Issue, OnlinePoints

from .forms import IssueForm, EditIssueForm, OnlinePointsForm, EditOnlinePointsForm

# Create your views here.

@login_required
def render_online_sirk_points(request):
    online_points = OnlinePoints.objects.filter(is_active=True)
    edit_forms = {point.pk: EditOnlinePointsForm(instance=point) for point in online_points}
    zipped_points_forms = zip(online_points, [edit_forms[point.pk] for point in online_points])

    return render(request, 'sirk/online_sirk_points.html', {
        'online_points': online_points, 
        'form': OnlinePointsForm(),
        'zipped_points_forms': zipped_points_forms,
        'edit_forms': edit_forms,
    })

def create_online_sirk_points(request):
    if request.method == 'POST':
        form = OnlinePointsForm(request.POST)
        if form.is_valid() : form.save()

    return redirect('sirk:render_online_sirk_points')

def edit_online_sirk_points(request, online_sirk_points_id):
    if request.method == 'POST':
        online_point = get_object_or_404(OnlinePoints, pk=online_sirk_points_id)
        form = EditOnlinePointsForm(request.POST, instance=online_point)
        if form.is_valid() : form.save()

    return redirect('sirk:render_online_sirk_points')

def delete_online_sirk_points(request, online_sirk_points_id):
    if request.method == 'POST':
        online_point = get_object_or_404(OnlinePoints, pk=online_sirk_points_id)
        online_point.is_active = False
        online_point.save()
    return redirect('sirk:render_online_sirk_points')

@login_required
def render_issues(request):
    app_info = APPInfo.objects.last()
    issues = Issue.objects.filter(app_info=app_info)
    last_issue = issues.last()

    context = {
        'issues': issues,
        'form': IssueForm(),
    }

    if issues:
        context['edit_form'] = EditIssueForm(instance=last_issue)
        context['last_issue_name'] = issues.last().name

    return render(request, 'sirk/issue.html', context)

def edit_issue(request):
    if request.method == "POST":
        issue = Issue.objects.last()
        form = EditIssueForm(request.POST, instance=issue)
        
        if form.is_valid():
            new_online_end_date = form.cleaned_data['online_end_date']

            if new_online_end_date != issue.online_end_date:
                issue.is_complete_online = False

            form.save()
            issue.save()

    return redirect('sirk:render_issues')

def create_issue(request):
    if request.method == 'POST':
        form = IssueForm(request.POST)
        if form.is_valid():
            try:
                sections = Section.objects.filter(is_active=True)
                sections_data = []
                for idx, section in enumerate(sections, start=1):
                    members = Member.objects.filter(section=section, is_active=True).filter(
                        Q(position="Kasapi") | Q(position="Korespondente")
                    )
                    section_data = {
                        'name': f'{str(idx).zfill(2)}. {section.name.upper()}',
                        'members': [member.get_name() for member in members]
                    }
                    sections_data.append(section_data)
                
                # Query online sirk data
                online_sirk_rules = OnlinePoints.objects.filter(is_active=True)
                online_sirk_data = [f'{str(idx).zfill(2)}. {online_sirk_rule.rule.upper()}' for idx, online_sirk_rule in enumerate(online_sirk_rules, start=1)]
                
                app_info = APPInfo.objects.last()
                parent_folder_id = app_info.sirk_folder_id

                # Save the issue form and create an issue instance
                issue = form.save(commit=False)
                issue.folder_id = None  # Set additional fields as needed
                issue.app_info = app_info
                issue.parent_folder_id = parent_folder_id
                issue.save()

                # Start any asynchronous tasks (e.g., Celery tasks)
                # add_isyu_in_sirk_tracker.delay(issue.pk)
                create_folders.delay(
                    issue_id=issue.pk,
                    sections=sections_data, 
                    online_sirk=online_sirk_data,
                    parent_folder_id=parent_folder_id,
                )
            except Exception as e:
                print(f"An error occurred: {e}")
            finally:
                # Perform any necessary cleanup here
                pass
    
    return redirect('sirk:render_issues')

from sirk.task import compute_sirk as compute_sirk_task

def compute_sirk(request):
    compute_sirk_task()
    return redirect('/sirk')