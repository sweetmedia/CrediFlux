"""
Vistas API para el asistente AI de CrediFlux.

Lógica de habilitación:
1. AI_ENABLED (global en settings/.env) — kill switch para toda la plataforma
2. tenant.enable_ai_assistant — cada tenant puede habilitar/deshabilitar
3. tenant.ai_provider / ai_api_key — si el tenant tiene su propia key, se usa;
   si no, se usa la key global de la plataforma
"""
import uuid

from django.conf import settings
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import connection
from djangosdk.models.conversation import Conversation
from djangosdk.providers.schemas import ProviderConfig

from apps.users.authz import ViewPermissionRequired
from .agents import CrediFluxAssistant, CrediFluxLiteAgent, CreditAnalystAgent
from .tools import con_usuario


def get_ai_config():
    """
    Resuelve la configuración AI efectiva.
    Prioridad: Tenant-specific > Global (.env)

    Returns:
        dict: {enabled, provider, model, api_key} o None si deshabilitado
    """
    # 1. Check global kill switch
    if not getattr(settings, 'AI_ENABLED', True):
        return None

    # 2. Check tenant-level settings
    tenant = getattr(connection, 'tenant', None)
    if tenant and hasattr(tenant, 'enable_ai_assistant'):
        if not tenant.enable_ai_assistant:
            return None

        # Tenant has its own AI config
        if tenant.ai_provider and tenant.ai_provider != 'global' and tenant.ai_api_key:
            provider = tenant.ai_provider
            model = tenant.ai_model or ''
            api_key = tenant.ai_api_key

            return {
                'enabled': True,
                'provider': provider,
                'model': model,
                'api_key': api_key,
                'source': 'tenant',
            }

    # 3. Fall back to global config
    ai_sdk = getattr(settings, 'AI_SDK', {})
    return {
        'enabled': True,
        'provider': ai_sdk.get('DEFAULT_PROVIDER', 'groq'),
        'model': ai_sdk.get('DEFAULT_MODEL', ''),
        'api_key': None,  # Global keys come from env vars, already set
        'source': 'global',
    }


# Proveedor del tenant (Tenant.ai_provider) → proveedor de litellm. 'custom' es
# compatible con OpenAI (no hay base_url propia en el modelo Tenant).
TENANT_LITELLM_PROVIDERS = {
    'groq': 'groq',
    'gemini': 'gemini',
    'openai': 'openai',
    'anthropic': 'anthropic',
    'custom': 'openai',
}

# Modelo por defecto cuando el tenant trae clave propia pero no indica modelo:
# siempre del proveedor del tenant, para que su clave nunca vaya a otro proveedor.
TENANT_DEFAULT_MODELS = {
    'groq': 'groq/llama-3.3-70b-versatile',
    'gemini': 'gemini/gemini-2.0-flash',
    'openai': 'openai/gpt-4o-mini',
    'anthropic': 'anthropic/claude-opus-5-5',
}


def build_tenant_agent(agent_class, ai_config):
    """
    Instancia el agente con la configuración AI efectiva.

    Si el tenant tiene clave propia, se pasa por instancia en un ``ProviderConfig``
    (llega a litellm como ``api_key`` sólo en esta request); nunca se escribe en
    ``os.environ``, que es global al proceso y compartido entre tenants. El
    proveedor y el modelo se fijan al proveedor del tenant para que su clave no
    se envíe nunca al proveedor global de la plataforma.
    """
    if not ai_config or ai_config['source'] != 'tenant':
        return agent_class()

    provider = TENANT_LITELLM_PROVIDERS.get(ai_config['provider'])
    if provider is None:
        raise ValueError(f"Proveedor AI no soportado: {ai_config['provider']}")

    model = ai_config.get('model') or TENANT_DEFAULT_MODELS[provider]
    if '/' not in model:
        model = f'{provider}/{model}'

    agent = agent_class(provider_config=ProviderConfig(name=provider, api_key=ai_config['api_key']))
    agent.provider = provider
    agent.model = model
    return agent


