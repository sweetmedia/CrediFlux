"""Todo monto va en RD$ (DOP) salvo que la financiera elija otra moneda."""
from django.conf import settings
from rest_framework.test import APIRequestFactory

from apps.core.views import get_tenant_config
from apps.loans.models_collections import CollectionContact


def test_moneda_por_defecto_es_dop():
    assert settings.DEFAULT_CURRENCY == 'DOP'
    assert settings.CURRENCIES[0] == 'DOP'


def test_promesa_de_pago_en_dop():
    assert CollectionContact._meta.get_field('promise_amount').default_currency == 'DOP'


def test_config_sin_tenant_responde_rd():
    response = get_tenant_config(APIRequestFactory().get('/api/config/'))
    assert response.data['currency'] == 'DOP'
    assert response.data['currency_symbol'] == 'RD$'
