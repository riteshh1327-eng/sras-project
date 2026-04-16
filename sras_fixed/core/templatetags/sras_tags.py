from django import template

register = template.Library()


@register.filter
def dict_key(d, key):
    """Get dict value by key in templates: {{ my_dict|dict_key:var }}"""
    if isinstance(d, dict):
        return d.get(key, '')
    return ''


@register.filter
def multiply(value, arg):
    """Multiply a value: {{ 60|multiply:0.4 }}"""
    try:
        return float(value) * float(arg)
    except (TypeError, ValueError):
        return ''


@register.filter
def subtract(value, arg):
    try:
        return float(value) - float(arg)
    except (TypeError, ValueError):
        return ''


@register.filter
def grade_color(grade):
    """Return CSS class for a grade."""
    colors = {
        'O': 'stat-green', 'A+': 'stat-green', 'A': 'stat-green',
        'B+': 'stat-blue', 'B': 'stat-blue', 'C': 'stat-orange', 'F': 'stat-red',
    }
    return colors.get(grade, 'stat-blue')
