"""
Herramientas AI para CrediFlux.
Funciones que el agente puede invocar para consultar y analizar datos del sistema.
"""
from djangosdk import tool
from django.utils import timezone
from django.db.models import Sum, Count, Q, Avg, F
from datetime import timedelta
from decimal import Decimal


@tool
def buscar_cliente(query: str) -> str:
    """Busca un cliente por nombre, cédula o número de cliente.

    Args:
        query: Nombre, número de cédula, o ID del cliente.
    """
    from apps.loans.models import Customer

    customers = Customer.objects.filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(id_number__icontains=query) |
        Q(customer_id__icontains=query)
    )[:5]

    if not customers:
        return f"No se encontraron clientes con '{query}'."

    results = []
    for c in customers:
        results.append(
            f"- {c.full_name} | Cédula: {c.id_number} | "
            f"ID: {c.customer_id} | Estado: {c.status} | "
            f"Tel: {c.phone or 'N/A'}"
        )
    return f"Se encontraron {len(results)} cliente(s):\n" + "\n".join(results)


@tool
def resumen_cliente(customer_id: str) -> str:
    """Obtiene el resumen completo de un cliente: datos personales, préstamos activos, historial de pagos.

    Args:
        customer_id: ID del cliente (ej: CUST-0001) o número de cédula.
    """
    from apps.loans.models import Customer, Loan, Payment

    try:
        customer = Customer.objects.filter(
            Q(customer_id=customer_id) | Q(id_number=customer_id)
        ).first()
        if not customer:
            return f"Cliente '{customer_id}' no encontrado."
    except Exception:
        return f"Error buscando cliente '{customer_id}'."

    loans = Loan.objects.filter(customer=customer)
    active_loans = loans.filter(status='active')
    total_disbursed = loans.aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')

    payments = Payment.objects.filter(loan__customer=customer)
    total_paid = payments.aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')

    info = [
        f"📋 **{customer.full_name}**",
        f"   Cédula: {customer.id_number}",
        f"   Teléfono: {customer.phone or 'N/A'}",
        f"   Email: {customer.email or 'N/A'}",
        f"   Estado laboral: {customer.employment_status or 'N/A'}",
        f"   Empleador: {customer.employer_name or 'N/A'}",
        f"   Ingreso mensual: RD$ {customer.monthly_income or 'N/A'}",
        f"",
        f"💰 Resumen financiero:",
        f"   Total préstamos: {loans.count()}",
        f"   Préstamos activos: {active_loans.count()}",
        f"   Total desembolsado: RD$ {total_disbursed:,.2f}",
        f"   Total pagado: RD$ {total_paid:,.2f}",
    ]

    for loan in active_loans:
        info.append(f"   📌 Préstamo {loan.loan_number}: RD$ {loan.amount:,.2f} - {loan.get_status_display()}")

    return "\n".join(info)


