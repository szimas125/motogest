from decimal import Decimal, InvalidOperation
from django import template

register = template.Library()


@register.filter
def brl(valor):
    try:
        numero = Decimal(valor)
    except (InvalidOperation, TypeError, ValueError):
        return 'R$ 0,00'
    texto = f'{numero:,.2f}'
    texto = texto.replace(',', 'X').replace('.', ',').replace('X', '.')
    return f'R$ {texto}'
