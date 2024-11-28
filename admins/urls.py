from django.urls import path

from . import views

app_name = "admin"

urlpatterns = [
    path('', views.render_admin, name='dashboard'),
    path('members', views.render_members, name='members'),
    path('add_members', views.add_members, name='add_members'),
    path('edit_member/<str:member_id>/', views.edit_member, name='edit_member'),
    # path('sections', views.render_sections, name='sections'),
    path('fetch_reports/', views.fetch_reports, name='fetch_reports'),
    path('get_members', views.get_members, name='get_members'),
    path('new_APP', views.new_APP, name='new_APP'),
    path('update_members', views.update_members, name='update_members'),
    
    path('auth', views.auth, name='auth'),
]