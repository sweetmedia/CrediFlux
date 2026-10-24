"""Códigos de respaldo del 2FA guardados como hash.

`User.backup_codes` (JSONField, sin cambio de esquema) guarda una lista de hashes de
Django (`make_password`, con sal). El código en claro sólo se muestra una vez, al
generarlo. Compatibilidad: una entrada sin `$` es un código en claro de antes de este
cambio; se compara en claro (tiempo constante) y, si acierta, el resto se rehashea.

El consumo relee la fila con `select_for_update()` dentro de `transaction.atomic()`:
dos peticiones simultáneas con el mismo código no pueden gastarlo las dos.
"""
import hmac
import secrets

from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction

BACKUP_CODE_COUNT = 10


def _normalize(code):
    return (code or '').strip().upper()


def _is_hashed(entry):
    return '$' in entry


def hash_codes(codes):
    return [make_password(_normalize(code)) for code in codes]


def generate_backup_codes(count=BACKUP_CODE_COUNT):
    """Devuelve (códigos en claro para mostrar una vez, hashes para guardar)."""
    codes = [secrets.token_hex(4).upper() for _ in range(count)]
    return codes, hash_codes(codes)


def _matches(code, entry):
    if _is_hashed(entry):
        return check_password(code, entry)
    return hmac.compare_digest(code.encode(), _normalize(entry).encode())


def consume_backup_code(user, code):
    """Gasta `code` si coincide con un código guardado. True si se aceptó.

    Actualiza también `user.backup_codes` en memoria.
    """
    from .models import User

    code = _normalize(code)
    if not code:
        return False
    with transaction.atomic():
        locked = User.objects.select_for_update().only('pk', 'backup_codes').get(pk=user.pk)
        stored = list(locked.backup_codes or [])
        for index, entry in enumerate(stored):
            if _matches(code, entry):
                break
        else:
            return False
        legacy = not _is_hashed(stored[index])
        del stored[index]
        if legacy:
            stored = [entry if _is_hashed(entry) else make_password(_normalize(entry)) for entry in stored]
        locked.backup_codes = stored
        locked.save(update_fields=['backup_codes'])
    user.backup_codes = stored
    return True