@tool
def analizar_riesgo_cliente(customer_id: str) -> str:
    """Analiza el riesgo crediticio de un cliente basado en su historial de pagos, estabilidad laboral e ingresos.

    Args:
        customer_id: ID del cliente o número de cédula.
    """
    from apps.loans.models import Customer, Loan, LoanSchedule, Payment

    customer = Customer.objects.filter(
        Q(customer_id=customer_id) | Q(id_number=customer_id)
    ).first()
    if not customer:
        return f"Cliente '{customer_id}' no encontrado."

    loans = Loan.objects.filter(customer=customer)
    schedules = LoanSchedule.objects.filter(loan__customer=customer)

    # Factor 1: Historial de pagos puntuales
    total_schedules = schedules.filter(status__in=['paid', 'overdue', 'partial']).count()
    overdue_schedules = schedules.filter(status='overdue').count()
    on_time_rate = ((total_schedules - overdue_schedules) / total_schedules * 100) if total_schedules > 0 else 0

    # Factor 2: Estabilidad laboral
    employment_score = 0
    if customer.employment_start_date:
        months_employed = (timezone.now().date() - customer.employment_start_date).days / 30
        if months_employed >= 24:
            employment_score = 100
        elif months_employed >= 12:
            employment_score = 75
        elif months_employed >= 6:
            employment_score = 50
        else:
            employment_score = 25
    else:
        employment_score = 0

    # Factor 3: Capacidad de pago (deuda vs ingreso)
    active_monthly_obligations = Decimal('0')
    active_loans = loans.filter(status='active')
    for loan in active_loans:
        pending = schedules.filter(loan=loan, status='pending').first()
        if pending:
            active_monthly_obligations += pending.total_amount.amount if hasattr(pending.total_amount, 'amount') else Decimal(str(pending.total_amount))

    monthly_income = customer.monthly_income.amount if customer.monthly_income and hasattr(customer.monthly_income, 'amount') else Decimal('0')
    debt_ratio = (active_monthly_obligations / monthly_income * 100) if monthly_income > 0 else 100

    # Score compuesto
    payment_weight = 0.50
    employment_weight = 0.25
    debt_weight = 0.25
    debt_score = max(0, 100 - float(debt_ratio))

    total_score = (on_time_rate * payment_weight +
                   employment_score * employment_weight +
                   debt_score * debt_weight)

    # Clasificación
    if total_score >= 80:
        risk_level = "🟢 BAJO"
        recommendation = "Cliente confiable. Aprobación recomendada."
    elif total_score >= 60:
        risk_level = "🟡 MODERADO"
        recommendation = "Revisar condiciones. Considerar garante o colateral."
    elif total_score >= 40:
        risk_level = "🟠 ALTO"
        recommendation = "Requiere garantías adicionales y verificación exhaustiva."
    else:
        risk_level = "🔴 MUY ALTO"
        recommendation = "No recomendado sin garantías sustanciales."

    return "\n".join([
        f"📊 **Análisis de Riesgo — {customer.full_name}**",
        f"",
        f"Puntaje total: {total_score:.0f}/100 → Riesgo: {risk_level}",
        f"",
        f"Desglose:",
        f"  • Pagos puntuales: {on_time_rate:.0f}% ({total_schedules - overdue_schedules}/{total_schedules} a tiempo)",
        f"  • Estabilidad laboral: {employment_score}/100",
        f"  • Ratio deuda/ingreso: {debt_ratio:.1f}% (score: {debt_score:.0f}/100)",
        f"  • Ingreso mensual: RD$ {monthly_income:,.2f}",
        f"  • Obligaciones mensuales: RD$ {active_monthly_obligations:,.2f}",
        f"",
        f"💡 Recomendación: {recommendation}",
    ])


@tool
def dashboard_resumen() -> str:
    """Obtiene el resumen ejecutivo del dashboard: cartera total, préstamos activos, mora, cobros del día."""
    from apps.loans.models import Loan, LoanSchedule, Payment

    today = timezone.now().date()

    total_loans = Loan.objects.count()
    active_loans = Loan.objects.filter(status='active').count()

    total_portfolio = Loan.objects.filter(status='active').aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')

    # Mora
    overdue_schedules = LoanSchedule.objects.filter(
        due_date__lt=today,
        status__in=['pending', 'partial', 'overdue']
    )
    overdue_count = overdue_schedules.values('loan').distinct().count()
    overdue_amount = overdue_schedules.aggregate(
        total=Sum('total_amount')
    )['total'] or Decimal('0')

    # Cobros del día
    today_payments = Payment.objects.filter(payment_date=today)
    today_collected = today_payments.aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')

    # Vencimientos hoy
    due_today = LoanSchedule.objects.filter(
        due_date=today,
        status__in=['pending', 'partial']
    ).count()

    return "\n".join([
        f"📊 **Dashboard CrediFlux — {today.strftime('%d/%m/%Y')}**",
        f"",
        f"Cartera total: RD$ {total_portfolio:,.2f}",
        f"Préstamos activos: {active_loans} de {total_loans}",
        f"",
        f"⚠️ Mora:",
        f"  • Préstamos en mora: {overdue_count}",
        f"  • Monto vencido: RD$ {overdue_amount:,.2f}",
        f"",
        f"💵 Hoy:",
        f"  • Cobros realizados: RD$ {today_collected:,.2f} ({today_payments.count()} pagos)",
        f"  • Cuotas por vencer hoy: {due_today}",
    ])


@tool
def clientes_en_mora() -> str:
    """Lista los clientes con cuotas vencidas, ordenados por días de atraso (más críticos primero)."""
    from apps.loans.models import LoanSchedule

    today = timezone.now().date()
    overdue = LoanSchedule.objects.filter(
        due_date__lt=today,
        status__in=['pending', 'partial', 'overdue']
    ).select_related('loan', 'loan__customer').order_by('due_date')[:20]

    if not overdue:
        return "✅ No hay clientes en mora actualmente."

    results = []
    seen = set()
    for s in overdue:
        customer = s.loan.customer
        if customer.id in seen:
            continue
        seen.add(customer.id)
        days = (today - s.due_date).days
        amount = s.total_amount.amount if hasattr(s.total_amount, 'amount') else s.total_amount
        results.append(
            f"  {'🔴' if days > 30 else '🟡'} {customer.full_name} — "
            f"{days} días | RD$ {amount:,.2f} | "
            f"Préstamo: {s.loan.loan_number} | Tel: {customer.phone or 'N/A'}"
        )

    return f"⚠️ **Clientes en mora ({len(results)}):**\n" + "\n".join(results)


