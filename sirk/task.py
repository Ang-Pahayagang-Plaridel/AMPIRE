from celery import shared_task
from collections import defaultdict
from django.shortcuts import get_object_or_404
from django.db.models import Q, Value, CharField, Case, When
from django.db.models.functions import Concat, Upper, Coalesce
from googleapiclient.errors import HttpError
from dateutil import parser
from decouple import config
import datetime, time, re

from gdrive.drive import get_drive_service, get_folder_id, get_folders, create_folder, get_image_files, find_gsheet_in_folder
from gsheets.sheets import get_text_in_row_2_from_column_c, add_text_to_first_blank_or_new_column, write_sirk_points_to_sheets, get_last_column_with_text, update_leaderboard
from AMPIRE.utils import handle_error, batch_callback, logger, hex_to_rgb

from .models import Issue, OnlinePoints
from admins.models import APPInfo, Member, Section

from admins.utils import lighten_color

def get_sirk_tracker():
    app_folder_id = APPInfo.objects.last().sirk_folder_id
    print("=================")
    print(app_folder_id)
    sirk_folder_id = get_folder_id("SIRKULASYON", app_folder_id)
    return find_gsheet_in_folder(sirk_folder_id, "ONLINE SIRK TRACKER")

def folder_exists(service, folder_name, parent_folder_id):
    """Check if a folder with the given name exists in the parent folder."""
    query = f"'{parent_folder_id}' in parents and name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    items = results.get('files', [])
    return items[0] if items else None

from django.http import HttpResponse
import time

def get_sirk_data():
    sirk = {}
    issue = Issue.objects.last()
    members = Member.objects.filter(
    is_active=True
        ).filter(
            Q(position="Kasapi") | Q(position="Korespondente")
        ).select_related('section').annotate(
            full_name=Concat(
                Upper('last_name'), 
                Value(', '), 
                'first_name',
                Case(
                    When(middle_initial__isnull=False, then=Concat(Value(' '), 'middle_initial', Value('.'))),
                    default=Value(''),
                    output_field=CharField()
                )
            )
        )
        # .annotate(full_name=Concat(Upper('last_name'), Value(', '), 'first_name'))
    print("members====================")
    for member in members:
        print(member.full_name)
    section_folders = get_folders(issue.folder_id)
    # print("section_folders====================")
    # print(section_folders)
    for section_folder in section_folders:
        section_name = re.sub(r'^\d+\.\s*', '', section_folder.get('name'))
        sirk_folders = get_folders(section_folder.get('id'))
        for sirk_folder in sirk_folders:
            rule = re.sub(r'^\d+\.\s*', '', sirk_folder.get('name'))
            online_sirk_rule = get_object_or_404(OnlinePoints, rule=rule)
            section_members_folders = get_folders(sirk_folder.get('id'))
            for section_members_folder in section_members_folders:
                    member = members.filter(full_name=section_members_folder.get('name')).last()
                    # print(section_members_folder.get('name'))
                    # print(member.get_name())
                    if member:
                        image_files = get_image_files(section_members_folder.get('id'))
                        for image_file in image_files:
                            sirk_pts = online_sirk_rule.value
                            if parser.parse(image_file.get('createdTime')) < issue.online_double_pts_end_date : sirk_pts *= 2
                            if member.get_name() in sirk:
                                sirk[member.get_name()]['points'] += sirk_pts
                            else:
                                sirk[member.get_name()] = {
                                    'points': sirk_pts,
                                    'section': member.section.name,
                                }
                            # print(sirk[member.get_name()])

    return sirk

@shared_task
def compute_sirk():
    issue = Issue.objects.last()
    if issue:
        if issue.is_online_ongoing() or issue.is_complete_online:
            print("compute sirk")
            logger.info("compute_sirk task is running.")
            sirk = get_sirk_data()
            print(sirk)
            # sirk = {
            #     'Zapata, Margaret L.': {'points': 324, 'section': 'Retrato'},
            #     'Rivera, Cherina Jewel R.': {'points': 572, 'section': 'Isports'},
            #     'Demoral, Aragorn M.': {'points': 653, 'section': 'Sining'},
            #     'Riguerra, Jemmiel Chriselle D.': {'points': 164, 'section': 'Sining'},
            #     'Besa, April Denise B.': {'points': 796, 'section': 'Sining'},
            #     'Villamora, Jazmine Daphnee C.': {'points': 115, 'section': 'Sining'},
            #     'Abas, Andrea Marie M.': {'points': 74, 'section': 'Retrato'},
            #     'Sadili, Carl Daniel C.': {'points': 40, 'section': 'Retrato'},
            #     'Fortaleza, Riezl Gayle C.': {'points': 79, 'section': 'Retrato'},
            #     'Arco, Gabrielle Mae V.': {'points': 23, 'section': 'Retrato'},
            #     'Soriano, Jessica Reigne M.': {'points': 50, 'section': 'Retrato'},
            #     'Panganiban, Eline Jann D.': {'points': 222, 'section': 'BNK'},
            #     'Garcia, Matthew Joshua D.': {'points': 992, 'section': 'BNK'},
            #     'Dela Paz, Quisha': {'points': 60, 'section': 'BNK'},
            #     'Tolentino, Lance Jeremiah G.': {'points': 39, 'section': 'Bayan'},
            #     'Revaula, Jeanine Cielsey I.': {'points': 144, 'section': 'Bayan'},
            #     'Bautista, Ryan Jesper R.': {'points': 710, 'section': 'Bayan'},
            #     'Pascual, Maria Francesca Josefina Patrocinia V.': {'points': 102, 'section': 'Bayan'},
            #     'Soto, Daniela Monica B.': {'points': 228, 'section': 'Bayan'},
            #     'Veloso, Francheska Kristine J.': {'points': 100, 'section': 'Bayan'},
            #     'Ferrer, Jill Pauline B.': {'points': 90, 'section': 'Bayan'},
            #     'Mateo, Kristina Editha L.': {'points': 208, 'section': 'Balita'},
            #     'Lu, Althea Julianne C.': {'points': 356, 'section': 'Balita'},
            #     'Aquino, Sly Nicole F.': {'points': 396, 'section': 'Balita'},
            #     'Basilio, Jay-Bell Freda Faye R.': {'points': 50, 'section': 'Balita'},
            #     'Pejo, Zeeriel Nathalie Joy S.': {'points': 128, 'section': 'Balita'},
            #     'Cortes, Pauline Anne S.': {'points': 108, 'section': 'Balita'},
            #     'Padilla, Trisha Isabella N.': {'points': 242, 'section': 'Balita'},
            #     'Gomez, Guilliane B.': {'points': 58, 'section': 'Balita'},
            #     'Nicdao, Francis Paul J.': {'points': 35, 'section': 'Balita'}
            # }
            spreadsheet_id = get_sirk_tracker()
            columnIndex = get_last_column_with_text(spreadsheet_id, Section.objects.filter(is_active=True).last().name.upper())
            write_sirk_points_to_sheets(spreadsheet_id, sirk, columnIndex)
            section_points = defaultdict(int)
            for member, data in sirk.items():
                section = data['section']
                points = data['points']
                section_points[section] += points

            # Step 2: Query the Section model to get the color codes
            sections = Section.objects.filter(name__in=section_points.keys()).values('name', 'section_color')

            # Step 3: Build section_colors dictionary
            section_colors = {}
            for section in sections:
                section_colors[section['name']] = {
                    'color_code': lighten_color(section['section_color'])
                }

            # Step 4: Create section_data with total points and color codes
            section_data = {}
            for section, points in section_points.items():
                secondary_color_rgb = hex_to_rgb(section_colors[section]['color_code'])
                section_data[section] = {
                    'total_points': points,
                    'color_code': secondary_color_rgb
                }
            logger.info(section_data)
            update_leaderboard(spreadsheet_id, sirk, section_data)

            if issue.is_final_online_date():
                issue.is_complete_online = True
                issue.save()
                
            logger.info("compute_sirk task is ending.")
        # Next Day Midnight run again
            
        
def create_main_folder(service, issue_name, parent_folder_id):
    online_sirk_folder_id = get_folder_id("01. ONLINE SIRK", parent_folder_id)
    online_sirk_folders = get_folders(online_sirk_folder_id)
    bilang = 1 if not online_sirk_folders else max(int(f['name'].split('.')[0]) for f in online_sirk_folders) + 1
    folder_name = f"{bilang:02d}. {issue_name.upper()}"
    existing_folder = folder_exists(service, folder_name, online_sirk_folder_id)
    return existing_folder['id'] if existing_folder else create_folder(service, folder_name, online_sirk_folder_id).get('id')

def create_section_folders(service, main_folder_id, sections):
    section_folders = {}
    for section in sections:
        section_name = section['name']
        existing_folder = folder_exists(service, section_name, main_folder_id)
        if existing_folder:
            section_folders[section_name] = existing_folder['id']
        else:
            section_folder = create_folder(service, section_name, main_folder_id)
            if section_folder:
                section_folders[section_name] = section_folder.get('id')
            else:
                logger.error(f"Failed to create section folder: {section_name}")
    return section_folders

