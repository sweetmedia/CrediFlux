"""R20: la 2FA obligatoria envuelve `APIView.perform_authentication` (apps/users/permissions_2fa.py).

Sólo vale si ninguna vista enrutada redefine `perform_authentication` ni `initial` (que es quien
lo llama): una redefinición sin `super()` saltaría la 2FA en esa vista. Este test recorre las
URL de tenant y del esquema público y falla si alguna clase de la MRO de una vista, fuera de
DRF, define cualquiera de los dos métodos.
"""
import importlib

import pytest
from django.urls import URLPattern, URLResolver
from rest_framework.views import APIView

METODOS = ('perform_authentication', 'initial')


def _patrones(resolver_o_lista):
    for patron in resolver_o_lista:
        if isinstance(patron, URLResolver):
            yield from _patrones(patron.url_patterns)
        elif isinstance(patron, URLPattern):
            yield patron


def _clase_drf(callback):
    cls = getattr(callback, 'cls', None) or getattr(callback, 'view_class', None)
    return cls if isinstance(cls, type) and issubclass(cls, APIView) else None


def _vistas(urlconf):
    modulo = importlib.import_module(urlconf)
    return {cls for p in _patrones(modulo.urlpatterns) if (cls := _clase_drf(p.callback))}


def _redefiniciones(cls):
    return [
        f'{k.__module__}.{k.__qualname__}.{m}'
        for k in cls.__mro__
        if not k.__module__.startswith('rest_framework.')
        for m in METODOS if m in vars(k)
    ]


@pytest.mark.parametrize('urlconf', ['config.urls', 'config.urls_public'])
def test_ninguna_vista_redefine_la_autenticacion(urlconf):
    vistas = _vistas(urlconf)
    assert len(vistas) > 20  # recorrió de verdad las rutas
    culpables = {r for cls in vistas for r in _redefiniciones(cls)}
    assert not culpables, culpables


def test_el_chequeo_detecta_una_redefinicion():
    class VistaQueSaltaLa2FA(APIView):
        def perform_authentication(self, request):
            pass

    assert _redefiniciones(VistaQueSaltaLa2FA)
