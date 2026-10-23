"""Archivos privados: URL firmada ligada al tenant y rutas de subida por tenant.

Cubre: sin `static(MEDIA_URL)` aunque DEBUG esté activo, la URL firmada que
devuelve el serializer abre sin cabecera en el host de su tenant, se rechaza en
otro host, caducada o alterada, y los archivos nuevos se guardan bajo
`<schema>/<prefijo>/...`. El logo del tenant es un activo público (`public/`).
"""

import importlib
from datetime import date
from urllib.parse import urlparse

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import clear_url_caches
from rest_framework.test import APIClient

TENANT_HOST = "tenant.test.localhost"
OTHER_HOST = "other.test.localhost"
PUBLIC_HOST = "localhost"

PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06"
    b"\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01"
    b"\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _reload_urlconfs():
    import config.urls
    import config.urls_public

    importlib.reload(config.urls)
    importlib.reload(config.urls_public)
    clear_url_caches()


@pytest.fixture
def debug_urlconfs():
    """URL confs recargadas con DEBUG=True; se restauran al terminar."""
    with override_settings(DEBUG=True):
        _reload_urlconfs()
        yield
    _reload_urlconfs()


@pytest.fixture
def customer(tenant_schema):
    from apps.loans.models import Customer

    return Customer.objects.create(
        first_name="Marta",
        last_name="Media",
        date_of_birth=date(1990, 1, 1),
        gender="F",
        email="marta.media@crediflux.test",
        phone="+18095550000",
        address_line1="Calle 1",
        city="Santo Domingo",
        state="DN",
        postal_code="10101",
        id_type="cedula",
        id_number="001-7777777-1",
        employment_status="employed",
    )


@pytest.fixture
def uploaded_document(auth_client, customer):
    """Documento subido por la API; devuelve (respuesta JSON, bytes subidos)."""
    response = auth_client.post(
        "/api/loans/customer-documents/",
        {
            "customer": str(customer.id),
            "document_type": "id_card",
            "title": "Cédula",
            "document_file": SimpleUploadedFile("cedula.png", PNG_BYTES, content_type="image/png"),
        },
        format="multipart",
    )
    assert response.status_code == 201, response.content
    yield response.json(), PNG_BYTES

    from apps.loans.models import CustomerDocument

    for document in CustomerDocument.objects.filter(pk=response.json()["id"]):
        document.document_file.delete(save=False)


def _signed_path(url):
    assert url, "el serializer no devolvió URL"
    path = urlparse(url).path
    assert path.startswith("/media/s/"), url
    return path


def _body(response):
    return b"".join(response.streaming_content)


def test_debug_does_not_serve_media_root_anonymously(debug_urlconfs, tenant_schema):
    name = default_storage.save("customer_documents/legacy.png", ContentFile(PNG_BYTES))
    try:
        for host in (TENANT_HOST, PUBLIC_HOST):
            response = APIClient(HTTP_HOST=host).get(f"/media/{name}")
            assert response.status_code == 404, (host, response.status_code)
    finally:
        default_storage.delete(name)


def test_new_customer_document_goes_under_tenant_prefix(uploaded_document):
    from apps.loans.models import CustomerDocument

    data, _ = uploaded_document
    document = CustomerDocument.objects.get(pk=data["id"])
    assert document.document_file.name.startswith("test/customer_documents/")
    assert document.document_file.name.endswith("cedula.png")


def test_serializer_url_opens_without_credentials_on_tenant_host(uploaded_document):
    data, content = uploaded_document
    path = _signed_path(data["document_file"])

    response = APIClient(HTTP_HOST=TENANT_HOST).get(path)

    assert response.status_code == 200
    assert _body(response) == content
    assert response["Content-Type"] == "image/png"
    assert response["Content-Disposition"].startswith("inline")


def test_signed_url_is_forbidden_on_another_tenant_host(uploaded_document, other_tenant):
    data, _ = uploaded_document
    path = _signed_path(data["document_file"])

    response = APIClient(HTTP_HOST=OTHER_HOST).get(path)

    assert response.status_code == 403


def test_expired_signature_is_forbidden(uploaded_document):
    data, _ = uploaded_document
    path = _signed_path(data["document_file"])

    with override_settings(MEDIA_SIGNED_URL_MAX_AGE=-1):
        response = APIClient(HTTP_HOST=TENANT_HOST).get(path)

    assert response.status_code == 403


def test_tampered_signature_is_forbidden(uploaded_document):
    data, _ = uploaded_document
    path = _signed_path(data["document_file"])
    tampered = path.rstrip("/")[:-1] + ("A" if not path.rstrip("/").endswith("A") else "B") + "/"

    response = APIClient(HTTP_HOST=TENANT_HOST).get(tampered)

    assert response.status_code == 403


