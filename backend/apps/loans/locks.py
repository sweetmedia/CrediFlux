"""Bloqueos de préstamos compartidos por el admin y la API (garantías y garantes).

Orden de bloqueo del módulo: préstamo → contrato → token. Estos helpers sólo toman bloqueos de
préstamos; quien los llama escribe después la fila y, si corresponde, el contrato.
"""
from .models import Loan


class LoanNotPending(Exception):
    """Algún préstamo bloqueado no está pendiente, ya no existe o la fila cambió de préstamo.

    El argumento describe qué se encontró (ids y estados); el mensaje para el usuario lo pone
    quien captura la excepción (PermissionDenied en el admin, ValidationError en la API).
    """


def lock_pending_loans(loan_ids):
    """Bloquea los préstamos indicados y exige que todos sigan pendientes.

    Debe llamarse dentro de una transacción. Descarta None y duplicados, bloquea con
    SELECT ... FOR UPDATE en una sola consulta ordenada por pk —orden de bloqueo determinista
    cuando son dos préstamos (garantía/garante movido entre préstamos)— y lanza LoanNotPending si
    alguno no está pendiente o ya no existe. No bloquea el contrato: se respeta el orden
    préstamo → contrato → token del módulo, y la regeneración posterior sólo escribe el contrato.
    Devuelve el conjunto de pks bloqueados.
    """
    ids = {pk for pk in loan_ids if pk is not None}
    locked = list(
        Loan.objects.select_for_update(of=('self',))
        .filter(pk__in=ids).order_by('pk').values_list('pk', 'status')
    )
    if len(locked) != len(ids) or any(status != 'pending' for _, status in locked):
        raise LoanNotPending({'requested': sorted(map(str, ids)), 'locked': locked})
    return ids


def lock_row_loans(model, obj, loan_ids):
    """Bloquea los préstamos de una garantía/un garante y revalida el préstamo actual de la fila.

    Debe llamarse dentro de una transacción. El préstamo anterior de la fila se leyó antes del
    bloqueo; otra petición pudo moverla entretanto. Tras bloquear se vuelve a leer su loan_id: si
    ya no es uno de los préstamos bloqueados, lanza LoanNotPending (cualquier movimiento desde un
    préstamo bloqueado necesita su bloqueo, así que la relectura es estable). En el alta la fila
    aún no existe (o no tiene pk), así que la relectura no devuelve nada y no hay nada que validar.
    """
    locked = lock_pending_loans(loan_ids)
    current = model.objects.filter(pk=obj.pk).values_list('loan_id', flat=True).first()
    if current is not None and current not in locked:
        raise LoanNotPending({'row': str(obj.pk), 'loan': str(current)})
    return locked
