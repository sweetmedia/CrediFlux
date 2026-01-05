"""
ViewSet for WhatsApp conversations API.

Provides endpoints for:
- Listing conversations (grouped by phone number)
- Getting messages for a specific conversation
- Sending messages to a conversation
"""
import logging
from django.db.models import Max, Count, Q, F
from django.db.models.functions import Coalesce
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import WhatsAppMessage
from .serializers_whatsapp import (
    WhatsAppMessageSerializer,
    WhatsAppConversationSerializer,
    SendWhatsAppMessageSerializer,
    WhatsAppMessageListSerializer,
)
from .tasks import send_whatsapp_message

logger = logging.getLogger(__name__)


class WhatsAppConversationViewSet(viewsets.ViewSet):
    """
    ViewSet for WhatsApp conversations.

    Provides conversation-centric views of WhatsApp messages,
    grouping messages by phone number (conversation_id).
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """
        List all conversations with summary info.

        Returns conversations ordered by most recent message.
        Each conversation includes:
        - conversation_id (phone number)
        - customer info if linked
        - last message preview
        - unread count
        - last message status

        Query params:
        - search: Filter by phone number or customer name
        """
        search = request.query_params.get('search', '')

        # Get unique conversations with aggregated data
        conversations_data = []

        # Get distinct conversation_ids with their latest message
        conversation_ids = WhatsAppMessage.objects.values_list(
            'conversation_id', flat=True
        ).distinct()

        for conv_id in conversation_ids:
            # Get latest message for this conversation
            latest_msg = WhatsAppMessage.objects.filter(
                conversation_id=conv_id
            ).order_by('-created_at').first()

            if not latest_msg:
                continue

            # Apply search filter
            if search:
                customer_name = ''
                if latest_msg.customer:
                    customer_name = latest_msg.customer.get_full_name().lower()

                if (search.lower() not in conv_id.lower() and
                    search.lower() not in customer_name):
                    continue

            # Count unread messages (inbound messages not marked as read)
            unread_count = WhatsAppMessage.objects.filter(
                conversation_id=conv_id,
                direction='inbound',
                read_at__isnull=True
            ).count()

            # Total messages in conversation
            total_messages = WhatsAppMessage.objects.filter(
                conversation_id=conv_id
            ).count()

            # Get profile name from metadata if available
            profile_name = None
            if latest_msg.metadata:
                profile_name = latest_msg.metadata.get('profile_name')

            conversations_data.append({
                'conversation_id': conv_id,
                'customer_id': latest_msg.customer_id,
                'customer_name': latest_msg.customer.get_full_name() if latest_msg.customer else None,
                'profile_name': profile_name,
                'last_message': latest_msg.content[:100] if latest_msg.content else '[Media]',
                'last_message_time': latest_msg.created_at,
                'last_direction': latest_msg.direction,
                'last_status': latest_msg.status,
                'unread_count': unread_count,
                'total_messages': total_messages,
            })

        # Sort by last message time (most recent first)
        conversations_data.sort(key=lambda x: x['last_message_time'], reverse=True)

        serializer = WhatsAppConversationSerializer(conversations_data, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """
        Get all messages for a specific conversation.

        Args:
            pk: The conversation_id (phone number)

        Query params:
        - limit: Number of messages to return (default 50)
        - offset: Offset for pagination
        """
        conversation_id = pk
        limit = int(request.query_params.get('limit', 50))
        offset = int(request.query_params.get('offset', 0))

        # Get messages for this conversation
        messages = WhatsAppMessage.objects.filter(
            conversation_id=conversation_id
        ).order_by('created_at')[offset:offset + limit]

        # Mark inbound messages as read
        WhatsAppMessage.objects.filter(
            conversation_id=conversation_id,
            direction='inbound',
            read_at__isnull=True
        ).update(read_at=F('created_at'))

        serializer = WhatsAppMessageListSerializer(messages, many=True)

        # Get conversation metadata
        latest_msg = WhatsAppMessage.objects.filter(
            conversation_id=conversation_id
        ).order_by('-created_at').first()

        metadata = {
            'conversation_id': conversation_id,
            'customer_id': latest_msg.customer_id if latest_msg else None,
            'customer_name': latest_msg.customer.get_full_name() if latest_msg and latest_msg.customer else None,
            'total_messages': WhatsAppMessage.objects.filter(conversation_id=conversation_id).count(),
        }

        return Response({
            'metadata': metadata,
            'messages': serializer.data,
        })

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """
        Send a message to a conversation.

        Args:
            pk: The conversation_id (phone number)

        Body:
            message: Text message to send
        """
        conversation_id = pk
        serializer = SendWhatsAppMessageSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        message_text = serializer.validated_data['message']

        # Get customer ID if exists in this conversation
        latest_msg = WhatsAppMessage.objects.filter(
            conversation_id=conversation_id
        ).order_by('-created_at').first()

        customer_id = latest_msg.customer_id if latest_msg else None

        # Get tenant schema from request
        tenant_schema = request.tenant.schema_name

        # Send via Celery task
        try:
            task = send_whatsapp_message.delay(
                tenant_schema=tenant_schema,
                to_phone=conversation_id,
                message_text=message_text,
                customer_id=customer_id
            )

            return Response({
                'status': 'queued',
                'task_id': task.id,
                'message': 'Message queued for delivery'
            }, status=status.HTTP_202_ACCEPTED)

        except Exception as e:
            logger.error(f"Error queueing message: {e}")
            return Response({
                'error': 'Failed to queue message',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """
        Mark all inbound messages in a conversation as read.

        Args:
            pk: The conversation_id (phone number)
        """
        conversation_id = pk
        from django.utils import timezone

        updated = WhatsAppMessage.objects.filter(
            conversation_id=conversation_id,
            direction='inbound',
            read_at__isnull=True
        ).update(read_at=timezone.now())

        return Response({
            'marked_read': updated
        })

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """
        Get total unread message count across all conversations.
        """
        count = WhatsAppMessage.objects.filter(
            direction='inbound',
            read_at__isnull=True
        ).count()

        return Response({
            'unread_count': count
        })
