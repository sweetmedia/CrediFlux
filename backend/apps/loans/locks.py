"""Bloqueos de préstamos y contratos compartidos por el admin y la API.

Orden de bloqueo del módulo: préstamo → fila de garantía/garante → contrato → token.
lock_pending_loans/lock_row_loans toman los bloqueos de préstamos; lock_row bloquea después la fila
de garantía/garante, y quien los llama escribe esa fila y, si corresponde, el contrato.
lock_contract bloquea sólo el contrato (acciones y edición/borrado de contratos).
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
    préstamo → fila → contrato → token del módulo, y la regeneración posterior sólo escribe el contrato.
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


def lock_row(model, pk):
    """Bloquea y devuelve la fila de garantía/garante tal como está en la base de datos.

    Debe llamarse dentro de una transacción y, si la escritura depende de préstamos, después de
    bloquearlos (orden préstamo → fila → contrato → token). Quien escribe debe usar la fila
    devuelta y no la instancia leída antes del bloqueo, para no pisar con valores viejos un cambio
    confirmado entretanto. Lanza model.DoesNotExist si la fila ya no existe.
    """
    return model.objects.select_for_update(of=('self',)).get(pk=pk)


def lock_contract(contract):
    """Vuelve a leer el contrato con SELECT ... FOR UPDATE (sólo su fila, sin joins).

    Llamar dentro de `transaction.atomic()`. Todas las comprobaciones y escrituras de la acción
    se hacen sobre la instancia devuelta, nunca sobre la copia leída antes. El orden de bloqueo
    del módulo es préstamo → contrato: después de esto no se bloquea el préstamo.
    """
    from .models_contracts import Contract

    return Contract.objects.select_for_update(of=('self',)).get(pk=contract.pk)
