from django import forms
from io import TextIOWrapper
import csv

from .models import Section, Member

from .utils import get_default_dates, process_full_name

class DateRangeForm(forms.Form):
    start_date, end_date = get_default_dates()
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), initial=start_date)
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), initial=end_date)
    sections = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['sections'].choices = [
            (section.pk, section.name) for section in Section.objects.filter(is_active=True)
        ]

class MembersFilterForm(forms.Form):
    sections = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['sections'].choices = [
            (section.pk, section.name) for section in Section.objects.filter(is_active=True)
        ]

class AddMemberForm(forms.ModelForm):

    id_num = forms.CharField(
        max_length=8,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '12345678',
        }),
        label="ID Number (e.g. 12345678)",
        required=False,
    )

    full_name = forms.CharField(
        max_length=300,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Doe, John Stephen',
        }),
        label="Full Name (e.g. Doe, John Stephen)",
        required=False,
    )

    position = forms.CharField(
        max_length=120,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Position',
        required=False,
    )

    csv_upload = forms.FileField(
        label="Upload CSV file for multiple members",
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
        required=False,
    )

    class Meta:
        model = Member
        fields = ['id_num', 'full_name', 'position', 'section', 'csv_upload']
        widgets = {
            'section': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['section'].choices = [
            (section.pk, section.name) for section in Section.objects.filter(is_active=True)
        ]

    def clean(self):
        cleaned_data = super().clean()
        csv_file = cleaned_data.get('csv_upload')
        id_num = cleaned_data.get('id_num')
        full_name = cleaned_data.get('full_name')

        if not csv_file and not (id_num and full_name):
            raise forms.ValidationError("Either fill out the form fields or upload a CSV file.")
        
        return cleaned_data

    def save(self, commit=True):
        csv_file = self.cleaned_data.get('csv_upload')

        if csv_file:
            self.handle_csv_upload(csv_file)
        else:
            self.handle_form_input()

    def handle_form_input(self):
        id_num = self.cleaned_data.get('id_num')
        full_name = self.cleaned_data.get('full_name')
        position = self.cleaned_data.get('position')
        section_name = self.cleaned_data.get('section')

        if id_num and full_name:
            # Process full_name
            parts = full_name.split(',')
            if len(parts) != 2:
                raise forms.ValidationError(f"Invalid full name format: {full_name}")

            last_name = parts[0].strip().title()
            first_name = parts[1].strip()
            middle_initial = None  # No middle initial for the form input

            # Check if a member with the same id_num exists
            member, created = Member.objects.get_or_create(
                id_num=id_num,
                defaults={
                    'last_name': last_name,
                    'first_name': first_name,
                    'middle_initial': middle_initial,
                    'position': position,
                    'section': Section.objects.get(pk=section_name),
                    'is_active': True
                }
            )

            if not created:
                # Update existing member's information
                member.last_name = last_name
                member.first_name = first_name
                member.middle_initial = middle_initial
                member.position = position
                member.section = Section.objects.get(pk=section_name)
                member.save()
                print(f"Updated member with ID {id_num}")
            else:
                print(f"Created new member with ID {id_num}")

    def handle_csv_upload(self, file):
        print("handle_csv_upload called")

        # Use utf-8-sig to handle BOM automatically if needed
        csv_reader = csv.reader((line.decode('utf-8-sig') for line in file))

        for row in csv_reader:
            print("Processing row:", row)

            # Strip whitespace from each element in the row
            id_num = row[0].strip()
            full_name = row[1].strip()
            position = row[2].strip()
            section_name = row[3].strip()

            # Convert id_num to integer
            try:
                id_num = int(id_num)  # Convert to integer
            except ValueError:
                print(f"Invalid ID Number: {id_num}")
                continue  # Skip this row if id_num is not valid

            # Ensure the section exists
            try:
                section = Section.objects.get(name=section_name)
            except Section.DoesNotExist:
                print(f"Section does not exist: {section_name}")
                continue  # Skip this entry

            # Process the full_name format
            last_name, first_name, middle_initial = process_full_name(full_name)

            # Check if a member with the same id_num exists
            member, created = Member.objects.get_or_create(
                id_num=id_num,
                defaults={
                    'last_name': last_name,
                    'first_name': first_name,
                    'middle_initial': middle_initial,
                    'position': position,
                    'section': section,
                    'is_active': True
                }
            )

            if not created:
                # Update existing member's information
                member.last_name = last_name
                member.first_name = first_name
                member.middle_initial = middle_initial
                member.position = position
                member.section = section
                member.save()  # Save the updated member
                print(f"Updated member with ID {id_num}")
            else:
                print(f"Created new member with ID {id_num}")

class EditMemberForm(forms.ModelForm):

    full_name = forms.CharField(
        max_length=300,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Doe, John Stephen',
        }),
        label="Full Name (e.g. Doe, John Stephen)",
        required=True,
    )

    position = forms.CharField(
        max_length=120,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Position',
        required=True,
    )

    section = forms.ModelChoiceField(
        queryset=Section.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Section',
        required=True,
    )

    class Meta:
        model = Member
        fields = ['id_num', 'full_name', 'position', 'section']

    def clean_full_name(self):
        full_name = self.cleaned_data.get('full_name')
        parts = full_name.split(',')
        if len(parts) != 2:
            raise forms.ValidationError("Full name must be in the format 'Last Name, First Name'.")
        return full_name

class AddSectionForm(forms.ModelForm):
    class Meta:
        model = Section
        fields = ['name', 'full_name', 'section_color']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }