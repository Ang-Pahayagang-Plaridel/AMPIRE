from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from django.conf import settings
import time

from AMPIRE.utils import logger

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def get_sheets_service():
    try:
        credentials = service_account.Credentials.from_service_account_file(
            settings.GOOGLE_CREDENTIALS_JSON, scopes=SCOPES)
        service = build('sheets', 'v4', credentials=credentials)
        return service
    except HttpError as error:
        logger.error(f"Failed to initialize Sheets service. Error: {error}")
        raise

def find_cells(spreadsheet_id, sheet_names, search_values, batch_size=100, max_retries=5, backoff_factor=2):
    service = get_sheets_service()

    valid_sheets = {}

    for sheet_name in sheet_names:
        search_results = {value: None for value in search_values}
        max_row_number = 0  # Track the highest row number found

        retries = 0
        while retries < max_retries:
            try:
                # Determine the number of rows in the sheet
                sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
                sheets = sheet_metadata.get('sheets', '')
                sheet_properties = next((s['properties'] for s in sheets if s['properties']['title'] == sheet_name), None)
                total_rows = sheet_properties['gridProperties']['rowCount'] if sheet_properties else 0

                for start_row in range(1, total_rows + 1, batch_size):
                    end_row = min(start_row + batch_size - 1, total_rows)
                    range_name = f"{sheet_name}!A{start_row}:Z{end_row}"

                    result = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
                    values = result.get('values', [])

                    for row_idx, row in enumerate(values):
                        for col_idx, cell_value in enumerate(row):
                            if cell_value in search_values:
                                col_letter = chr(ord('A') + col_idx)
                                row_number = start_row + row_idx
                                cell_reference = f"{sheet_name}!{col_letter}{row_number}"

                                # Update to the highest row number
                                if search_results[cell_value] is None or row_number > max_row_number:
                                    max_row_number = row_number
                                    search_results[cell_value] = cell_reference

                # Adjust all found cell references to the highest row number found
                if all(search_results[value] is not None for value in search_values):
                    for value in search_results:
                        col_letter = search_results[value].split('!')[1][0]  # Extract column letter
                        search_results[value] = f"{sheet_name}!{col_letter}{max_row_number}"
                    valid_sheets[sheet_name] = search_results

                break  # Exit the retry loop if successful

            except HttpError as error:
                if error.resp.status in [500, 503, 429]:
                    wait_time = backoff_factor ** retries
                    logger.warning(f"Internal server error occurred. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    retries += 1
                else:
                    logger.error(f"Failed to find cells in sheet '{sheet_name}'. Error: {error}")
                    break  # Break if it's not a retryable error

        if retries == max_retries:
            logger.error(f"Failed to find cells in sheet '{sheet_name}' after {max_retries} attempts.")

    return valid_sheets


def read_sheet_data(spreadsheet_id, range_names, max_retries=5, backoff_factor=2):
    service = get_sheets_service()
    sheet = service.spreadsheets()

    retries = 0
    while retries < max_retries:
        try:
            result = sheet.values().batchGet(spreadsheetId=spreadsheet_id, ranges=range_names).execute()
            value_ranges = result.get('valueRanges', [])

            data = {}
            for value_range in value_ranges:
                range_name = value_range['range']
                values = value_range.get('values', [])
                data[range_name] = values

            return data  # Return data if successful

        except HttpError as error:
            if error.resp.status in [500, 503, 429]:
                wait_time = backoff_factor * (2 ** retries)
                logger.warning(f"Internal server error occurred. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                retries += 1
            else:
                logger.error(f"Failed to read sheet data. Error: {error}")
                break  # Break if it's not a retryable error

    raise Exception(f"Failed to read sheet data after {max_retries} attempts.")

def update_sheet_data(spreadsheet_id, data, max_retries=5, backoff_factor=2):
    service = get_sheets_service()
    sheet = service.spreadsheets()

    retries = 0
    while retries < max_retries:
        try:
            requests = []
            for range_name, values in data.items():
                requests.append({
                    'range': range_name,
                    'values': values
                })
            body = {
                'valueInputOption': 'RAW',
                'data': requests
            }
            result = sheet.values().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
            return result  # Return result if successful

        except HttpError as error:
            if error.resp.status in [500, 503, 429]:
                wait_time = backoff_factor ** retries
                logger.warning(f"Internal server error occurred. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                retries += 1
            else:
                logger.error(f"Failed to update sheet data. Error: {error}")
                break  # Break if it's not a retryable error

    raise Exception(f"Failed to update sheet data after {max_retries} attempts.")

def get_sheet_names(spreadsheet_id, max_retries=5, backoff_factor=2):
    service = get_sheets_service()

    retries = 0
    while retries < max_retries:
        try:
            spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            sheets = spreadsheet.get('sheets', [])
            sheet_names = [sheet['properties']['title'] for sheet in sheets]
            return sheet_names  # Return sheet names if successful

        except HttpError as error:
            if error.resp.status in [500, 503, 429]:
                wait_time = backoff_factor ** retries
                logger.warning(f"Internal server error occurred. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                retries += 1
            else:
                logger.error(f"Failed to get sheet names. Error: {error}")
                break  # Break if it's not a retryable error

    raise Exception(f"Failed to get sheet names after {max_retries} attempts.")

def get_fill_colors(spreadsheet_id, range_names, max_retries=7, backoff_factor=3):
    print(range_names)
    service = get_sheets_service()
    sheet = service.spreadsheets()
    
    fill_colors = {}
    retries = 0
    
    while retries < max_retries:
        try:
            for range_name in range_names:
                sheet_name = range_name.split('!')[0]
                result = sheet.get(
                    spreadsheetId=spreadsheet_id, 
                    ranges=range_name, 
                    fields="sheets(data(rowData(values(effectiveFormat(backgroundColor)))))"
                ).execute()
                
                sheets = result.get('sheets', [])
                
                if sheets:
                    row_data = sheets[0].get('data', [])[0].get('rowData', [])
                    for row in row_data:
                        cell = row.get('values', [])[0]
                        background_color = cell.get('effectiveFormat', {}).get('backgroundColor', {})
                        fill_colors[range_name] = background_color

            return fill_colors  # Return results if successful

        except HttpError as error:
            if error.resp.status in [500, 503, 429]:  # Handle server errors and rate limiting
                wait_time = backoff_factor ** retries
                logger.warning(f"Rate limit exceeded or server error occurred. Retrying in {wait_time} seconds...")
                logger.warning(f"Error details: {error}")
                time.sleep(wait_time)
                retries += 1
            else:
                logger.error(f"Failed to get fill colors. Error: {error}")
                raise  # Re-raise the error if it's not a retryable error
    
    raise Exception(f"Failed to get fill colors after {max_retries} attempts.")

def get_sheet_id_by_name(spreadsheet_id, sheet_name, max_retries=5, backoff_factor=2):
    service = get_sheets_service()
    retries = 0

    while retries < max_retries:
        try:
            # Fetch the spreadsheet metadata
            spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            for sheet in spreadsheet.get('sheets', []):
                if sheet['properties']['title'] == sheet_name:
                    return sheet['properties']['sheetId']
            logger.warning(f"Sheet '{sheet_name}' not found in spreadsheet '{spreadsheet_id}'.")
            return None

        except HttpError as error:
            if error.resp.status in [500, 503, 429]:
                wait_time = backoff_factor ** retries + random.uniform(0, 1)
                logger.warning(f"Internal server error occurred. Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
                retries += 1
            else:
                logger.error(f"Failed to retrieve sheet ID for '{sheet_name}'. Error: {error}")
                break

    if retries == max_retries:
        logger.error(f"Failed to retrieve sheet ID for '{sheet_name}' after {max_retries} attempts.")
        raise Exception(f"Failed to retrieve sheet ID for '{sheet_name}' after {max_retries} attempts.")
    
def copy_sheets(source_spreadsheet_id, sheet_id, destination_spreadsheet_id, new_sheet_names, colors):
    service = get_sheets_service()
    new_sheet_ids = []
    batch_requests = []

    for new_sheet_name, color in zip(new_sheet_names, colors):
        # Copy the sheet to the destination spreadsheet
        copied_sheet = service.spreadsheets().sheets().copyTo(
            spreadsheetId=source_spreadsheet_id,
            sheetId=sheet_id,
            body={'destinationSpreadsheetId': destination_spreadsheet_id}
        ).execute()

        new_sheet_id = copied_sheet['sheetId']
        new_sheet_ids.append(new_sheet_id)

        # Get the row count for the newly copied sheet
        sheet_properties = service.spreadsheets().get(spreadsheetId=destination_spreadsheet_id).execute()
        for sheet in sheet_properties['sheets']:
            if sheet['properties']['sheetId'] == new_sheet_id:
                row_count = sheet['properties']['gridProperties']['rowCount']
                break

        # Prepare batch requests for renaming the sheet, setting the tab color, and applying the fill color
        batch_requests.append({
            'updateSheetProperties': {
                'properties': {
                    'sheetId': new_sheet_id,
                    'title': new_sheet_name,
                    'tabColor': color
                },
                'fields': 'title,tabColor'
            }
        })

        # Apply fill color to first and last rows
        batch_requests.extend([
            {
                "repeatCell": {
                    "range": {
                        "sheetId": new_sheet_id,  # Use the new sheet ID
                        "startRowIndex": 0,
                        "endRowIndex": 1
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": color
                        }
                    },
                    "fields": "userEnteredFormat.backgroundColor"
                }
            },
            {
                "repeatCell": {
                    "range": {
                        "sheetId": new_sheet_id,  # Use the new sheet ID
                        "startRowIndex": row_count - 1,
                        "endRowIndex": row_count
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": color
                        }
                    },
                    "fields": "userEnteredFormat.backgroundColor"
                }
            }
        ])

    # Execute the batch update for all sheets
    if batch_requests:
        service.spreadsheets().batchUpdate(
            spreadsheetId=destination_spreadsheet_id,
            body={"requests": batch_requests}
        ).execute()

    return new_sheet_ids


def add_rows_and_fill_color(spreadsheet_id, sheet_data_with_colors, max_retries=5, backoff_factor=2):
    service = get_sheets_service()

    for sheet_name, data in sheet_data_with_colors.items():
        text_list = data['members']
        fill_color = data['secondary_color']
        num_new_rows = len(text_list)
        retries = 0

        while retries < max_retries:
            try:
                # Get the sheet ID and sheet properties
                spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
                sheet = next(sheet for sheet in spreadsheet['sheets'] if sheet['properties']['title'] == sheet_name)
                sheet_id = sheet['properties']['sheetId']
                row_count = 2  # Start adding new rows after row 2 (i.e., at row 3)
                col_count = sheet['properties']['gridProperties']['columnCount']

                second_last_col_index = col_count - 2
                third_last_col_index = col_count - 3

                sum_range_start = 'C'
                sum_range_end = chr(65 + third_last_col_index)  # Convert column index to letter

                # Step 1: Add the new rows starting from row 3
                requests = [{
                    "insertDimension": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "ROWS",
                            "startIndex": row_count,
                            "endIndex": row_count + num_new_rows
                        },
                        "inheritFromBefore": False
                    }
                }]

                # Step 2: Prepare the batch update to insert the text in column B, apply the fill color, and insert the formula
                for i, text in enumerate(text_list):
                    row_index = row_count + i
                    formula = f"=SUM({sum_range_start}{row_index + 1}:{sum_range_end}{row_index + 1})"
                    
                    requests.append({
                        "updateCells": {
                            "rows": [
                                {
                                    "values": [
                                        {"userEnteredValue": {}},  # Leave column A (index 0) blank
                                        {
                                            "userEnteredValue": {"stringValue": text},
                                            "userEnteredFormat": {
                                                "backgroundColor": fill_color,
                                                "wrapStrategy": "WRAP"
                                            }
                                        },
                                        *[{"userEnteredValue": {}} for _ in range(2, second_last_col_index)],
                                        {"userEnteredValue": {"formulaValue": formula}},  # Add the formula in the second-to-last column
                                    ]
                                }
                            ],
                            "fields": "userEnteredValue,userEnteredFormat.backgroundColor,userEnteredFormat.wrapStrategy",
                            "start": {"sheetId": sheet_id, "rowIndex": row_index, "columnIndex": 0}
                        }
                    })

                # Step 3: After creating the rows, add a formula in the second-to-last column after the last row
                final_row_index = row_count + num_new_rows
                sum_formula = f"=SUM({chr(65 + second_last_col_index)}{row_count + 1}:{chr(65 + second_last_col_index)}{final_row_index})"
                
                requests.append({
                    "updateCells": {
                        "rows": [
                            {
                                "values": [
                                    {"userEnteredValue": {"formulaValue": sum_formula}}
                                ]
                            }
                        ],
                        "fields": "userEnteredValue",
                        "start": {"sheetId": sheet_id, "rowIndex": final_row_index, "columnIndex": second_last_col_index}
                    }
                })

                # Apply the batch update
                service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body={"requests": requests}
                ).execute()

                logger.info(f"Successfully added {num_new_rows} rows and applied fill color to sheet '{sheet_name}'.")
                break

            except HttpError as error:
                if error.resp.status in [500, 503, 429]:
                    wait_time = backoff_factor ** retries
                    logger.warning(f"Internal server error occurred. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    retries += 1
                else:
                    logger.error(f"Failed to add rows to sheet '{sheet_name}'. Error: {error}")
                    break

        if retries == max_retries:
            logger.error(f"Failed to add rows to sheet '{sheet_name}' after {max_retries} attempts.")
            raise Exception(f"Failed to add rows to sheet '{sheet_name}' after {max_retries} attempts.")


def get_text_in_row_2_from_column_c(spreadsheet_id, sheet_name, max_retries=5, backoff_factor=2):
    service = get_sheets_service()
    retries = 0

    while retries < max_retries:
        try:
            # Get the sheet metadata to determine the last column
            spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            sheet = next(sheet for sheet in spreadsheet['sheets'] if sheet['properties']['title'] == sheet_name)
            col_count = sheet['properties']['gridProperties']['columnCount']

            # Determine the last column letter dynamically
            last_col_letter = chr(65 + col_count - 1)
            range_name = f"{sheet_name}!C2:{last_col_letter}2"

            # Get the values from the specified range
            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()

            values = result.get('values', [])
            if not values:
                logger.warning(f"No data found in row 2 starting from column C in sheet '{sheet_name}'.")
                return []
            
            # Extract values until "Total" is found
            row_values = values[0]
            result_list = []
            for value in row_values:
                if value == "Total":
                    break
                result_list.append(value)
            
            return result_list

        except HttpError as error:
            if error.resp.status in [500, 503, 429]:
                wait_time = backoff_factor ** retries
                logger.warning(f"Internal server error occurred. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                retries += 1
            else:
                logger.error(f"Failed to get text in row 2 from column C in sheet '{sheet_name}'. Error: {error}")
                break

    if retries == max_retries:
        logger.error(f"Failed to get text in row 2 from column C in sheet '{sheet_name}' after {max_retries} attempts.")
        raise Exception(f"Failed to get text in row 2 from column C in sheet '{sheet_name}' after {max_retries} attempts.")
    
def add_text_to_first_blank_or_new_column(spreadsheet_id, sheet_names, new_text, max_retries=5, backoff_factor=2):
    service = get_sheets_service()
    spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()

    batch_requests = []

    for sheet_name in sheet_names:
        try:
            sheet = next(sheet for sheet in spreadsheet['sheets'] if sheet['properties']['title'] == sheet_name)
            sheet_id = sheet['properties']['sheetId']
            row_count = sheet['properties']['gridProperties']['rowCount']
            col_count = sheet['properties']['gridProperties']['columnCount']

            # Define the range starting from column C (i.e., column 3) in row 2
            range_name = f"{sheet_name}!C2:{chr(65 + col_count - 1)}2"

            # Get the values from the specified range
            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()

            values = result.get('values', [])
            if not values:
                logger.warning(f"No data found in row 2 in sheet '{sheet_name}'.")
                continue

            row_values = values[0]

            # Start checking from column C (i.e., index 2)
            target_col_index = None
            for i, value in enumerate(row_values):
                if value == '':
                    target_col_index = i + 2  # Offset by 2 because the range starts from column C (index 2)
                    break

            if target_col_index is None:
                # No blank cell found, so we need to handle the "Total" column
                if "Total" in row_values:
                    total_index = row_values.index("Total")
                    target_col_index = total_index + 2  # Offset for "Total" position in column C

                    # Insert a new column just before the "Total" column
                    batch_requests.append({
                        "insertDimension": {
                            "range": {
                                "sheetId": sheet_id,
                                "dimension": "COLUMNS",
                                "startIndex": target_col_index,
                                "endIndex": target_col_index + 1
                            },
                            "inheritFromBefore": True
                        }
                    })
                else:
                    # If "Total" is not found, just add a new column after the last column
                    target_col_index = len(row_values) + 2  # Adjust for column C offset

            target_col_letter = chr(65 + target_col_index)

            # Prepare the request to update the cell with new text
            batch_requests.append({
                "updateCells": {
                    "rows": [
                        {
                            "values": [
                                {"userEnteredValue": {"stringValue": new_text}}
                            ]
                        }
                    ],
                    "fields": "userEnteredValue",
                    "start": {"sheetId": sheet_id, "rowIndex": 1, "columnIndex": target_col_index}
                }
            })

            # Determine the range for the SUM formula
            second_last_row_index = row_count - 2
            sum_formula = f"=SUM({target_col_letter}3:{target_col_letter}{second_last_row_index})"

            # Add the SUM formula to the second-to-last row of the target column
            batch_requests.append({
                "updateCells": {
                    "rows": [
                        {
                            "values": [
                                {"userEnteredValue": {"formulaValue": sum_formula}}
                            ]
                        }
                    ],
                    "fields": "userEnteredValue",
                    "start": {"sheetId": sheet_id, "rowIndex": second_last_row_index, "columnIndex": target_col_index}
                }
            })

        except HttpError as error:
            logger.error(f"Failed to process sheet '{sheet_name}'. Error: {error}")
            continue

    if batch_requests:
        retries = 0
        while retries < max_retries:
            try:
                service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body={"requests": batch_requests}
                ).execute()
                logger.info(f"Successfully updated sheets with new text and SUM formulas.")
                break
            except HttpError as error:
                if error.resp.status in [500, 503, 429]:
                    wait_time = backoff_factor ** retries
                    logger.warning(f"Internal server error occurred. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    retries += 1
                else:
                    logger.error(f"Failed to batch update sheets. Error: {error}")
                    break

        if retries == max_retries:
            logger.error(f"Failed to batch update sheets after {max_retries} attempts.")
            raise Exception(f"Failed to batch update sheets after {max_retries} attempts.")

        
import random


def exponential_backoff_with_jitter(retries, backoff_factor=2, jitter=0.5):
    """Calculate backoff time with jitter."""
    base = backoff_factor ** retries
    return base + random.uniform(0, jitter * base)

def write_sirk_points_to_sheets(spreadsheet_id, sirk_data, columnIndex, max_retries=5, backoff_factor=2, jitter=0.5):
    service = get_sheets_service()

    # Get the spreadsheet metadata to retrieve sheet IDs
    retries = 0
    while retries < max_retries:
        try:
            spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            sheet_id_map = {sheet['properties']['title']: sheet['properties']['sheetId'] for sheet in spreadsheet['sheets']}
            break
        except HttpError as error:
            if error.resp.status in [500, 503, 429]:
                wait_time = exponential_backoff_with_jitter(retries, backoff_factor, jitter)
                logger.warning(f"Quota exceeded or server error occurred. Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
                retries += 1
            else:
                logger.error(f"Failed to retrieve spreadsheet metadata. Error: {error}")
                raise Exception(f"Failed to retrieve spreadsheet metadata after {max_retries} attempts.")
    if retries == max_retries:
        raise Exception(f"Failed to retrieve spreadsheet metadata after {max_retries} attempts.")

    batch_requests = []

    for member_name, data in sirk_data.items():
        section = data['section']
        points = data['points']
        sheet_name = section.upper()

        # Retrieve the sheet ID from the metadata
        sheet_id = sheet_id_map.get(sheet_name)
        if not sheet_id:
            logger.warning(f"Sheet '{sheet_name}' not found in the spreadsheet.")
            continue

        try:
            # Get the names in column B to find the row index for the member
            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!B2:B"
            ).execute()
            values = result.get('values', [])

            if not values:
                logger.warning(f"No data found in column B in sheet '{sheet_name}'.")
                continue

            # Find the row where the member's name appears
            for row_idx, row in enumerate(values, start=2):
                if row and row[0].strip().upper() == member_name.upper():
                    # Prepare the request to update the points in column C
                    batch_requests.append({
                        "updateCells": {
                            "rows": [
                                {
                                    "values": [
                                        {"userEnteredValue": {"numberValue": points}}
                                    ]
                                }
                            ],
                            "fields": "userEnteredValue",
                            "start": {"sheetId": sheet_id, "rowIndex": row_idx - 1, "columnIndex": columnIndex}  # Column C is index 2
                        }
                    })
                    logger.info(f"Prepared update for '{member_name}' in section '{sheet_name}'.")
                    break  # Exit the loop once the member is found

        except HttpError as error:
            logger.error(f"Failed to prepare update for '{member_name}' in section '{sheet_name}'. Error: {error}")

    # Execute the batch update
    if batch_requests:
        retries = 0
        while retries < max_retries:
            try:
                service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body={"requests": batch_requests}
                ).execute()
                logger.info("Successfully updated points for all members.")
                break
            except HttpError as error:
                if error.resp.status in [500, 503, 429]:
                    wait_time = exponential_backoff_with_jitter(retries, backoff_factor, jitter)
                    logger.warning(f"Quota exceeded or server error occurred. Retrying in {wait_time:.2f} seconds...")
                    time.sleep(wait_time)
                    retries += 1
                else:
                    logger.error(f"Failed to execute batch update. Error: {error}")
                    break

        if retries == max_retries:
            logger.error(f"Failed to update points after {max_retries} attempts.")
            raise Exception(f"Failed to update points after {max_retries} attempts.")

def get_last_column_with_text(spreadsheet_id, sheet_name, max_retries=5, backoff_factor=2, jitter=0.5):
    service = get_sheets_service()
    retries = 0

    while retries < max_retries:
        try:
            # Get the sheet metadata to determine the number of columns
            spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            sheet = next(sheet for sheet in spreadsheet['sheets'] if sheet['properties']['title'] == sheet_name)
            col_count = sheet['properties']['gridProperties']['columnCount']

            # Define the range to fetch data from row 2 starting from column C to the 3rd to last column
            third_last_col_letter = chr(65 + col_count - 3)
            range_name = f"{sheet_name}!C2:{third_last_col_letter}2"

            # Get the values from the specified range
            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()

            values = result.get('values', [])
            if not values or not values[0]:
                logger.warning(f"No data found in row 2 from column C in sheet '{sheet_name}'.")
                return None

            row_values = values[0]

            # Iterate through columns in the specified range to find the last column with text
            last_col_index = 2  # Start counting from column C, which is index 2
            for i, value in enumerate(row_values):
                if value.strip():
                    last_col_index = i + 2  # Adjusting to start index at 2 for column C
                else:
                    break  # Stop at the first empty column

            return last_col_index

        except HttpError as error:
            if error.resp.status in [500, 503, 429]:
                wait_time = exponential_backoff_with_jitter(retries, backoff_factor, jitter)
                logger.warning(f"Internal server error or quota exceeded. Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
                retries += 1
            else:
                logger.error(f"Failed to get the last column with text in row 2 for sheet '{sheet_name}'. Error: {error}")
                break

    if retries == max_retries:
        logger.error(f"Failed to get the last column with text in row 2 for sheet '{sheet_name}' after {max_retries} attempts.")
        raise Exception(f"Failed to get the last column with text in row 2 for sheet '{sheet_name}' after {max_retries} attempts.")

def update_leaderboard(spreadsheet_id, sirk_data, section_data, max_retries=5, backoff_factor=2, jitter=0.5):
    service = get_sheets_service()

    # Sort members by scores
    sorted_members = sorted(sirk_data.items(), key=lambda x: x[1]['points'], reverse=True)[:5]

    # Sort sections by total points
    sorted_sections = sorted(section_data.items(), key=lambda x: x[1]['total_points'], reverse=True)[:5]

    # Format the current time
    updated_time = time.strftime("%Y/%m/%d %I:%M %p", time.localtime())

    retries = 0
    while retries < max_retries:
        try:
            # Get the sheet ID
            sheet_id = get_sheet_id_by_name(spreadsheet_id, "LEADERBOARD")

            # Prepare the requests for clearing and updating
            requests = []

            # Clear the relevant cells (B4:B8, C4:C8, E4:E8, F4:F8)
            requests.append({
                "updateCells": {
                    "range": {"sheetId": sheet_id, "startRowIndex": 3, "endRowIndex": 8, "startColumnIndex": 1, "endColumnIndex": 6},
                    "fields": "userEnteredValue,userEnteredFormat.backgroundColor"
                }
            })

            # Prepare the data to update in the leaderboard sheet
            for i in range(len(sorted_members)):
                member_name = sorted_members[i][0]
                member_score = sorted_members[i][1]['points']
                member_section = sorted_members[i][1]['section']
                member_color = section_data[member_section]['color_code']  # Fetch color from section_data

                requests.append({
                    "updateCells": {
                        "rows": [
                            {
                                "values": [
                                    {
                                        "userEnteredValue": {"stringValue": member_name},
                                        "userEnteredFormat": {"backgroundColor": member_color}
                                    }
                                ]
                            }
                        ],
                        "fields": "userEnteredValue,userEnteredFormat.backgroundColor",
                        "start": {"sheetId": sheet_id, "rowIndex": 3 + i, "columnIndex": 1}  # B4-B8
                    }
                })

                requests.append({
                    "updateCells": {
                        "rows": [
                            {
                                "values": [
                                    {
                                        "userEnteredValue": {"numberValue": member_score},
                                        "userEnteredFormat": {"backgroundColor": member_color}
                                    }
                                ]
                            }
                        ],
                        "fields": "userEnteredValue,userEnteredFormat.backgroundColor",
                        "start": {"sheetId": sheet_id, "rowIndex": 3 + i, "columnIndex": 2}  # C4-C8
                    }
                })

            for i in range(len(sorted_sections)):
                section_name = sorted_sections[i][0]
                section_score = sorted_sections[i][1]['total_points']
                section_color = sorted_sections[i][1]['color_code']

                requests.append({
                    "updateCells": {
                        "rows": [
                            {
                                "values": [
                                    {
                                        "userEnteredValue": {"stringValue": section_name},
                                        "userEnteredFormat": {"backgroundColor": section_color}
                                    }
                                ]
                            }
                        ],
                        "fields": "userEnteredValue,userEnteredFormat.backgroundColor",
                        "start": {"sheetId": sheet_id, "rowIndex": 3 + i, "columnIndex": 4}  # E4-E8
                    }
                })

                requests.append({
                    "updateCells": {
                        "rows": [
                            {
                                "values": [
                                    {
                                        "userEnteredValue": {"numberValue": section_score},
                                        "userEnteredFormat": {"backgroundColor": section_color}
                                    }
                                ]
                            }
                        ],
                        "fields": "userEnteredValue,userEnteredFormat.backgroundColor",
                        "start": {"sheetId": sheet_id, "rowIndex": 3 + i, "columnIndex": 5}  # F4-F8
                    }
                })

            # Update the timestamp in D2
            requests.append({
                "updateCells": {
                    "rows": [
                        {
                            "values": [
                                {
                                    "userEnteredValue": {"stringValue": updated_time},
                                }
                            ]
                        }
                    ],
                    "fields": "userEnteredValue",
                    "start": {"sheetId": sheet_id, "rowIndex": 1, "columnIndex": 4}  # E2
                }
            })

            # Execute the batch update
            service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={"requests": requests}
            ).execute()

            logger.info("Leaderboard successfully updated.")
            break

        except HttpError as error:
            if error.resp.status in [500, 503, 429]:
                wait_time = exponential_backoff_with_jitter(retries, backoff_factor, jitter)
                logger.warning(f"Internal server error or quota exceeded. Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
                retries += 1
            else:
                logger.error(f"Failed to update the leaderboard. Error: {error}")
                break

    if retries == max_retries:
        logger.error("Failed to update the leaderboard after max retries.")
        raise Exception("Failed to update the leaderboard after max retries.")
    
def get_sheets_members(spreadsheet_id, sheet_names, max_retries=5, backoff_factor=2):
    service = get_sheets_service()
    all_texts = {}

    for sheet_name in sheet_names:
        retries = 0
        while retries < max_retries:
            try:
                # Get the sheet's row count
                sheet_metadata = service.spreadsheets().get(
                    spreadsheetId=spreadsheet_id,
                    ranges=[f"{sheet_name}!B:B"],
                    fields="sheets(properties(gridProperties(rowCount)))"
                ).execute()

                row_count = sheet_metadata['sheets'][0]['properties']['gridProperties']['rowCount']

                # Define the range for column B from B3 to B(2nd last row)
                range_name = f"{sheet_name}!B3:B{row_count-1}"

                # Get the values from the specified range
                result = service.spreadsheets().values().get(
                    spreadsheetId=spreadsheet_id,
                    range=range_name
                ).execute()

                values = result.get('values', [])
                all_texts[sheet_name] = [value[0] for value in values if value]

                break

            except HttpError as error:
                if error.resp.status in [500, 503, 429]:
                    wait_time = backoff_factor ** retries
                    print(f"Internal server error occurred. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    retries += 1
                else:
                    print(f"Failed to retrieve data from sheet '{sheet_name}'. Error: {error}")
                    break

    return all_texts

def update_sirk_tracker_with_new_members(spreadsheet_id, new_members_dict, max_retries=5, backoff_factor=2):
    service = get_sheets_service()
    batch_update_requests = []

    for section_name, new_members in new_members_dict.items():
        retries = 0
        while retries < max_retries:
            try:
                # Get the sheet ID and metadata
                sheet_metadata = service.spreadsheets().get(
                    spreadsheetId=spreadsheet_id,
                    ranges=[f"{section_name}!A1"],
                    fields="sheets(properties(sheetId,gridProperties(rowCount,columnCount)))"
                ).execute()

                sheet = sheet_metadata['sheets'][0]
                sheet_id = sheet['properties']['sheetId']
                row_count = sheet['properties']['gridProperties']['rowCount']
                col_count = sheet['properties']['gridProperties']['columnCount']

                # Get existing members in the sheet
                existing_members_range = f"{section_name}!B3:B{row_count - 2}"
                existing_members = service.spreadsheets().values().get(
                    spreadsheetId=spreadsheet_id,
                    range=existing_members_range
                ).execute().get('values', [])
                
                # Flatten existing_members list and clean up the data
                existing_members = [name[0] for name in existing_members if name]

                # Track how many rows we've inserted
                inserted_rows = 0

                # Add each new member in alphabetical order
                for member_name in new_members:
                    insert_position = next(
                        (index for index, name in enumerate(existing_members) if member_name < name),
                        len(existing_members)
                    )
                    existing_members.insert(insert_position, member_name)
                    
                    # Insert new row at the calculated position
                    row_index = insert_position + 2 + inserted_rows  # Adding 2 to start at B3, add inserted_rows to keep track
                    
                    batch_update_requests.append({
                        "insertDimension": {
                            "range": {
                                "sheetId": sheet_id,
                                "dimension": "ROWS",
                                "startIndex": row_index,
                                "endIndex": row_index + 1
                            },
                            "inheritFromBefore": False
                        }
                    })

                    # Add the new member's name to the correct position in column B
                    batch_update_requests.append({
                        "updateCells": {
                            "rows": [
                                {
                                    "values": [
                                        {"userEnteredValue": {"stringValue": member_name}}
                                    ]
                                }
                            ],
                            "fields": "userEnteredValue",
                            "start": {"sheetId": sheet_id, "rowIndex": row_index, "columnIndex": 1}
                        }
                    })

                    # Add SUM formula in the 2nd-to-last column for the new row
                    sum_formula = f"=SUM(C{row_index + 1}:{chr(65 + col_count - 3)}{row_index + 1})"
                    batch_update_requests.append({
                        "updateCells": {
                            "rows": [
                                {
                                    "values": [
                                        {"userEnteredValue": {"formulaValue": sum_formula}}
                                    ]
                                }
                            ],
                            "fields": "userEnteredValue",
                            "start": {"sheetId": sheet_id, "rowIndex": row_index, "columnIndex": col_count - 2}
                        }
                    })

                    inserted_rows += 1

                # Execute the batch update request
                service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body={"requests": batch_update_requests}
                ).execute()

                print(f"Successfully added new members to '{section_name}' and inserted SUM formulas.")
                break

            except HttpError as error:
                if error.resp.status in [500, 503, 429]:
                    wait_time = backoff_factor ** retries
                    print(f"Server error or quota limit reached. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    retries += 1
                else:
                    print(f"Failed to update sheet '{section_name}'. Error: {error}")
                    break

        if retries == max_retries:
            raise Exception(f"Failed to update sheet '{section_name}' after {max_retries} attempts.")
        
def update_2nd_to_last_row_formulas(spreadsheet_id, sheet_names, max_retries=5, backoff_factor=2):
    service = get_sheets_service()
    batch_update_requests = []

    for section_name in sheet_names:
        retries = 0
        while retries < max_retries:
            try:
                # Get the sheet ID and metadata
                sheet_metadata = service.spreadsheets().get(
                    spreadsheetId=spreadsheet_id,
                    ranges=[f"{section_name}!A1"],
                    fields="sheets(properties(sheetId,gridProperties(rowCount,columnCount)))"
                ).execute()

                sheet = sheet_metadata['sheets'][0]
                sheet_id = sheet['properties']['sheetId']
                row_count = sheet['properties']['gridProperties']['rowCount']
                col_count = sheet['properties']['gridProperties']['columnCount']

                second_last_row = row_count - 2
                third_last_row = row_count - 3

                # Get all values in the 2nd-to-last row
                second_last_row_range = f"{section_name}!C{second_last_row + 1}:{chr(65 + col_count - 1)}{second_last_row + 1}"
                values_2nd_last_row = service.spreadsheets().values().get(
                    spreadsheetId=spreadsheet_id,
                    range=second_last_row_range,
                    valueRenderOption='FORMULA'  # Fetch the formulas, if they exist
                ).execute().get('values', [])

                print(f"Checking formulas in '{section_name}':\nSecond last row values: {values_2nd_last_row}")

                if values_2nd_last_row:
                    for col_index in range(2, col_count):
                        current_col_letter = chr(65 + col_index)
                        
                        if len(values_2nd_last_row[0]) > col_index - 2:
                            current_value = values_2nd_last_row[0][col_index - 2]
                        else:
                            current_value = ''

                        expected_formula = f"=SUM({current_col_letter}3:{current_col_letter}{third_last_row + 1})"

                        # Check if the value is a formula or a number
                        if current_value.startswith('='):
                            # It's a formula, check if it needs updating
                            if current_value != expected_formula:
                                print(f"Updating formula in {current_col_letter}{second_last_row + 1}: {expected_formula}")
                                batch_update_requests.append({
                                    "updateCells": {
                                        "rows": [
                                            {
                                                "values": [
                                                    {"userEnteredValue": {"formulaValue": expected_formula}}
                                                ]
                                            }
                                        ],
                                        "fields": "userEnteredValue",
                                        "start": {"sheetId": sheet_id, "rowIndex": second_last_row, "columnIndex": col_index}
                                    }
                                })

                if batch_update_requests:
                    # Execute the batch update request
                    service.spreadsheets().batchUpdate(
                        spreadsheetId=spreadsheet_id,
                        body={"requests": batch_update_requests}
                    ).execute()
                    print(f"Successfully updated formulas in '{section_name}'.")
                else:
                    print(f"No formulas to update in '{section_name}'.")

                break

            except HttpError as error:
                if error.resp.status in [500, 503, 429]:
                    wait_time = backoff_factor ** retries
                    print(f"Server error or quota limit reached. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    retries += 1
                else:
                    print(f"Failed to update formulas in sheet '{section_name}'. Error: {error}")
                    break

        if retries == max_retries:
            raise Exception(f"Failed to update formulas in sheet '{section_name}' after {max_retries} attempts.")
