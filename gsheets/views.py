from django.shortcuts import render
import re

from . import sheets

from AMPIRE.utils import rgb_to_hex

# Create your views here.

def increment_cell(cell_ref):
    match = re.match(r"([A-Z]+)(\d+)", cell_ref)
    if match:
        column, row = match.groups()
        new_row = int(row) + 1
        return f"{column}{new_row}"
    else:
        raise ValueError("Invalid cell reference format")
    
def get_column(cell_ref):
    match = re.match(r"([A-Z]+)(\d+)", cell_ref)
    if match:
        column, _ = match.groups()
        return column
    else:
        raise ValueError("Invalid cell reference format")

def create_range(input_str):
    # Split the input string to extract the relevant parts
    parts = input_str.split('!')
    prefix = parts[0]
    cell = parts[1]
    
    # Extract the column and row number from the cell reference
    col = ''.join(filter(str.isalpha, cell))
    row = int(''.join(filter(str.isdigit, cell)))
    
    # Increment the row number by 1
    new_row = row + 1
    
    # Create the new range string
    new_range = f"{prefix}!{col}{new_row}:{col}"
    
    return new_range

def arrange_data_by_sheets(sheet_data, header_values):
    arranged_data = {}

    for sheet_range, values in sheet_data.items():
        # Extract the sheet name from the range
        raw_sheet_name = sheet_range.split('!')[0].strip("'")
        # Remove numbers and periods
        sheet_name = re.sub(r'^\d+\.\s*', '', raw_sheet_name)

        if sheet_name not in arranged_data : arranged_data[sheet_name] = {}
            # arranged_data[sheet_name] = {
            #     'ID Number': [],
            #     'name': [],
            #     'position': [],
            #     'origin': []
            # }

        # Determine the type of data based on the order of the range
        index = list(sheet_data.keys()).index(sheet_range) % len(header_values)

        if index == 0:
            arranged_data[sheet_name]['ID Number'] = values
        elif index == 1:
            arranged_data[sheet_name]['name'] = values
        elif index == 2:
            arranged_data[sheet_name]['position'] = values
        elif index == 3:
            arranged_data[sheet_name]['origin'] = values

    return arranged_data

def get_first_stated_range(range_list):
    first_ranges = []
    seen_sheets = set()
    
    for full_range in range_list:
        sheet_name = full_range.split('!')[0]
        
        if sheet_name not in seen_sheets:
            # Include A1 cell for each sheet
            first_ranges.append(f"{sheet_name}!A1")
            seen_sheets.add(sheet_name)

    return first_ranges

from AMPIRE.utils import logger

def reformat_colors(fill_colors):
    logger.info(fill_colors)
    hex_colors = {}
    
    for cell_reference, color in fill_colors.items():
        # Extract the sheet name and cell part (e.g., A1 or B5)
        sheet_name, cell = cell_reference.split('!')
        
        # Remove any prefix (e.g., "01. ") from the sheet name
        sheet_name = sheet_name.split('. ', 1)[-1]
        
        # Convert the RGB color to HEX
        hex_color = rgb_to_hex(color)
        
        # Determine if it's primary (A1) or secondary (B5) color
        if sheet_name not in hex_colors:
            hex_colors[sheet_name] = {}
        
        if cell == 'A1':
            hex_colors[sheet_name] = hex_color
    
    return hex_colors

def get_members_data(spreadsheet_id):
    sheet_names = sheets.get_sheet_names(spreadsheet_id)
    header_values = [
        'ID Number',
        'Pangalan (Surname, Name, Middle Initial)',
        'Position',
        'Origin',
    ]
    cell_headers = sheets.find_cells(spreadsheet_id, sheet_names, header_values)
    # print(cell_headers)
    read_range = []
    for sheet, cell_header in cell_headers.items():
        for cell_header in cell_header.values():
            read_range.append(create_range(cell_header))
    
    sheet_data = sheets.read_sheet_data(spreadsheet_id, read_range)
    colors = reformat_colors(sheets.get_fill_colors(spreadsheet_id, get_first_stated_range(read_range)))

    return arrange_data_by_sheets(sheet_data, header_values), colors
