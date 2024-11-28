import colorsys
import datetime

from AMPIRE.utils import logger

def get_default_dates():
    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=today.weekday())
    end_date = start_date + datetime.timedelta(days=6)
    return start_date, end_date

def lighten_color(hex_color, lighten_factor=0.5):
    # Convert hex to RGB
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    # Convert RGB to HLS (Hue, Lightness, Saturation)
    h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)

    # Increase the lightness by the lighten_factor
    l = max(0, min(1, l + (1 - l) * lighten_factor))

    # Convert HLS back to RGB
    r, g, b = colorsys.hls_to_rgb(h, l, s)

    # Convert RGB back to hex
    return '#{:02x}{:02x}{:02x}'.format(int(r * 255), int(g * 255), int(b * 255))

def process_full_name(full_name):
    # Split the name into last name and the rest
    parts = full_name.strip().split(', ')
    
    if len(parts) < 2:
        raise ValueError("Full name must be in 'Last Name, First Name Middle Initial' format")
    
    last_name = parts[0]
    rest_of_name = ', '.join(parts[1:])  # Rejoin in case of extra commas (e.g., for Jr.)
    
    # Split the rest of the name into components
    name_parts = rest_of_name.split()
    
    # Identify suffixes (e.g., Jr., Sr., III)
    suffix = None
    if name_parts[-1] in {"Jr.", "Sr.", "III", "II", "IV"}:
        suffix = name_parts.pop()  # Remove suffix from name parts
    
    # Handle middle initial
    middle_initial = None
    if len(name_parts) > 1 and len(name_parts[-1]) == 2 and name_parts[-1].endswith('.'):
        middle_initial = name_parts.pop()[:-1]  # Extract middle initial without period
    
    # Remaining parts are the first name
    first_name = ' '.join(name_parts)
    
    # Add suffix to first name if it exists
    if suffix:
        first_name += f' {suffix}'
    
    print(f"full_name: {full_name}")
    print(f"last_name: {last_name}")
    print(f"first_name: {first_name}")
    print(f"middle_initial: {middle_initial}")

    return last_name, first_name, middle_initial
