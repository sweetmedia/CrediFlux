"""Ningún admin servido en el host de un tenant lista ni acepta usuarios de otro tenant.

La tabla de usuarios es compartida (schema público). `UserAdmin` la acota por tenant y la API
usa `TenantUserField`, pero los admins de modelos de tenant con FK a `users.User` construían sus
selects y filtros de lista con el manager sin filtrar: el filtro `assignee` de tareas, el select
`loan_officer` del alta de préstamo o `default_cashier` de caja listaban los correos de usuarios
de otros tenants y de la plataforma, y un POST guardaba una tarea asignada a un usuario ajeno
(run-5, admin.shared-user-fk-choices-and-emailaddressadmin-not-tenant-scoped).

Ahora `TenantUserFKMixin` limita esos campos a los usuarios activos del tenant de quien pide
(conserva el usuario ya asignado al objeto aunque esté inactivo) y los filtros de lista a los
usuarios del tenant; el superusuario de plataforma sigue viéndolos todos. Un test recorre el
registro del admin para que un admin futuro con FK a usuarios no quede abierto.
"""
import pytest
from django.contrib import admin
from django.contrib.admin.utils import get_fields_from_path
from django.contrib.auth.models import Permission
from django.db import connection
from django.test import Client, RequestFactory

from apps.cashbox.models import CashRegister
from apps.communications.models import Task
from apps.core.admin_mixins import PlatformAdminOnlyMixin
from apps.loans.models import Loan
from apps.users.models import User

pytestmark = pytest.mark.django_db

TENANT_HOST = "tenant.test.localhost"
FOREIGN_EMAIL = "ajeno-r24@otra.test"
PLATFORM_EMAIL = "plataforma-r24@crediflux.test"
OWN_EMAIL = "propio-r24@financiera.test"
INACTIVE_EMAIL = "inactivo-r24@financiera.test"


@pytest.fixture
def users(tenant, other_tenant):
    """Usuarios de las tres procedencias, creados en public (la tabla es compartida)."""
    connection.set_schema_to_public()
    return {
        "foreign": User.objects.create_user(
            username="ajeno-r24", email=FOREIGN_EMAIL, password="x",
            first_name="Ajeno", last_name="B", tenant=other_tenant, role="loan_officer",
        ),
        "platform": User.objects.create_user(
            username="plataforma-r24", email=PLATFORM_EMAIL, password="x",
            is_superuser=True, is_staff=True,
        ),
        "own": User.objects.create_user(
            username="propio-r24", email=OWN_EMAIL, password="x",
            first_name="Propio", last_name="A", tenant=tenant, role="loan_officer",
        ),
        "inactive": User.objects.create_user(
            username="inactivo-r24", email=INACTIVE_EMAIL, password="x",
            tenant=tenant, role="loan_officer", is_active=False,
        ),
    }


def _staff(tenant, name, codenames, role="viewer"):
    staff = User.objects.create_user(
        username=name, email=f"{name}@financiera.test", password="x",
        tenant=tenant, is_staff=True, role=role,
    )
    staff.user_permissions.add(*Permission.objects.filter(codename__in=codenames))
    return User.objects.get(pk=staff.pk)  # sin la caché de permisos


def _client(user):
    client = Client(HTTP_HOST=TENANT_HOST)
    client.force_login(user)
    return client


def _form_errors(response):
    return response.context["adminform"].form.errors


def _task_post(assignee):
    return {
        "title": "tarea-r24", "description": "", "status": "todo", "priority": "medium",
        "position": "0", "assignee": str(assignee.pk), "due_date": "", "tags": "[]", "_save": "Guardar",
    }


def _assert_only_own_users(html):
    assert FOREIGN_EMAIL not in html
    assert PLATFORM_EMAIL not in html
    assert OWN_EMAIL in html


# --- tareas (communications) -------------------------------------------------------------------

def test_task_changelist_filter_lists_only_own_tenant_users(tenant, users):
    response = _client(_staff(tenant, "staff-task-view-r24", ["view_task"])).get(
        "/admin/communications/task/"
    )

    assert response.status_code == 200
    _assert_only_own_users(response.content.decode())