class ChatView(APIView):
    """
    Endpoint principal del chat AI.
    POST /api/ai/chat/
    Body: {"prompt": "...", "conversation_id": "...", "agent": "assistant|analyst|lite"}

    Exige `ai.access`; cada herramienta del agente mide además el código del dato que lee
    con los permisos del usuario de la petición (`con_usuario`).
    """
    permission_classes = [IsAuthenticated, ViewPermissionRequired]
    permission_codes = {'POST': 'ai.access'}

    AGENTS = {
        'assistant': CrediFluxAssistant,
        'lite': CrediFluxLiteAgent,
        'analyst': CreditAnalystAgent,
    }

    def post(self, request):
        # Check if AI is enabled
        ai_config = get_ai_config()
        if ai_config is None:
            return Response(
                {'error': 'El asistente AI está deshabilitado para esta organización.'},
                status=status.HTTP_403_FORBIDDEN
            )

        prompt = request.data.get('prompt', '').strip()
        conversation_id = request.data.get('conversation_id')
        agent_type = request.data.get('agent', 'assistant')

        if not prompt:
            return Response(
                {'error': 'El campo "prompt" es requerido.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if conversation_id:
            try:
                conversation_id = uuid.UUID(str(conversation_id))
            except ValueError:
                return Response(
                    {'error': 'conversation_id inválido.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            owned = Conversation.objects.filter(
                id=conversation_id, metadata__user_id=request.user.pk
            ).exists()
            if not owned:
                return Response(
                    {'error': 'Conversación no encontrada.'},
                    status=status.HTTP_404_NOT_FOUND
                )

        agent_class = self.AGENTS.get(agent_type, CrediFluxAssistant)
        try:
            agent = build_tenant_agent(agent_class, ai_config)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if conversation_id:
            agent = agent.with_conversation(conversation_id)
        else:
            conversation = agent.start_conversation(
                metadata={'user_id': request.user.pk, 'schema': connection.schema_name}
            )
            conversation_id = conversation.id

        try:
            with con_usuario(request.user):
                response = agent.handle(prompt)
        except Exception as e:
            return Response(
                {'error': f'Error del asistente: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({
            'text': response.text,
            'conversation_id': str(response.conversation_id or conversation_id),
            'thinking': response.thinking.content if response.thinking else None,
            'usage': {
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens,
            } if response.usage else None,
        })


class AgentsListView(APIView):
    """
    Lista los agentes AI disponibles.
    GET /api/ai/agents/
    """
    permission_classes = [IsAuthenticated, ViewPermissionRequired]
    permission_codes = {'GET': 'ai.access'}

    def get(self, request):
        # Check if AI is enabled
        ai_config = get_ai_config()
        if ai_config is None:
            return Response({
                'enabled': False,
                'agents': [],
                'message': 'El asistente AI está deshabilitado.',
            })

        return Response({
            'enabled': True,
            'ai_source': ai_config['source'],  # 'global' or 'tenant'
            'agents': [
                {
                    'id': 'lite',
                    'name': 'Asistente Rápido',
                    'description': 'Respuestas rápidas, cálculos y preguntas generales (sin acceso a datos).',
                    'model': CrediFluxLiteAgent.model,
                    'tools': [],
                },
                {
                    'id': 'assistant',
                    'name': 'Asistente Completo',
                    'description': 'Consultas con acceso al sistema: clientes, dashboard, mora, proyecciones.',
                    'model': CrediFluxAssistant.model,
                    'tools': [t.__name__ for t in CrediFluxAssistant.tools],
                },
                {
                    'id': 'analyst',
                    'name': 'Analista de Crédito',
                    'description': 'Análisis profundo de riesgo crediticio y recomendaciones.',
                    'model': CreditAnalystAgent.model,
                    'tools': [t.__name__ for t in CreditAnalystAgent.tools],
                },
            ]
        })


class AIConfigView(APIView):
    """
    GET: Ver configuración AI del tenant actual.
    PUT: Actualizar configuración AI (solo admin).
    """
    permission_classes = [IsAuthenticated, ViewPermissionRequired]
    permission_codes = {'GET': 'settings.view', 'PUT': 'settings.edit'}

    def get(self, request):
        tenant = getattr(connection, 'tenant', None)
        global_enabled = getattr(settings, 'AI_ENABLED', True)

        data = {
            'global_enabled': global_enabled,
            'tenant_enabled': True,
            'provider': 'global',
            'model': '',
            'has_custom_key': False,
        }

        if tenant and hasattr(tenant, 'enable_ai_assistant'):
            data.update({
                'tenant_enabled': tenant.enable_ai_assistant,
                'provider': tenant.ai_provider or 'global',
                'model': tenant.ai_model or '',
                'has_custom_key': bool(tenant.ai_api_key),
            })

        return Response(data)

    def put(self, request):
        tenant = getattr(connection, 'tenant', None)
        if not tenant or not hasattr(tenant, 'enable_ai_assistant'):
            return Response(
                {'error': 'No hay tenant activo.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update fields
        if 'enabled' in request.data:
            tenant.enable_ai_assistant = request.data['enabled']
        if 'provider' in request.data:
            tenant.ai_provider = request.data['provider']
        if 'model' in request.data:
            tenant.ai_model = request.data['model'] or None
        if 'api_key' in request.data:
            tenant.ai_api_key = request.data['api_key'] or None

        tenant.save(update_fields=[
            'enable_ai_assistant', 'ai_provider', 'ai_model', 'ai_api_key'
        ])

        return Response({
            'message': 'Configuración AI actualizada.',
            'tenant_enabled': tenant.enable_ai_assistant,
            'provider': tenant.ai_provider,
            'model': tenant.ai_model or '',
            'has_custom_key': bool(tenant.ai_api_key),
        })
