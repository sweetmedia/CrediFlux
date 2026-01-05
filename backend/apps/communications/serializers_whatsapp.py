"""
Serializers for WhatsApp conversations and messages API.
"""
from rest_framework import serializers
from .models import WhatsAppMessage


class WhatsAppMessageSerializer(serializers.ModelSerializer):
    """
    Serializer for individual WhatsApp messages.
    """
    customer_name = serializers.SerializerMethodField()

    class Meta:
        model = WhatsAppMessage
        fields = [
            'id',
            'wa_message_id',
            'direction',
            'status',
            'message_type',
            'from_phone',
            'to_phone',
            'content',
            'media_url',
            'media_type',
            'caption',
            'customer',
            'customer_name',
            'conversation_id',
            'sent_at',
            'delivered_at',
            'read_at',
            'created_at',
            'updated_at',
            'error_message',
        ]
        read_only_fields = [
            'id',
            'wa_message_id',
            'created_at',
            'updated_at',
        ]

    def get_customer_name(self, obj):
        """Get customer full name if available."""
        if obj.customer:
            return obj.customer.get_full_name()
        return None


class WhatsAppConversationSerializer(serializers.Serializer):
    """
    Serializer for conversation list (aggregated view).

    A conversation is a grouping of messages by conversation_id (phone number).
    """
    conversation_id = serializers.CharField()
    customer_id = serializers.IntegerField(allow_null=True)
    customer_name = serializers.CharField(allow_null=True)
    profile_name = serializers.CharField(allow_null=True)
    last_message = serializers.CharField()
    last_message_time = serializers.DateTimeField()
    last_direction = serializers.CharField()
    last_status = serializers.CharField()
    unread_count = serializers.IntegerField()
    total_messages = serializers.IntegerField()


class SendWhatsAppMessageSerializer(serializers.Serializer):
    """
    Serializer for sending a new WhatsApp message.
    """
    message = serializers.CharField(
        max_length=4096,
        help_text='Text message to send (max 4096 characters)'
    )

    def validate_message(self, value):
        """Validate message is not empty."""
        if not value.strip():
            raise serializers.ValidationError("Message cannot be empty")
        return value.strip()


class WhatsAppMessageListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for message lists.
    """
    class Meta:
        model = WhatsAppMessage
        fields = [
            'id',
            'wa_message_id',
            'direction',
            'status',
            'message_type',
            'content',
            'media_url',
            'sent_at',
            'delivered_at',
            'read_at',
            'created_at',
        ]
