# filtros_residuo.py
from django import template

register = template.Library()

@register.filter
def precio_residuo(diccionario, clave):
    if isinstance(diccionario, dict):
        return diccionario.get(clave, '')
    return ''



@register.filter
def sumar_pesajes(lista):
    try:
        return round(sum(p.get('peso_neto', 0) for p in lista), 2)
    except:
        return 0