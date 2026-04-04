"""
Vistas API para el asistente AI de CrediFlux.
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .agents import CrediFluxAssistant, CreditAnalystAgent


class ChatView(APIView):
    """
    Endpoint principal del chat AI.
    POST /api/ai/chat/
    Body: {"prompt": "...", "conversation_id": "...", "agent": "assistant|analyst"}
    """
    permission_classes = [IsAuthenticated]

    AGENTS = {
        'assistant': CrediFluxAssistant,
        'analyst': CreditAnalystAgent,
    }

    def post(self, request):
        prompt = request.data.get('prompt', '').strip()
        conversation_id = request.data.get('conversation_id')
        agent_type = request.data.get('agent', 'assistant')

        if not prompt:
            return Response(
                {'error': 'El campo "prompt" es requerido.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        agent_class = self.AGENTS.get(agent_type, CrediFluxAssistant)
        agent = agent_class()

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
        return Response({
            'agents': [
                {
                    'id': 'assistant',
                    'name': 'Asistente CrediFlux',
                    'description': 'Consultas generales, búsqueda de clientes, dashboard, cálculos.',
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
