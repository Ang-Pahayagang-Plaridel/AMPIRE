from django.urls import path

from . import views
from .task import compute_sirk

app_name = "sirk"

urlpatterns = [
    path('', views.render_issues, name='render_issues'),
    path('online_sirk_points', views.render_online_sirk_points, name='render_online_sirk_points'),
    # path('manual_sirk_points', views.render_manual_sirk_points, name='manual_sirk_points'),
    path('create_issue', views.create_issue, name='create_issue'),
    path('edit_issue', views.edit_issue, name='edit_issue'),
    # path('add_online_sirk_point', views.add_online_sirk_point, name='add_online_sirk_point'),
    path('create_online_sirk_points', views.create_online_sirk_points, name='create_online_sirk_points'),
    path('edit_online_sirk_points/<int:online_sirk_points_id>/', views.edit_online_sirk_points, name='edit_online_sirk_points'),
    path('delete_online_sirk_points/<int:online_sirk_points_id>/', views.delete_online_sirk_points, name='delete_online_sirk_points'),
    # path('add_manual_sirk_point', views.add_manual_sirk_point, name='add_manual_sirk_point'),

    path('compute_sirk', views.compute_sirk, name='compute_sirk'),
]