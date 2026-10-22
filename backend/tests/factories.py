"""Fábricas factory_boy compartidas por la suite.

Las fábricas NO activan schemas: úsalas desde un test que ya tenga el
schema correcto (fixture `tenant_schema` o `public_schema`).
"""

import factory
from django.contrib.auth import get_user_model


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()
        django_get_or_create = ("email",)

    email = factory.Sequence(lambda n: f"usuario{n}@crediflux.test")
    username = factory.Sequence(lambda n: f"usuario{n}")
    first_name = factory.Faker("first_name", locale="es_ES")
    last_name = factory.Faker("last_name", locale="es_ES")
    role = "viewer"
    is_active = True
    password = factory.django.Password("clave-de-prueba-123")
