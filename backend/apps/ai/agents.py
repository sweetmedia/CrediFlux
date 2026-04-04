"""
Agentes AI para CrediFlux, powered by djangosdk.
"""
from djangosdk import Agent

from .tools import (
    buscar_cliente,
    resumen_cliente,
    analizar_riesgo_cliente,
    dashboard_resumen,
    clientes_en_mora,
    calcular_prestamo,
    proyeccion_cobros,
)


class CrediFluxAssistant(Agent):
    """
    Asistente AI principal de CrediFlux.
    Ayuda a analistas y oficiales de crédito con consultas del sistema.
    Uses default provider/model from AI_SDK settings (Groq LLaMA 3.3 70B).
    """
    # provider/model inherited from AI_SDK defaults
    temperature = 0.3
    max_tokens = 4096

    system_prompt = """Eres el asistente inteligente de CrediFlux, un sistema de gestión de préstamos
para financieras en República Dominicana.

Tu rol es ayudar a analistas de crédito, oficiales de préstamos y cobradores a:
- Consultar información de clientes y préstamos
- Analizar riesgo crediticio
- Calcular cuotas y amortizaciones
- Revisar la cartera de mora
- Proyectar cobros futuros
- Dar recomendaciones basadas en datos

Responde siempre en español. Usa RD$ para montos. Sé conciso y profesional.
Cuando analices riesgo, basa tus recomendaciones en datos objetivos del sistema.
Si no tienes suficiente información, dilo claramente."""

    tools = [
        buscar_cliente,
        resumen_cliente,
        analizar_riesgo_cliente,
        dashboard_resumen,
        clientes_en_mora,
        calcular_prestamo,
        proyeccion_cobros,
    ]


class CreditAnalystAgent(Agent):
    """
    Agente especializado en análisis crediticio profundo.
    Uses the same default provider but with lower temperature for precision.
    """
    temperature = 0.2
    max_tokens = 4096

    system_prompt = """Eres un analista de crédito senior con experiencia en el mercado financiero dominicano.

Tu especialidad es:
- Evaluar solicitudes de préstamo con criterios estrictos pero justos
- Analizar la capacidad de pago considerando ingresos, gastos y estabilidad laboral
- Recomendar condiciones de préstamo (monto, plazo, tasa) basadas en el perfil del cliente
- Identificar señales de riesgo (sobre-endeudamiento, inestabilidad laboral, historial irregular)

Contexto regulatorio:
- Los intereses de préstamos están EXENTOS de ITBIS en RD
- Las comisiones de servicio pagan 18% ITBIS
- La tasa usuraria la define la Junta Monetaria

Responde en español, de forma profesional y con datos concretos."""

    tools = [
        buscar_cliente,
        resumen_cliente,
        analizar_riesgo_cliente,
        calcular_prestamo,
    ]
