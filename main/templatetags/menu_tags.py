# main/templatetags/menu_tags.py
from django import template
from django.urls import reverse, NoReverseMatch

register = template.Library()


@register.filter
def formatar_tempo(segundos):
    if not segundos:
        return '—'
    s = int(segundos)
    dias, s = divmod(s, 86400)
    horas, s = divmod(s, 3600)
    minutos, segs = divmod(s, 60)
    if dias > 0:
        return f"{dias}d {horas:02}:{minutos:02}:{segs:02}"
    if horas > 0:
        return f"{horas:02}:{minutos:02}:{segs:02}"
    return f"{minutos:02}:{segs:02}"

def resolver_url(valor):
    try:
        return reverse(valor)
    except NoReverseMatch:
        return valor

def eh_externo(url):
    """Retorna True se a URL começa com http ou https"""
    return url.startswith('http://') or url.startswith('https://') or url.startswith('www.') 

@register.inclusion_tag('main/comp/menu_item.html', takes_context=True)
def render_menu_item(context, label, icon, target):
    request = context['request']
    url = resolver_url(target)
    
    return {
        'label': label,
        'icon': icon,
        'url': url,
        'is_active': request.path == url,
        'externo': eh_externo(url) # Nova variável
    }

@register.inclusion_tag('main/comp/menu_subitem.html', takes_context=True)
def render_subitem(context, label, target):
    request = context['request']
    url = resolver_url(target)
    
    return {
        'label': label,
        'url': url,
        'is_active': request.path == url,
        'externo': eh_externo(url) # Nova variável
    }