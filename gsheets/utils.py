import re

def extract_sheet_id(url):
    # Define the regular expression pattern to match the sheet ID
    pattern = r'/d/([a-zA-Z0-9-_]+)'

    # Search for the pattern in the provided URL
    match = re.search(pattern, url)

    # If a match is found, return the first captured group
    if match:
        return match.group(1)
    else:
        return None