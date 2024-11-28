from django import forms

from .models import Issue, OnlinePoints

class IssueForm(forms.ModelForm):
    class Meta:
        model = Issue
        fields = ['name', 'online_start_date', 'online_end_date', 'online_double_pts_end_date']
        widgets = {
            'online_start_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local', 
                'class': 'form-control'
            }),
            'online_end_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local', 
                'class': 'form-control'
            }),
            'online_double_pts_end_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local', 
                'class': 'form-control'
            }),
        }

class EditIssueForm(forms.ModelForm):
    class Meta:
        model = Issue
        fields = ['online_start_date', 'online_end_date', 'online_double_pts_end_date']
        widgets = {
            'online_start_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local', 
                'class': 'form-control'
            }),
            'online_end_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local', 
                'class': 'form-control'
            }),
            'online_double_pts_end_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local', 
                'class': 'form-control'
            }),
        }

class OnlinePointsForm(forms.ModelForm):
    class Meta:
        model = OnlinePoints
        fields = ['rule', 'value']
        widgets = {
            'rule': forms.TextInput(attrs={'class': 'form-control'}),
            'value': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        }

class EditOnlinePointsForm(forms.ModelForm):
    class Meta:
        model = OnlinePoints
        fields = ['value']
        widgets = {
            'value': forms.NumberInput(attrs={'class': 'form-control'}),
        }