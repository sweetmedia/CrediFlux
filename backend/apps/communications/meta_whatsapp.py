"""
Cliente mínimo de la Graph API de Meta para plantillas de WhatsApp.

Se usa HTTP directo (no los objetos tipados de pywa 3) para crear, listar y
enviar plantillas: el JSON es el que documenta Meta y se prueba fácil con
`responses`. Misma versión de la Graph API que usa pywa 3.4.
"""
import requests

GRAPH_URL = 'https://graph.facebook.com/v24.0'
TIMEOUT = 20


class MetaAPIError(Exception):
    """Error devuelto por la Graph API (o de red)."""

    def __init__(self, message, code=None):
        super().__init__(message)
        self.code = code


def _request(method, path, token, **kwargs):
    try:
        response = requests.request(
            method,
            f'{GRAPH_URL}/{path}',
            headers={'Authorization': f'Bearer {token}'},
            timeout=TIMEOUT,
            **kwargs,
        )
    except requests.RequestException as exc:
        raise MetaAPIError(f'Sin respuesta de Meta: {exc}') from exc
    try:
        data = response.json()
    except ValueError:
        data = {}
    if response.status_code >= 400 or 'error' in data:
        error = data.get('error') or {}
        message = error.get('error_user_msg') or error.get('message') or f'HTTP {response.status_code}'
        raise MetaAPIError(message, code=error.get('code'))
    return data


def list_templates(waba_id, token, name_prefix=''):
    """Plantillas de la cuenta (id, name, language, status, category, rejected_reason)."""
    templates = []
    path = f'{waba_id}/message_templates'
    params = {'fields': 'id,name,language,status,category,rejected_reason', 'limit': 200}
    while path:
        data = _request('GET', path, token, params=params)
        templates.extend(t for t in data.get('data', []) if t.get('name', '').startswith(name_prefix))
        after = (data.get('paging') or {}).get('cursors', {}).get('after')
        if after and (data.get('paging') or {}).get('next'):
            params = {**params, 'after': after}
        else:
            path = None
    return templates


def create_template(waba_id, token, payload):
    """Crea una plantilla; devuelve {'id', 'status', 'category'}."""
    return _request('POST', f'{waba_id}/message_templates', token, json=payload)


def send_template(phone_number_id, token, to, name, language, components):
    """Envía un mensaje de plantilla; devuelve el wamid."""
    data = _request('POST', f'{phone_number_id}/messages', token, json={
        'messaging_product': 'whatsapp',
        'to': to,
        'type': 'template',
        'template': {
            'name': name,
            'language': {'code': language},
            'components': components,
        },
    })
    messages = data.get('messages') or [{}]
    wamid = messages[0].get('id')
    if not wamid:
        raise MetaAPIError('Meta no devolvió el id del mensaje')
    return wamid
