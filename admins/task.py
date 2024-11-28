from celery import shared_task
from django.shortcuts import get_object_or_404
from django.db import transaction
from collections import Counter

from gdrive.views import create_APP_folder_process
from gsheets.views import get_members_data
from sirk.task import get_sirk_tracker

from .models import APPInfo, Member, Section

from collections import defaultdict
from django.http import HttpResponse
from gsheets.sheets import copy_sheets, add_rows_and_fill_color, get_sheet_names, get_sheets_members, update_sirk_tracker_with_new_members, update_2nd_to_last_row_formulas
from gdrive.drive import add_manager_and_set_permissions, find_gsheet_in_folder
from django.db.models import Q
from decouple import config
from AMPIRE.utils import hex_to_rgb, logger
from .utils import lighten_color, process_full_name

def initialize_sirk_tracker():
    spreadsheet_template_id = config('SPREADSHEET_TEMPLATE_ID')
    spreadsheet_id = get_sirk_tracker()
    sections = Section.objects.filter(is_active=True)
    sections_list = [section.upper() for section in Section.objects.filter(is_active=True).values_list('name', flat=True)]
    sections_primary_colors = [hex_to_rgb(color) for color in sections.values_list('section_color', flat=True)]
    # sections_secondary_colors = [hex_to_rgb(lighten_color(color)) for color in sections.values_list('section_color', flat=True)]
    new_sheet_ids = copy_sheets(spreadsheet_template_id, config('SIRK_SECTION_TEMPLATE'), spreadsheet_id, sections_list, sections_primary_colors)

    # Combine section names, primary and secondary colors
    sheet_data_with_colors = {
        section.name.upper(): {
            'members': [],
            # 'primary_color': hex_to_rgb(section.section_color),
            'secondary_color': hex_to_rgb(lighten_color(section.section_color))
        } 
        for section in sections
    }

    members = Member.objects.filter(is_active=True).filter(
                Q(position="Kasapi") | Q(position="Korespondente")
            ).order_by('last_name', 'first_name')

    for member in members:
        section = member.section.name.upper()
        sheet_data_with_colors[section]['members'].append(member.get_name())

    # Sort members in each section
    for section in sheet_data_with_colors:
        sheet_data_with_colors[section]['members'].sort()

    # Pass the combined data to the function
    add_rows_and_fill_color(spreadsheet_id, sheet_data_with_colors)

def update_sirk_tracker_members():
    spreadsheet_id = get_sirk_tracker()
    tracker_sections = get_sheet_names(spreadsheet_id)
    sections = Section.objects.filter(is_active=True)
    sections_list = [section.upper() for section in sections.values_list('name', flat=True)]
    new_sections_list = [section for section in sections_list if section not in tracker_sections]

    if new_sections_list: 
        new_sections = Section.objects.filter(name__in=new_sections_list)
        sections_primary_colors = [hex_to_rgb(color) for color in sections.values_list('section_color', flat=True)]
        spreadsheet_template_id=config('SPREADSHEET_TEMPLATE_ID')
        copy_sheets(spreadsheet_template_id, config('SIRK_SECTION_TEMPLATE'), spreadsheet_id, new_sections, sections_primary_colors)
    
    existing_sheets_members = get_sheets_members(spreadsheet_id, sections_list)
    members = Member.objects.filter(is_active=True).filter(
                Q(position="Kasapi") | Q(position="Korespondente")
            ).order_by('last_name', 'first_name')
    
    new_members_dict = {}

    for member in members:
        section_name_upper = member.section.name.upper()
        sheet_members = existing_sheets_members.get(section_name_upper, [])

        if member.get_name() not in sheet_members:
            if section_name_upper not in new_members_dict:
                new_members_dict[section_name_upper] = []
            new_members_dict[section_name_upper].append(member.get_name())
    print(new_members_dict)
    if new_members_dict:
        update_sirk_tracker_with_new_members(spreadsheet_id, new_members_dict)
        update_2nd_to_last_row_formulas(spreadsheet_id, sections_list)

@shared_task
def create_APP_folder(app_info_id, gmail):
    try:
        app_info = get_object_or_404(APPInfo, pk=app_info_id)
        logger.info("Starting create_APP_folder_process...")
        app_info.sirk_folder_id = create_APP_folder_process(f"APP {app_info.year}")
        app_info.save()
        add_manager_and_set_permissions(app_info.sirk_folder_id, gmail)
        logger.info("Finished create_APP_folder_process, now running initialize_sirk_tracker...")
        
        initialize_sirk_tracker()
        
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        raise e  # Re-raise to ensure Celery can see the exception if needed


@shared_task
def update_db(spread_sheet_id, is_update_sirk_tracker):
    [ data, section_colors ] = get_members_data(spread_sheet_id)
    # Initialize counters and dictionaries
    section_abbreviations = {}
    section_counters = {}

    # First pass to determine the most used origin for each section and create/update sections
    for sheet_name, section_data in data.items():
        if sheet_name == "Lupong Patnugutan":
            continue

        origin_data = section_data['origin']
        origin_counts = Counter([item[0] for item in origin_data])
        most_common_origin = origin_counts.most_common(1)[0][0]
        section_abbreviations[sheet_name] = most_common_origin
        # primary_color = section_colors.get(sheet_name)['primary_color']
        # secondary_color = section_colors.get(sheet_name)['secondary_color']
        section_color = section_colors.get(sheet_name)
        # Create or update the Section
        section, created = Section.objects.get_or_create(
            name=most_common_origin,
            defaults={
                'full_name': sheet_name,
                'section_color': section_color
                # 'primary_color': primary_color,
                # 'secondary_color': secondary_color,
            }
        )

        if not created:
            # section.primary_color = primary_color
            # section.secondary_color = secondary_color
            section.section_color = section_color
            section.save()
            
        section_counters[sheet_name] = section

    # Mark all existing members as inactive
    Member.objects.all().update(is_active=False)

    # Second pass to add members
    for sheet_name, section_data in data.items():
        id_data = section_data['ID Number']
        name_data = section_data['name']
        position_data = section_data['position']
        
        if sheet_name == "Lupong Patnugutan":
            origin_data = section_data['origin']

            for i in range(len(id_data)):
                id_num = int(id_data[i][0])
                
                [ last_name, first_name, middle_initial ] = process_full_name(name_data[i][0])

                position = position_data[i][0]
                section_abbreviation = origin_data[i][0]
                section = Section.objects.get(name=section_abbreviation)

                # Create or update the Member
                Member.objects.update_or_create(
                    id_num=id_num,
                    defaults={
                        'last_name': last_name,
                        'first_name': first_name,
                        'middle_initial': middle_initial[0] if middle_initial else None,
                        'position': position,
                        'section': section,
                        'is_active': True,
                    }
                )
        else:
            section = section_counters[sheet_name]

            for i in range(len(id_data)):
                id_num = int(id_data[i][0])
                [ last_name, first_name, middle_initial ] = process_full_name(name_data[i][0])
                position = position_data[i][0]

                # Create or update the Member
                Member.objects.update_or_create(
                    id_num=id_num,
                    defaults={
                        'last_name': last_name,
                        'first_name': first_name,
                        'middle_initial': middle_initial[0] if middle_initial else None,
                        'position': position,
                        'section': section,
                        'is_active': True,
                    }
                )
    if APPInfo.objects.last() and is_update_sirk_tracker: update_sirk_tracker_members()