def test_task_add_form_lists_only_active_own_tenant_users(tenant, users):
    response = _client(_staff(tenant, "staff-task-add-r24", ["view_task", "add_task"])).get(
        "/admin/communications/task/add/"
    )

    assert response.status_code == 200
    html = response.content.decode()
    _assert_only_own_users(html)
    assert INACTIVE_EMAIL not in html


def test_task_add_rejects_assignee_of_another_tenant(tenant, users):
    client = _client(_staff(tenant, "staff-task-post-r24", ["view_task", "add_task"]))

    response = client.post("/admin/communications/task/add/", _task_post(users["foreign"]))

    assert response.status_code == 200
    assert "assignee" in _form_errors(response)
    connection.set_tenant(tenant)
    assert not Task.objects.filter(title="tarea-r24").exists()


def test_task_add_accepts_active_user_of_own_tenant(tenant, users):
    client = _client(_staff(tenant, "staff-task-own-r24", ["view_task", "add_task"]))

    response = client.post("/admin/communications/task/add/", _task_post(users["own"]))

    assert response.status_code == 302
    connection.set_tenant(tenant)
    assert Task.objects.get(title="tarea-r24").assignee_id == users["own"].pk


def test_task_change_keeps_inactive_user_already_assigned(tenant, users):
    """Editar una tarea cuyo responsable ya está inactivo no lo borra ni falla la validación."""
    connection.set_tenant(tenant)
    task = Task.objects.create(title="tarea-r24", assignee=users["inactive"])
    client = _client(_staff(tenant, "staff-task-chg-r24", ["view_task", "change_task"]))
    url = f"/admin/communications/task/{task.pk}/change/"

    assert INACTIVE_EMAIL in client.get(url).content.decode()
    data = _task_post(users["inactive"])
    data["description"] = "editada"
    response = client.post(url, data)

    assert response.status_code == 302
    connection.set_tenant(tenant)
    task.refresh_from_db()
    assert (task.description, task.assignee_id) == ("editada", users["inactive"].pk)


# --- préstamos (loans) -----------------------------------------------------------------------

def test_loan_add_form_lists_only_own_tenant_officers(tenant, users):
    staff = _staff(tenant, "cajero-r24", ["view_loan", "add_loan"], role="cashier")

    response = _client(staff).get("/admin/loans/loan/add/")

    assert response.status_code == 200
    _assert_only_own_users(response.content.decode())


def test_loan_add_rejects_officer_of_another_tenant(tenant, users):
    staff = _staff(tenant, "cajero-post-r24", ["view_loan", "add_loan"], role="cashier")

    response = _client(staff).post(
        "/admin/loans/loan/add/", {"loan_officer": str(users["foreign"].pk), "_save": "Guardar"}
    )

    assert response.status_code == 200
    assert "loan_officer" in _form_errors(response)
    connection.set_tenant(tenant)
    assert not Loan.objects.exists()


def test_contract_template_add_form_lists_only_own_tenant_users(tenant, users):
    staff = _staff(tenant, "staff-plantilla-r24", ["view_contracttemplate", "add_contracttemplate"])

    response = _client(staff).get("/admin/loans/contracttemplate/add/")

    assert response.status_code == 200
    _assert_only_own_users(response.content.decode())


# --- caja (cashbox) --------------------------------------------------------------------------

def test_cash_register_add_form_lists_only_own_tenant_users(tenant, users):
    staff = _staff(tenant, "staff-caja-r24", ["view_cashregister", "add_cashregister"])

    response = _client(staff).get("/admin/cashbox/cashregister/add/")

    assert response.status_code == 200
    _assert_only_own_users(response.content.decode())


