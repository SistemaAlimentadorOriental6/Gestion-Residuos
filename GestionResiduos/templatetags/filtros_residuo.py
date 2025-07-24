# filtros_residuo.py
from django import template

register = template.Library()

@register.filter
def precio_residuo(diccionario, clave):
    if isinstance(diccionario, dict):
        return diccionario.get(clave, '')
    return ''