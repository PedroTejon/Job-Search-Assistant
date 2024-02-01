from __future__ import annotations

from django import template

register = template.Library()


@register.filter
def get_type(value) -> type:  # type: ignore[no-untyped-def, misc]
    return type(value)