def test_cash_register_add_rejects_cashier_of_another_tenant(tenant, users):
    staff = _staff(tenant, "staff-caja-post-r24", ["view_cashregister", "add_cashregister"])

    response = _client(staff).post("/admin/cashbox/cashregister/add/", {
        "name": "Caja R24", "code": "CAJA-R24", "location": "", "is_active": "on",
        "default_cashier": str(users["foreign"].pk), "_save": "Guardar",
    })

    assert response.status_code == 200
    assert "default_cashier" in _form_errors(response)
    connection.set_tenant(tenant)
    assert not CashRegister.objects.filter(code="CAJA-R24").exists()


# --- superusuario de plataforma: ve y elige usuarios de cualquier tenant ---------------------

def test_platform_superuser_sees_and_assigns_users_of_any_tenant(tenant, users):
    client = _client(users["platform"])

    for url in ("/admin/communications/task/", "/admin/communications/task/add/",
                "/admin/loans/loan/add/"):
        html = client.get(url).content.decode()
        assert FOREIGN_EMAIL in html, url
        assert OWN_EMAIL in html, url

    response = client.post("/admin/communications/task/add/", _task_post(users["foreign"]))

    assert response.status_code == 302
    connection.set_tenant(tenant)
    assert Task.objects.get(title="tarea-r24").assignee_id == users["foreign"].pk


# --- registro: todo admin con FK/M2M a usuarios aplica el acotamiento ------------------------

def _user_fields(model):
    return [
        f for f in model._meta.get_fields()
        if f.concrete and (f.many_to_one or f.one_to_one or f.many_to_many) and f.related_model is User
    ]


def _excluded(model_admin):
    # UserAdmin ya acota su propia tabla; los admins sólo de plataforma no se abren a un tenant.
    return model_admin.model is User or isinstance(model_admin, PlatformAdminOnlyMixin)


def _scoped_admins():
    for model, model_admin in admin.site._registry.items():
        if _excluded(model_admin):
            continue
        yield model_admin.__class__.__name__, model_admin
        for inline_class in model_admin.inlines:
            yield f"{model_admin.__class__.__name__}.{inline_class.__name__}", inline_class(model, admin.site)


def test_every_admin_with_user_fk_scopes_choices_and_filters(tenant, users):
    staff = _staff(tenant, "staff-registro-r24", [])
    request = RequestFactory(HTTP_HOST=TENANT_HOST).get("/admin/")
    request.user = staff
    checked = set()

    for label, model_admin in _scoped_admins():
        for field in _user_fields(model_admin.model):
            if field.many_to_many:
                formfield = model_admin.formfield_for_manytomany(field, request)
            else:
                formfield = model_admin.formfield_for_foreignkey(field, request)
            pks = set(formfield.queryset.values_list("pk", flat=True))
            where = f"{label}.{field.name}"
            assert users["foreign"].pk not in pks, where
            assert users["platform"].pk not in pks, where
            assert users["inactive"].pk not in pks, where
            assert users["own"].pk in pks, where
            checked.add(where)

        if isinstance(model_admin, admin.ModelAdmin):  # los inlines no tienen filtros de lista
            for entry in model_admin.get_list_filter(request):
                path = entry[0] if isinstance(entry, (list, tuple)) else entry
                if not isinstance(path, str):
                    continue  # SimpleListFilter propio: no recorre un FK a usuarios
                if get_fields_from_path(model_admin.model, path)[-1].related_model is not User:
                    continue
                from apps.core.admin_filters import TenantUserListFilter
                assert isinstance(entry, (list, tuple)) and issubclass(entry[1], TenantUserListFilter), (
                    f"{label}: filtro de lista '{path}' sin acotar"
                )
                checked.add(f"{label} filtro {path}")

    # El barrido tiene que haber pasado por los casos conocidos.
    assert {
        "TaskAdmin.assignee", "TaskAdmin filtro assignee", "LoanAdmin.loan_officer",
        "ContractAdmin.generated_by", "ContractTemplateAdmin.created_by",
        "CustomerDocumentAdmin.verified_by", "CollectionReminderAdmin.sent_by",
        "LoanPaymentAdmin.reversed_by", "CashSessionAdmin.cashier", "CashRegisterAdmin.default_cashier",
        "InvoiceAdmin.created_by", "CustomerAdmin.LoanInline.loan_officer",
    } <= checked
