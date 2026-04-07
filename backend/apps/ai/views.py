"""
Vistas API para el asistente AI de CrediFlux.

Lógica de habilitación:
1. AI_ENABLED (global en settings/.env) — kill switch para toda la plataforma
2. tenant.enable_ai_assistant — cada tenant puede habilitar/deshabilitar
3. tenant.ai_provider / ai_api_key — si el tenant tiene su propia key, se usa;
   si no, se usa la key global de la plataforma
"""
import os

from django.conf import settings
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import connection

from .agents import CrediFluxAssistant, CrediFluxLiteAgent, CreditAnalystAgent


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


def apply_tenant_ai_config(ai_config):
    """
    Si el tenant tiene su propia API key, la inyecta como variable
    de entorno para que litellm la use en esta request.
    """
    if not ai_config or ai_config['source'] != 'tenant':
        return

    provider = ai_config['provider']
    api_key = ai_config['api_key']

    # Map provider to env var that litellm expects
    env_map = {
        'groq': 'GROQ_API_KEY',
        'gemini': 'GEMINI_API_KEY',
        'openai': 'OPENAI_API_KEY',
        'anthropic': 'ANTHROPIC_API_KEY',
        'custom': 'OPENAI_API_KEY',  # litellm uses openai-compatible for custom
    }

    env_var = env_map.get(provider)
    if env_var and api_key:
        os.environ[env_var] = api_key


class ChatView(APIView):
    """
    Endpoint principal del chat AI.
    POST /api/ai/chat/
    Body: {"prompt": "...", "conversation_id": "...", "agent": "assistant|analyst|lite"}
    """
    permission_classes = [IsAuthenticated]

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

        # Apply tenant-specific API key if configured
        apply_tenant_ai_config(ai_config)

        agent_class = self.AGENTS.get(agent_type, CrediFluxAssistant)
        agent = agent_class()

        # Override model if tenant has a specific one
        if ai_config.get('model') and ai_config['source'] == 'tenant':
            agent.model = ai_config['model']

        if conversation_id:
            agent = agent.with_conversation(conversation_id)

        try:
            response = agent.handle(prompt)
        except Exception as e:
            return Response(
                {'error': f'Error del asistente: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({
            'text': response.text,
            'conversation_id': response.conversation_id or conversation_id,
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
    permission_classes = [IsAuthenticated]

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
    permission_classes = [IsAuthenticated]

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

        # Check if user is admin
        user = request.user
        if not (user.is_staff or user.is_superuser or getattr(user, 'role', '') == 'admin'):
            return Response(
                {'error': 'Solo administradores pueden cambiar la configuración AI.'},
                status=status.HTTP_403_FORBIDDEN
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
