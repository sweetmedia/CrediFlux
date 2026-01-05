import { apiClient } from './client';

// Types
export interface WhatsAppConversation {
  conversation_id: string;
  customer_id: number | null;
  customer_name: string | null;
  profile_name: string | null;
  last_message: string;
  last_message_time: string;
  last_direction: 'inbound' | 'outbound';
  last_status: string;
  unread_count: number;
  total_messages: number;
}

export interface WhatsAppMessage {
  id: number;
  wa_message_id: string;
  direction: 'inbound' | 'outbound';
  status: 'pending' | 'sent' | 'delivered' | 'read' | 'failed' | 'received';
  message_type: 'text' | 'image' | 'audio' | 'video' | 'document' | 'location' | 'template';
  content: string;
  media_url: string | null;
  sent_at: string | null;
  delivered_at: string | null;
  read_at: string | null;
  created_at: string;
}

export interface ConversationMessages {
  metadata: {
    conversation_id: string;
    customer_id: number | null;
    customer_name: string | null;
    total_messages: number;
  };
  messages: WhatsAppMessage[];
}

export interface SendMessageResponse {
  status: string;
  task_id: string;
  message: string;
}

export interface UnreadCountResponse {
  unread_count: number;
}

export const whatsappAPI = {
  /**
   * Get all conversations with summary info
   */
  async getConversations(search?: string): Promise<WhatsAppConversation[]> {
    const params = search ? `?search=${encodeURIComponent(search)}` : '';
    return apiClient.get<WhatsAppConversation[]>(
      `/api/communications/whatsapp/conversations/${params}`
    );
  },

  /**
   * Get messages for a specific conversation
   */
  async getMessages(
    conversationId: string,
    limit: number = 50,
    offset: number = 0
  ): Promise<ConversationMessages> {
    return apiClient.get<ConversationMessages>(
      `/api/communications/whatsapp/conversations/${encodeURIComponent(conversationId)}/?limit=${limit}&offset=${offset}`
    );
  },

  /**
   * Send a message to a conversation
   */
  async sendMessage(
    conversationId: string,
    message: string
  ): Promise<SendMessageResponse> {
    return apiClient.post<SendMessageResponse>(
      `/api/communications/whatsapp/conversations/${encodeURIComponent(conversationId)}/send/`,
      { message }
    );
  },

  /**
   * Mark all messages in a conversation as read
   */
  async markAsRead(conversationId: string): Promise<{ marked_read: number }> {
    return apiClient.post<{ marked_read: number }>(
      `/api/communications/whatsapp/conversations/${encodeURIComponent(conversationId)}/mark_read/`,
      {}
    );
  },

  /**
   * Get total unread message count
   */
  async getUnreadCount(): Promise<UnreadCountResponse> {
    return apiClient.get<UnreadCountResponse>(
      '/api/communications/whatsapp/conversations/unread_count/'
    );
  },
};