def test_traversal_name_is_forbidden_even_if_signed(tenant_schema):
    from apps.core.media import signed_media_url

    path = signed_media_url("../config/settings/base.py", "test")

    response = APIClient(HTTP_HOST=TENANT_HOST).get(path)

    assert response.status_code == 403


def test_missing_file_is_404(tenant_schema):
    from apps.core.media import signed_media_url

    path = signed_media_url("test/customer_documents/nope/missing.pdf", "test")

    response = APIClient(HTTP_HOST=TENANT_HOST).get(path)

    assert response.status_code == 404


def test_non_image_non_pdf_is_served_as_attachment(tenant_schema):
    from apps.core.media import signed_media_url

    name = default_storage.save("test/customer_documents/x/page.svg", ContentFile(b"<svg/>"))
    try:
        response = APIClient(HTTP_HOST=TENANT_HOST).get(signed_media_url(name, "test"))
        assert response.status_code == 200
        assert response["Content-Disposition"].startswith("attachment")
    finally:
        default_storage.delete(name)


def test_public_url_cannot_sign_tenant_files(tenant_schema, other_tenant):
    """Firmar con schema `public` sólo vale para activos bajo `public/`."""
    from apps.core.media import signed_media_url

    name = default_storage.save("test/customer_documents/x/secret.pdf", ContentFile(b"%PDF-1"))
    try:
        response = APIClient(HTTP_HOST=OTHER_HOST).get(signed_media_url(name, "public"))
        assert response.status_code == 403
    finally:
        default_storage.delete(name)


def test_tenant_logo_is_public_asset_readable_from_any_host(tenant, other_tenant):
    from apps.tenants.serializers import TenantSerializer

    tenant.logo.save("logo.png", ContentFile(PNG_BYTES), save=False)
    try:
        assert tenant.logo.name.startswith("public/tenant_logos/")
        url = TenantSerializer(tenant).data["logo"]
        path = _signed_path(url)
        for host in (TENANT_HOST, OTHER_HOST, PUBLIC_HOST):
            response = APIClient(HTTP_HOST=host).get(path)
            assert response.status_code == 200, host
            assert _body(response) == PNG_BYTES
    finally:
        tenant.logo.delete(save=False)


def test_signed_file_field_returns_none_without_file(customer):
    from apps.loans.serializers import CustomerSerializer

    assert CustomerSerializer(customer).data["photo"] is None


def _signed_file_response(name, schema, host, content=b"%PDF-1"):
    from apps.core.media import signed_media_url

    stored = default_storage.save(name, ContentFile(content))
    try:
        return stored, APIClient(HTTP_HOST=host).get(signed_media_url(stored, schema))
    finally:
        default_storage.delete(stored)


def test_public_schema_files_outside_logo_prefix_are_not_cross_host(tenant_schema, other_tenant):
    _, response = _signed_file_response("public/customer_documents/x/x.pdf", "public", OTHER_HOST)
    assert response.status_code == 403

    _, response = _signed_file_response("public/tenant_logos/x/x.png", "public", OTHER_HOST, PNG_BYTES)
    assert response.status_code == 200


def test_name_of_another_schema_is_forbidden_even_if_signed_for_host(tenant_schema):
    _, response = _signed_file_response("other/customer_documents/x/x.pdf", "test", TENANT_HOST)
    assert response.status_code == 403


def test_legacy_name_without_schema_prefix_is_served_on_its_host(tenant_schema):
    _, response = _signed_file_response("customer_documents/2025/01/old.pdf", "test", TENANT_HOST)
    assert response.status_code == 200


def test_private_file_is_not_cached(uploaded_document):
    data, _ = uploaded_document
    response = APIClient(HTTP_HOST=TENANT_HOST).get(_signed_path(data["document_file"]))
    assert response["Cache-Control"] == "private, no-store"
    assert response["X-Content-Type-Options"] == "nosniff"


def test_certificate_upload_response_omits_certificate_file(auth_client):
    response = auth_client.post(
        "/api/billing/certificates/",
        {
            "name": "Firma DGII",
            "certificate_file": SimpleUploadedFile(
                "cert.p12", b"not-a-real-p12", content_type="application/x-pkcs12"
            ),
            "certificate_password": "s3cret",
        },
        format="multipart",
    )
    assert response.status_code == 201, response.content
    assert "certificate_file" not in response.json()

    from apps.billing.models import DigitalCertificate

    certificate = DigitalCertificate.objects.get(pk=response.json()["id"])
    assert certificate.certificate_file.name.startswith("test/billing/certificates/")
    certificate.certificate_file.delete(save=False)
