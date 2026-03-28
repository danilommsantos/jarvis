# main/templatetags/menu_tags.py
from django import template
from django.urls import reverse, NoReverseMatch

register = template.Library()

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