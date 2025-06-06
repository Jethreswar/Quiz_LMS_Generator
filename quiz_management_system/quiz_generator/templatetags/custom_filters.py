from django import template
import json
from django.utils.safestring import mark_safe
from django.template.defaultfilters import stringfilter

register = template.Library()

@register.filter
def parse_json(value):
    try:
        return json.loads(value)
    except:
        return []

@register.filter(is_safe=True)
def json_script(value, element_id):
    """
    Output value as a JSON script element with given id.
    """
    json_str = json.dumps(value)
    return mark_safe(f'<script id="{element_id}" type="application/json">{json_str}</script>')

@register.filter
def replace(value, arg):
    """
    Replace all instances of the argument with an empty string
    """
    return value.replace(arg, '')

@register.filter
def clean_course(value):
    """
    Clean up course name formatting
    """
    if isinstance(value, str):
        return value.replace('\n', '').replace('"', '').strip()
    return value