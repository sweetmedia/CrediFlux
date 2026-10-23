"""
Catálogo de plantillas de WhatsApp (Utility) que CrediFlux usa para escribirle a
los clientes de cada financiera.

Por qué plantillas: fuera de la ventana de 24 h desde el último mensaje del
cliente, Meta sólo entrega mensajes de plantillas aprobadas. Las plantillas viven
en la cuenta de WhatsApp (WABA) de CADA financiera, así que este catálogo es la
fuente de verdad y `whatsapp_template_service.sync_tenant_templates` las crea en
cada cuenta.

Reglas de los textos (branding/VOICE.md §4.3 y reglas de Meta):
- "usted", nombre de la financiera como remitente, nunca "CrediFlux";
- ninguna plantilla empieza ni termina con una variable;
- cambiar un texto aprobado obliga a otra revisión de Meta: no se edita a la
  ligera, se agrega una versión nueva con otro nombre.
"""
import re
from dataclasses import dataclass
from typing import Optional

TEMPLATE_LANGUAGE = 'es'
TEMPLATE_CATEGORY = 'UTILITY'
NAME_PREFIX = 'crediflux_'

_PLACEHOLDER = re.compile(r'\{\{(\d+)\}\}')


@dataclass(frozen=True)
class TemplateSpec:
    key: str
    body: str
    example: tuple  # valores de ejemplo para la revisión de Meta, en orden {{1}}..{{n}}
    button_text: Optional[str] = None  # botón URL con sufijo variable
    button_example: Optional[str] = None

    @property
    def name(self) -> str:
        return f'{NAME_PREFIX}{self.key}'

    @property
    def param_count(self) -> int:
        return len(set(_PLACEHOLDER.findall(self.body)))

    def render(self, values) -> str:
        """Texto del cuerpo con los valores puestos (para guardar el mensaje enviado)."""
        return _PLACEHOLDER.sub(lambda m: str(values[int(m.group(1)) - 1]), self.body)


CATALOG = {
    spec.key: spec
    for spec in (
        TemplateSpec(
            key='recordatorio_cuota',
            body=(
                'Hola {{1}}, {{2}} le recuerda que su cuota del préstamo {{3}} vence el {{4}}. '
                'Monto a pagar: {{5}}. Si ya realizó el pago, puede ignorar este mensaje.'
            ),
            example=('Juan', 'Financiera Ejemplo', 'LN-2026-0001', '15 de abril de 2026', 'RD$4,500.00'),
        ),
        TemplateSpec(
            key='cuota_vencida',
            body=(
                'Hola {{1}}, {{2}} le informa que su cuota del préstamo {{3}} venció el {{4}} '
                'y tiene {{5}} días de atraso. Monto pendiente, incluida la mora: {{6}}. '
                'Puede pagar en nuestras oficinas o escribirnos por este medio.'
            ),
            example=('Juan', 'Financiera Ejemplo', 'LN-2026-0001', '15 de abril de 2026', '7', 'RD$5,000.00'),
        ),
        TemplateSpec(
            key='recibo_pago',
            body=(
                'Hola {{1}}, {{2}} confirma que recibió su pago de {{3}} el {{4}} para el préstamo {{5}}. '
                'Número de recibo: {{6}}. Gracias por su pago.'
            ),
            example=('Juan', 'Financiera Ejemplo', 'RD$4,500.00', '15 de abril de 2026', 'LN-2026-0001',
                     'PMT-2026-0001'),
        ),
        TemplateSpec(
            key='firma_contrato',
            body=(
                'Hola {{1}}, su contrato {{2}} con {{3}} está listo para firmar. '
                'Use el botón para revisarlo y firmarlo. El enlace es personal.'
            ),
            example=('Juan', 'CONT-2026-0001', 'Financiera Ejemplo'),
            button_text='Revisar y firmar',
            button_example='ejemplo-token',
        ),
        TemplateSpec(
            key='prestamo_aprobado',
            body=(
                'Hola {{1}}, {{2}} le informa que su préstamo {{3}} por {{4}} fue aprobado. '
                'Nos comunicaremos con usted para coordinar el desembolso.'
            ),
            example=('Juan', 'Financiera Ejemplo', 'LN-2026-0001', 'RD$50,000.00'),
        ),
    )
}


def create_payload(spec: TemplateSpec, button_base_url: Optional[str] = None) -> dict:
    """Cuerpo de POST /{waba_id}/message_templates para crear la plantilla."""
    components = [{
        'type': 'BODY',
        'text': spec.body,
        'example': {'body_text': [list(spec.example)]},
    }]
    if spec.button_text:
        if not button_base_url:
            raise ValueError(f'La plantilla {spec.name} necesita la URL base del botón')
        base = button_base_url.rstrip('/') + '/'
        components.append({
            'type': 'BUTTONS',
            'buttons': [{
                'type': 'URL',
                'text': spec.button_text,
                'url': base + '{{1}}',
                'example': [base + spec.button_example],
            }],
        })
    return {
        'name': spec.name,
        'language': TEMPLATE_LANGUAGE,
        'category': TEMPLATE_CATEGORY,
        'components': components,
    }


def send_components(spec: TemplateSpec, values, button_value: Optional[str] = None) -> list:
    """`components` del mensaje de plantilla con los valores en orden."""
    if len(values) != spec.param_count:
        raise ValueError(f'{spec.name} espera {spec.param_count} valores y recibió {len(values)}')
    components = [{
        'type': 'body',
        'parameters': [{'type': 'text', 'text': str(v)} for v in values],
    }]
    if spec.button_text:
        if not button_value:
            raise ValueError(f'{spec.name} necesita el valor del botón')
        components.append({
            'type': 'button',
            'sub_type': 'url',
            'index': '0',
            'parameters': [{'type': 'text', 'text': button_value}],
        })
    return components
