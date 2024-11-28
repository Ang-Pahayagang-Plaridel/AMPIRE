import time
import random
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def exponential_backoff(retries, max_backoff):
    wait_time = min((2 ** retries) + random.uniform(0, 1), max_backoff)
    time.sleep(wait_time)

def handle_error(error, retries, max_backoff):
    status = error.resp.status
    if status in [500, 502, 503, 504] or (status == 403 and 'rateLimitExceeded' in error.resp.reason):
        logger.warning(f'Retryable error {status}, retrying...')
        exponential_backoff(retries, max_backoff)
        return True  # Indicates a retryable error
    else:
        logger.error(f'Non-retryable error occurred: {error}')
        return False  # Indicates a non-retryable error

def batch_callback(request_id, response, exception):
    if exception:
        logger.error(f'An error occurred: {exception}')
    else:
        logger.info(f'Folder created with ID: {response.get("id")}')

def rgb_to_hex(rgb):
    try:
        # Use .get() to provide default values if the key is missing
        r = int(rgb.get('red', 0) * 255)
        g = int(rgb.get('green', 0) * 255)
        b = int(rgb.get('blue', 0) * 255)
        
        # Ensure the values are within the 0-255 range
        r = min(max(r, 0), 255)
        g = min(max(g, 0), 255)
        b = min(max(b, 0), 255)
        
        # Return the hex value
        return '#{:02x}{:02x}{:02x}'.format(r, g, b)
    
    except TypeError as e:
        raise ValueError("Invalid RGB input format") from e

def hex_to_rgb(hex_color):
    # Convert hex color to Google's RGB color format
    hex_color = hex_color.lstrip('#')
    return {
        'red': int(hex_color[0:2], 16) / 255.0,
        'green': int(hex_color[2:4], 16) / 255.0,
        'blue': int(hex_color[4:6], 16) / 255.0,
    }