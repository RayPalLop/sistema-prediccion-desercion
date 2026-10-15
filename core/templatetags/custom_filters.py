import re
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter(name='render_markdown_bold')
def render_markdown_bold(value):
    """
    Filtro para transformar los asteriscos de Markdown (**texto**)
    en etiquetas HTML de negrita (<strong>texto</strong>).
    """
    if not isinstance(value, str):
        return value
    
    # Expresión regular que busca todo lo que esté entre ** y lo reemplaza por <strong>
    processed_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', value)
    
    return mark_safe(processed_text)