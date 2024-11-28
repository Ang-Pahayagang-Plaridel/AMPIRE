from django import template

register = template.Library()

@register.filter(name='mask_id')
def mask_id(value):
    value_str = str(value)
    if len(value_str) > 3:
        return value_str[:3] + '*' * (len(value_str) - 3)
    return value_str