@tool
def calcular_prestamo(monto: float, tasa_mensual: float, plazo_meses: int, metodo: str = "french") -> str:
    """Calcula las cuotas de un préstamo con diferentes métodos de amortización.

    Args:
        monto: Monto del préstamo en RD$.
        tasa_mensual: Tasa de interés mensual (ej: 3.5 para 3.5%).
        plazo_meses: Plazo en meses.
        metodo: Método de amortización: french, flat, saldo_insoluto, german.
    """
    monto = Decimal(str(monto))
    tasa = Decimal(str(tasa_mensual)) / 100

    if metodo == 'french':
        # Cuota fija (sistema francés)
        if tasa > 0:
            cuota = monto * (tasa * (1 + tasa) ** plazo_meses) / ((1 + tasa) ** plazo_meses - 1)
        else:
            cuota = monto / plazo_meses
        total = cuota * plazo_meses
        total_interes = total - monto
    elif metodo == 'flat':
        total_interes = monto * tasa * plazo_meses
        total = monto + total_interes
        cuota = total / plazo_meses
    elif metodo == 'saldo_insoluto':
        capital_fijo = monto / plazo_meses
        primer_interes = monto * tasa
        primera_cuota = capital_fijo + primer_interes
        ultima_cuota = capital_fijo + (capital_fijo * tasa)
        total_interes = sum([(monto - capital_fijo * i) * tasa for i in range(plazo_meses)])
        total = monto + total_interes
        cuota = primera_cuota  # Variable, mostrar primera
    elif metodo == 'german':
        capital_fijo = monto / plazo_meses
        primer_interes = monto * tasa
        primera_cuota = capital_fijo + primer_interes
        total_interes = sum([(monto - capital_fijo * i) * tasa for i in range(plazo_meses)])
        total = monto + total_interes
        cuota = primera_cuota
    else:
        return f"Método '{metodo}' no soportado. Usa: french, flat, saldo_insoluto, german."

    return "\n".join([
        f"🧮 **Cálculo de Préstamo**",
        f"",
        f"Monto: RD$ {monto:,.2f}",
        f"Tasa mensual: {tasa_mensual}%",
        f"Plazo: {plazo_meses} meses",
        f"Método: {metodo}",
        f"",
        f"{'Cuota fija' if metodo in ('french', 'flat') else 'Primera cuota'}: RD$ {cuota:,.2f}",
        f"Total intereses: RD$ {total_interes:,.2f}",
        f"Total a pagar: RD$ {total:,.2f}",
    ])


@tool
def proyeccion_cobros(dias: int = 7) -> str:
    """Proyecta los cobros esperados para los próximos días.

    Args:
        dias: Número de días a proyectar (default: 7).
    """
    from apps.loans.models import LoanSchedule

    today = timezone.now().date()
    upcoming = LoanSchedule.objects.filter(
        due_date__gte=today,
        due_date__lte=today + timedelta(days=dias),
        status__in=['pending', 'partial']
    ).order_by('due_date')

    if not upcoming:
        return f"No hay cobros programados en los próximos {dias} días."

    total = Decimal('0')
    by_day = {}
    for s in upcoming:
        amount = s.total_amount.amount if hasattr(s.total_amount, 'amount') else Decimal(str(s.total_amount))
        total += amount
        day_str = s.due_date.strftime('%a %d/%m')
        if day_str not in by_day:
            by_day[day_str] = {'count': 0, 'amount': Decimal('0')}
        by_day[day_str]['count'] += 1
        by_day[day_str]['amount'] += amount

    lines = [f"📅 **Proyección de cobros — Próximos {dias} días**", ""]
    for day, data in by_day.items():
        lines.append(f"  {day}: {data['count']} cuotas = RD$ {data['amount']:,.2f}")
    lines.append(f"")
    lines.append(f"Total esperado: RD$ {total:,.2f} ({upcoming.count()} cuotas)")

    return "\n".join(lines)