def create_sirk_folders(service, section_folder_id, online_sirk):
    sirk_folders = {}
    for sirk in online_sirk:
        existing_folder = folder_exists(service, sirk, section_folder_id)
        if existing_folder:
            sirk_folders[sirk] = existing_folder['id']
        else:
            sirk_folder = create_folder(service, sirk, section_folder_id)
            if sirk_folder:
                sirk_folders[sirk] = sirk_folder.get('id')
            else:
                logger.error(f"Failed to create online sirk folder: {sirk}")
    return sirk_folders

def create_member_folders(service, sirk_folder_id, members, batch_size=50, max_retries=3):
    retries = 0
    while retries < max_retries:
        try:

            for i in range(0, len(members), batch_size):
                batch = service.new_batch_http_request(callback=batch_callback)
                for member in members[i:i + batch_size]:
                    logger.info(f"Attempting to create or find folder for member: {member}")

                    # Check if the member folder already exists
                    existing_folder = service.files().list(
                        q=f"name = '{member}' and '{sirk_folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder'",
                        corpora='drive',  # Use "drive" for shared drives
                        driveId=config('SHARED_DRIVE_ID'),  # Specify the driveId for the shared drive
                        includeItemsFromAllDrives=True,
                        supportsAllDrives=True,
                        fields='files(id, name)'
                    ).execute()

                    if existing_folder.get('files'):
                        logger.info(f"Member folder already exists: {member}")
                        continue

                    # Create the member folder
                    batch.add(service.files().create(body={
                        'name': member,
                        'mimeType': 'application/vnd.google-apps.folder',
                        'parents': [sirk_folder_id]
                    }, fields='id', supportsAllDrives=True))
                    
                batch.execute()
                logger.info(f"Executed batch for members {i} to {i + batch_size}")
                time.sleep(1)  # Add delay to prevent hitting limits
            return  # Exit if successful

        except HttpError as error:
            if error.resp.status == 404:
                logger.warning(f"Folder with ID {sirk_folder_id} not found. Retrying in 5 seconds...")
                time.sleep(5)  # Delay before retrying
                retries += 1
            elif error.resp.status == 403:
                logger.error(f"Permission denied: {error}")
                raise  # Cannot recover from a permission error
            else:
                logger.error(f"Failed to create member folders. Error: {error}")
                raise  # For other errors, raise the exception

    raise Exception(f"Failed to create member folders after {max_retries} retries.")

def add_isyu_in_sirk_tracker(issue_id):
    spreadsheet_id = get_sirk_tracker()
    sections_list = Section.objects.filter(is_active=True).values_list('name', flat=True)
    section_names = [section.upper() for section in sections_list if section.upper()]
    issue_list_sheets = get_text_in_row_2_from_column_c(spreadsheet_id, section_names[0])

    add_text_to_first_blank_or_new_column(spreadsheet_id, section_names, Issue.objects.last().name)

@shared_task(bind=True, max_retries=5, default_retry_delay=60)
def create_folders(self, issue_id, sections, online_sirk, parent_folder_id):
    add_isyu_in_sirk_tracker(issue_id)
    try:
        issue = get_object_or_404(Issue, pk=issue_id)
        service = get_drive_service()

        sirk_folder_id = get_folder_id("SIRKULASYON", parent_folder_id)
        # Create main folder
        main_folder_id = create_main_folder(service, issue.name, sirk_folder_id)
        if not main_folder_id:
            raise self.retry(exc=Exception("Failed to create main folder"))

        # Create section folders
        section_folders = create_section_folders(service, main_folder_id, sections)
        if not section_folders:
            raise self.retry(exc=Exception("Failed to create section folders"))

        # Create sirk folders and member folders for each section
        for section in sections:
            section_name = section['name']
            section_folder_id = section_folders.get(section_name)
            if not section_folder_id:
                continue

            sirk_folders = create_sirk_folders(service, section_folder_id, online_sirk)
            if not sirk_folders:
                raise self.retry(exc=Exception(f"Failed to create sirk folders for section {section_name}"))

            for sirk in online_sirk:
                sirk_folder_id = sirk_folders.get(sirk)
                if not sirk_folder_id:
                    continue

                create_member_folders(service, sirk_folder_id, section['members'])

        issue.folder_id = main_folder_id
        issue.save()
        
    except HttpError as error:
        if error.resp.status == 403 and 'rateLimitExceeded' in error.resp.reason:
            wait_time = 60  # Wait for 1 minute before retrying
            logger.warning(f'Quota exceeded, waiting for {wait_time} seconds...')
            time.sleep(wait_time)
            self.retry(exc=error)  # Retry the task
        elif error.resp.status == 404:
            logger.error(f"Folder not found: {error}")
            raise self.retry(exc=error)  # Retry the task with 404 handling
        else:
            logger.error(f'Unhandled error: {error}')
            raise self.retry(exc=error)  # Retry the task
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise self.retry(exc=e)  # Retry the task