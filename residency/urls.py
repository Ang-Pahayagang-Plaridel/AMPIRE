from django.urls import path

from . import views

app_name = "residency"

urlpatterns = [
    path('', views.render_residency, name='index'),
    path('current_time', views.get_current_time, name='current_time'),
    path('run', views.run, name='run'),
]