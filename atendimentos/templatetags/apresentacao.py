from django import template
from django.templatetags.static import static
from django.utils.html import format_html

from ..forms import PRIORIDADES

register = template.Library()

_SITUACOES = {
    "aguardando": "Aguardando",
    "em_atendimento": "Em atendimento",
    "concluido": "Concluído",
    "cancelado": "Cancelado",
    "disponivel": "Disponível",
}
_PRIORIDADES = dict(PRIORIDADES)


@register.filter
def situacao(valor):
    return _SITUACOES[valor]


@register.filter
def prioridade(valor):
    return _PRIORIDADES[valor]


@register.simple_tag(takes_context=True)
def link_ativo(context, nome):
    if context["request"].resolver_match.url_name == nome:
        return 'aria-current=page'
    return ""


@register.simple_tag
def icone(nome):
    return format_html(
        '<svg class="icone" aria-hidden="true" focusable="false">'
        '<use href="{}#{}"></use></svg>',
        static("css/icones.svg"), nome,
    )
