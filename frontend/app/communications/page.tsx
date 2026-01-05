'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/lib/contexts/AuthContext';
import { whatsappAPI, WhatsAppConversation, WhatsAppMessage as WAMessage } from '@/lib/api/whatsapp';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs';
import {
  Mail,
  MessageSquare,
  Send,
  Inbox,
  Loader2,
  Plus,
  Search,
  RefreshCw,
  Clock,
  FileText,
  SendIcon,
  Trash2,
  Archive,
  Users,
  Newspaper,
  MessageCircle,
  ShoppingCart,
  Tag,
  Star,
  Trash,
  ArchiveX,
  Reply,
  Forward,
  MoreVertical,
  Check,
  CheckCheck,
  AlertCircle,
} from 'lucide-react';

interface EmailFolder {
  id: string;
  name: string;
  icon: any;
  count: number;
  color?: string;
}

interface EmailLabel {
  id: string;
  name: string;
  color: string;
}

interface Email {
  id: string;
  from: string;
  fromName: string;
  to: string;
  subject: string;
  body: string;
  date: string;
  read: boolean;
  folder: string;
  labels: string[];
  important: boolean;
}

// WhatsAppMessage interface is now imported from API module

export default function CommunicationsPage() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const [activeTab, setActiveTab] = useState<'email' | 'whatsapp'>('email');
  const [emailView, setEmailView] = useState<'inbox' | 'compose'>('inbox');
  const [selectedFolder, setSelectedFolder] = useState('inbox');
  const [emailFilter, setEmailFilter] = useState<'all' | 'unread'>('all');

  // Email states
  const [emails, setEmails] = useState<Email[]>([]);
  const [selectedEmail, setSelectedEmail] = useState<Email | null>(null);
  const [isLoadingEmails, setIsLoadingEmails] = useState(false);
  const [replyText, setReplyText] = useState('');

  // Compose email states
  const [composeTo, setComposeTo] = useState('');
  const [composeSubject, setComposeSubject] = useState('');
  const [composeBody, setComposeBody] = useState('');
  const [isSendingEmail, setIsSendingEmail] = useState(false);

  // WhatsApp states
  const [conversations, setConversations] = useState<WhatsAppConversation[]>([]);
  const [currentMessages, setCurrentMessages] = useState<WAMessage[]>([]);
  const [selectedChat, setSelectedChat] = useState<string | null>(null);
  const [selectedConversation, setSelectedConversation] = useState<WhatsAppConversation | null>(null);
  const [whatsappMessage, setWhatsAppMessage] = useState('');
  const [isSendingWhatsApp, setIsSendingWhatsApp] = useState(false);
  const [isLoadingConversations, setIsLoadingConversations] = useState(false);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [whatsappSearch, setWhatsappSearch] = useState('');

  // Email folders
  const folders: EmailFolder[] = [
    { id: 'inbox', name: 'Inbox', icon: Inbox, count: 128, color: 'text-blue-600' },
    { id: 'drafts', name: 'Drafts', icon: FileText, count: 9, color: 'text-gray-600' },
    { id: 'sent', name: 'Sent', icon: SendIcon, count: 0, color: 'text-gray-600' },
    { id: 'junk', name: 'Junk', icon: Trash2, count: 23, color: 'text-gray-600' },
    { id: 'trash', name: 'Trash', icon: Trash, count: 0, color: 'text-gray-600' },
    { id: 'archive', name: 'Archive', icon: Archive, count: 0, color: 'text-gray-600' },
    { id: 'social', name: 'Social', icon: Users, count: 972, color: 'text-gray-600' },
    { id: 'updates', name: 'Updates', icon: Newspaper, count: 342, color: 'text-gray-600' },
    { id: 'forums', name: 'Forums', icon: MessageCircle, count: 128, color: 'text-gray-600' },
    { id: 'shopping', name: 'Shopping', icon: ShoppingCart, count: 8, color: 'text-gray-600' },
    { id: 'promotions', name: 'Promotions', icon: Tag, count: 21, color: 'text-gray-600' },
  ];

  // Email labels
  const labels: EmailLabel[] = [
    { id: 'work', name: 'work', color: 'bg-green-600' },
    { id: 'important', name: 'important', color: 'bg-red-600' },
    { id: 'meeting', name: 'meeting', color: 'bg-blue-600' },
    { id: 'personal', name: 'personal', color: 'bg-purple-600' },
    { id: 'budget', name: 'budget', color: 'bg-yellow-600' },
  ];

  // Load WhatsApp conversations
  const fetchConversations = useCallback(async () => {
    setIsLoadingConversations(true);
    try {
      const data = await whatsappAPI.getConversations(whatsappSearch);
      setConversations(data);
    } catch (error) {
      console.error('Error loading conversations:', error);
    } finally {
      setIsLoadingConversations(false);
    }
  }, [whatsappSearch]);

  // Load messages for selected conversation
  const fetchMessages = useCallback(async (conversationId: string) => {
    setIsLoadingMessages(true);
    try {
      const data = await whatsappAPI.getMessages(conversationId);
      setCurrentMessages(data.messages);
    } catch (error) {
      console.error('Error loading messages:', error);
    } finally {
      setIsLoadingMessages(false);
    }
  }, []);

  // Load conversations when WhatsApp tab is active
  useEffect(() => {
    if (activeTab === 'whatsapp' && isAuthenticated) {
      fetchConversations();
    }
  }, [activeTab, isAuthenticated, fetchConversations]);

  // Load messages when conversation is selected
  useEffect(() => {
    if (selectedChat) {
      fetchMessages(selectedChat);
      // Find the selected conversation
      const conv = conversations.find(c => c.conversation_id === selectedChat);
      setSelectedConversation(conv || null);
    } else {
      setCurrentMessages([]);
      setSelectedConversation(null);
    }
  }, [selectedChat, fetchMessages, conversations]);

  // Polling for new messages (every 30 seconds when WhatsApp tab is active)
  useEffect(() => {
    if (activeTab !== 'whatsapp' || !isAuthenticated) return;

    const interval = setInterval(() => {
      fetchConversations();
      if (selectedChat) {
        fetchMessages(selectedChat);
      }
    }, 30000);

    return () => clearInterval(interval);
  }, [activeTab, isAuthenticated, selectedChat, fetchConversations, fetchMessages]);

  // Mock data for emails (TODO: implement email API)
  useEffect(() => {
    const mockEmails: Email[] = [
      {
        id: '1',
        from: 'williamsmith@example.com',
        fromName: 'William Smith',
        to: 'info@miempresa.com',
        subject: 'Meeting Tomorrow',
        body: `Hi, let's have a meeting tomorrow to discuss the project.`,
        date: new Date(Date.now() - 120000).toISOString(),
        read: false,
        folder: 'inbox',
        labels: ['meeting', 'work', 'important'],
        important: true,
      },
    ];
    setEmails(mockEmails);
  }, []);

  // Get initials from name
  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  // Get time ago string
  const getTimeAgo = (date: string) => {
    const now = new Date();
    const emailDate = new Date(date);
    const diffInSeconds = Math.floor((now.getTime() - emailDate.getTime()) / 1000);

    if (diffInSeconds < 60) return 'just now';
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)} minutes ago`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)} hours ago`;
    if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)} days ago`;
    if (diffInSeconds < 2592000) return `${Math.floor(diffInSeconds / 604800)} weeks ago`;
    return `${Math.floor(diffInSeconds / 2592000)} months ago`;
  };

  const handleSendEmail = async () => {
    if (!composeTo || !composeSubject || !composeBody) {
      alert('Por favor completa todos los campos');
      return;
    }

    setIsSendingEmail(true);
    try {
      // TODO: Implementar llamada a API para enviar email
      await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate API call

      alert('Email enviado exitosamente');
      setComposeTo('');
      setComposeSubject('');
      setComposeBody('');
      setEmailView('inbox');
    } catch (error) {
      console.error('Error sending email:', error);
      alert('Error al enviar email');
    } finally {
      setIsSendingEmail(false);
    }
  };

  const handleRefreshEmails = async () => {
    setIsLoadingEmails(true);
    try {
      // TODO: Implementar llamada a API para obtener emails
      await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate API call
    } catch (error) {
      console.error('Error refreshing emails:', error);
    } finally {
      setIsLoadingEmails(false);
    }
  };

  const handleSendWhatsApp = async () => {
    if (!whatsappMessage.trim() || !selectedChat) return;

    setIsSendingWhatsApp(true);
    try {
      await whatsappAPI.sendMessage(selectedChat, whatsappMessage);
      setWhatsAppMessage('');
      // Refresh messages after sending
      await fetchMessages(selectedChat);
      // Also refresh conversations to update last message
      await fetchConversations();
    } catch (error) {
      console.error('Error sending WhatsApp:', error);
      alert('Error al enviar mensaje de WhatsApp');
    } finally {
      setIsSendingWhatsApp(false);
    }
  };

  // Render message status icon
  const renderMessageStatus = (status: string, direction: string) => {
    if (direction === 'inbound') return null;

    switch (status) {
      case 'sent':
        return <Check className="h-3 w-3 text-gray-400" />;
      case 'delivered':
        return <CheckCheck className="h-3 w-3 text-gray-400" />;
      case 'read':
        return <CheckCheck className="h-3 w-3 text-blue-500" />;
      case 'failed':
        return <AlertCircle className="h-3 w-3 text-red-500" />;
      default:
        return <Clock className="h-3 w-3 text-gray-400" />;
    }
  };

  const filteredEmails = emails
    .filter(email => email.folder === selectedFolder)
    .filter(email => emailFilter === 'all' || !email.read);

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="container mx-auto max-w-full">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <MessageSquare className="h-6 w-6 text-blue-600" />
            Comunicaciones
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Gestiona tus comunicaciones por email y WhatsApp desde un solo lugar
          </p>
        </div>

        {/* Main Tabs */}
        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'email' | 'whatsapp')} className="w-full">
          <TabsList className="grid w-full max-w-md grid-cols-2 mb-6 bg-slate-100">
            <TabsTrigger
              value="email"
              className="data-[state=active]:bg-blue-600 data-[state=active]:text-white flex items-center gap-2"
            >
              <Mail className="h-4 w-4" />
              Email
            </TabsTrigger>
            <TabsTrigger
              value="whatsapp"
              className="data-[state=active]:bg-green-600 data-[state=active]:text-white flex items-center gap-2"
            >
              <MessageSquare className="h-4 w-4" />
              WhatsApp
            </TabsTrigger>
          </TabsList>

          {/* EMAIL TAB */}
          <TabsContent value="email" className="mt-0">
            {emailView === 'compose' ? (
              <Card className="border-slate-200">
                <CardHeader>
                  <CardTitle>Redactar Email</CardTitle>
                  <CardDescription>Envía un nuevo email</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="to">Para</Label>
                    <Input
                      id="to"
                      type="email"
                      placeholder="destinatario@example.com"
                      value={composeTo}
                      onChange={(e) => setComposeTo(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="subject">Asunto</Label>
                    <Input
                      id="subject"
                      placeholder="Asunto del email"
                      value={composeSubject}
                      onChange={(e) => setComposeSubject(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="body">Mensaje</Label>
                    <Textarea
                      id="body"
                      rows={10}
                      placeholder="Escribe tu mensaje aquí..."
                      value={composeBody}
                      onChange={(e) => setComposeBody(e.target.value)}
                    />
                  </div>
                  <div className="flex gap-2">
                    <Button onClick={handleSendEmail} disabled={isSendingEmail}>
                      {isSendingEmail && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                      <Send className="mr-2 h-4 w-4" />
                      Enviar
                    </Button>
                    <Button variant="outline" onClick={() => setEmailView('inbox')}>
                      Cancelar
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ) : (
              <div className="grid grid-cols-12 gap-4">
                {/* Left Sidebar - Folders */}
                <div className="col-span-2">
                  <Card className="border-slate-200">
                    <CardContent className="p-4 space-y-1">
                      <Button
                        className="w-full mb-4 bg-blue-600 hover:bg-blue-700"
                        onClick={() => setEmailView('compose')}
                      >
                        <Plus className="mr-2 h-4 w-4" />
                        Redactar
                      </Button>

                      {folders.map((folder) => {
                        const Icon = folder.icon;
                        const isSelected = selectedFolder === folder.id;
                        return (
                          <button
                            key={folder.id}
                            onClick={() => setSelectedFolder(folder.id)}
                            className={`w-full flex items-center justify-between px-3 py-2 rounded-md text-sm transition-colors ${
                              isSelected
                                ? 'bg-green-50 text-green-700 font-medium'
                                : 'text-gray-700 hover:bg-gray-100'
                            }`}
                          >
                            <div className="flex items-center gap-2">
                              <Icon className={`h-4 w-4 ${isSelected ? 'text-green-700' : folder.color}`} />
                              <span>{folder.name}</span>
                            </div>
                            {folder.count > 0 && (
                              <span className={`text-xs px-2 py-0.5 rounded-full ${
                                isSelected ? 'bg-green-200 text-green-800' : 'bg-gray-200 text-gray-700'
                              }`}>
                                {folder.count}
                              </span>
                            )}
                          </button>
                        );
                      })}
                    </CardContent>
                  </Card>
                </div>

                {/* Middle - Email List */}
                <div className="col-span-5">
                  <Card className="border-slate-200">
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <div>
                          <CardTitle className="text-lg capitalize">{selectedFolder}</CardTitle>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={handleRefreshEmails}
                          disabled={isLoadingEmails}
                        >
                          {isLoadingEmails ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <RefreshCw className="h-4 w-4" />
                          )}
                        </Button>
                      </div>
                      <div className="flex gap-2 mt-3">
                        <Button
                          variant={emailFilter === 'all' ? 'default' : 'ghost'}
                          size="sm"
                          onClick={() => setEmailFilter('all')}
                          className="h-8"
                        >
                          All mail
                        </Button>
                        <Button
                          variant={emailFilter === 'unread' ? 'default' : 'ghost'}
                          size="sm"
                          onClick={() => setEmailFilter('unread')}
                          className="h-8"
                        >
                          Unread
                        </Button>
                      </div>
                      <div className="relative mt-3">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                        <Input placeholder="Search" className="pl-10 h-9" />
                      </div>
                    </CardHeader>
                    <CardContent className="p-0">
                      {filteredEmails.length === 0 ? (
                        <div className="text-center py-12 text-gray-500">
                          <Inbox className="h-12 w-12 mx-auto mb-4 opacity-50" />
                          <p>No hay emails en esta carpeta</p>
                        </div>
                      ) : (
                        <div className="divide-y">
                          {filteredEmails.map((email) => (
                            <div
                              key={email.id}
                              onClick={() => setSelectedEmail(email)}
                              className={`p-4 cursor-pointer transition-colors hover:bg-slate-50 ${
                                !email.read ? 'bg-blue-50/50' : ''
                              } ${selectedEmail?.id === email.id ? 'bg-slate-100 border-l-4 border-blue-600' : ''}`}
                            >
                              <div className="flex gap-3">
                                {/* Avatar */}
                                <div className="flex-shrink-0">
                                  <div className={`w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center text-white text-sm font-semibold`}>
                                    {getInitials(email.fromName)}
                                  </div>
                                </div>

                                {/* Content */}
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-start justify-between gap-2 mb-1">
                                    <div className="flex items-center gap-2">
                                      {email.important && <Star className="h-4 w-4 text-yellow-500 fill-yellow-500" />}
                                      {!email.read && <div className="w-2 h-2 bg-blue-600 rounded-full"></div>}
                                      <span className={`text-sm truncate ${!email.read ? 'font-semibold' : 'font-medium'}`}>
                                        {email.fromName}
                                      </span>
                                    </div>
                                    <span className="text-xs text-gray-500 whitespace-nowrap">
                                      {getTimeAgo(email.date)}
                                    </span>
                                  </div>
                                  <h4 className={`text-sm mb-1 truncate ${!email.read ? 'font-semibold' : ''}`}>
                                    {email.subject}
                                  </h4>
                                  <p className="text-xs text-gray-600 line-clamp-2 mb-2">
                                    {email.body}
                                  </p>
                                  <div className="flex gap-1 flex-wrap">
                                    {email.labels.map((labelId) => {
                                      const label = labels.find(l => l.id === labelId);
                                      return label ? (
                                        <Badge
                                          key={labelId}
                                          variant="secondary"
                                          className={`${label.color} text-white text-xs px-2 py-0`}
                                        >
                                          {label.name}
                                        </Badge>
                                      ) : null;
                                    })}
                                  </div>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </div>

                {/* Right - Email Detail */}
                <div className="col-span-5">
                  {selectedEmail ? (
                    <Card className="border-slate-200">
                      <CardHeader className="border-b">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-2">
                              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center text-white text-sm font-semibold">
                                {getInitials(selectedEmail.fromName)}
                              </div>
                              <div>
                                <h3 className="font-semibold text-base">{selectedEmail.fromName}</h3>
                                <p className="text-xs text-gray-600">Reply-To: {selectedEmail.from}</p>
                              </div>
                            </div>
                            <h2 className="text-lg font-semibold mt-3">{selectedEmail.subject}</h2>
                          </div>
                          <div className="text-right">
                            <p className="text-xs text-gray-500">
                              {new Date(selectedEmail.date).toLocaleString('en-US', {
                                month: 'short',
                                day: 'numeric',
                                year: 'numeric',
                                hour: 'numeric',
                                minute: '2-digit',
                                hour12: true,
                              })}
                            </p>
                          </div>
                        </div>
                        <div className="flex gap-2 mt-4">
                          <Button variant="outline" size="sm">
                            <Reply className="h-4 w-4 mr-2" />
                            Reply
                          </Button>
                          <Button variant="outline" size="sm">
                            <Forward className="h-4 w-4 mr-2" />
                            Forward
                          </Button>
                          <Button variant="outline" size="sm">
                            <Archive className="h-4 w-4 mr-2" />
                            Archive
                          </Button>
                          <Button variant="outline" size="sm">
                            <Trash className="h-4 w-4 mr-2" />
                            Delete
                          </Button>
                        </div>
                      </CardHeader>
                      <CardContent className="pt-6">
                        <div className="prose max-w-none mb-6">
                          <p className="whitespace-pre-wrap text-sm text-gray-700">
                            {selectedEmail.body}
                          </p>
                        </div>

                        <div className="border-t pt-6">
                          <div className="flex items-center justify-between mb-4">
                            <Label className="text-sm font-semibold">Reply {selectedEmail.fromName}...</Label>
                            <div className="flex items-center gap-2">
                              <Switch id="mute-thread" />
                              <Label htmlFor="mute-thread" className="text-sm text-gray-600">
                                Mute this thread
                              </Label>
                            </div>
                          </div>
                          <Textarea
                            placeholder="Type your reply..."
                            rows={5}
                            value={replyText}
                            onChange={(e) => setReplyText(e.target.value)}
                            className="mb-3"
                          />
                          <Button className="bg-green-600 hover:bg-green-700">
                            <Send className="h-4 w-4 mr-2" />
                            Send
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  ) : (
                    <Card className="border-slate-200 h-full">
                      <CardContent className="flex items-center justify-center h-full min-h-[600px]">
                        <div className="text-center text-gray-500">
                          <Mail className="h-16 w-16 mx-auto mb-4 opacity-50" />
                          <p className="text-lg">Selecciona un email para ver su contenido</p>
                          <p className="text-sm mt-2">Haz clic en un email de la lista para leerlo</p>
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </div>
              </div>
            )}
          </TabsContent>

          {/* WHATSAPP TAB */}
          <TabsContent value="whatsapp">
            <Card className="border-slate-200">
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <MessageSquare className="h-5 w-5 text-green-600" />
                    Conversaciones de WhatsApp
                  </CardTitle>
                  <CardDescription>
                    Gestiona tus conversaciones de WhatsApp con clientes
                  </CardDescription>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={fetchConversations}
                  disabled={isLoadingConversations}
                >
                  {isLoadingConversations ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <RefreshCw className="h-4 w-4" />
                  )}
                </Button>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-12 gap-4">
                  {/* Chats List */}
                  <div className="col-span-4 border-r pr-4">
                    <div className="mb-4">
                      <div className="relative">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                        <Input
                          placeholder="Buscar conversaciones..."
                          className="pl-10"
                          value={whatsappSearch}
                          onChange={(e) => setWhatsappSearch(e.target.value)}
                        />
                      </div>
                    </div>
                    <div className="space-y-2 max-h-[450px] overflow-y-auto">
                      {isLoadingConversations ? (
                        <div className="text-center py-8">
                          <Loader2 className="h-8 w-8 animate-spin mx-auto text-green-600" />
                          <p className="text-sm text-gray-500 mt-2">Cargando conversaciones...</p>
                        </div>
                      ) : conversations.length === 0 ? (
                        <div className="text-center py-8 text-gray-500">
                          <MessageSquare className="h-12 w-12 mx-auto mb-4 opacity-50" />
                          <p className="text-sm">No hay conversaciones</p>
                        </div>
                      ) : (
                        conversations.map((conv) => (
                          <div
                            key={conv.conversation_id}
                            className={`p-3 border rounded-lg cursor-pointer transition-colors hover:bg-slate-50 ${
                              selectedChat === conv.conversation_id ? 'bg-green-50 border-green-200' : 'border-slate-200'
                            }`}
                            onClick={() => setSelectedChat(conv.conversation_id)}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <div className="h-8 w-8 rounded-full bg-green-100 flex items-center justify-center text-green-700 font-semibold text-xs">
                                  {conv.customer_name
                                    ? getInitials(conv.customer_name)
                                    : conv.profile_name
                                    ? getInitials(conv.profile_name)
                                    : conv.conversation_id.slice(-2)}
                                </div>
                                <div>
                                  <span className="font-semibold text-sm block">
                                    {conv.customer_name || conv.profile_name || conv.conversation_id}
                                  </span>
                                  {conv.customer_name && (
                                    <span className="text-xs text-gray-500">{conv.conversation_id}</span>
                                  )}
                                </div>
                              </div>
                              <div className="text-right">
                                <span className="text-xs text-gray-500 block">
                                  {getTimeAgo(conv.last_message_time)}
                                </span>
                                {conv.unread_count > 0 && (
                                  <Badge className="bg-green-600 text-white text-xs mt-1">
                                    {conv.unread_count}
                                  </Badge>
                                )}
                              </div>
                            </div>
                            <p className="text-sm text-gray-600 mt-2 line-clamp-1 flex items-center gap-1">
                              {conv.last_direction === 'outbound' && (
                                <span className="text-gray-400">
                                  {renderMessageStatus(conv.last_status, 'outbound')}
                                </span>
                              )}
                              {conv.last_message}
                            </p>
                          </div>
                        ))
                      )}
                    </div>
                  </div>

                  {/* Chat Area */}
                  <div className="col-span-8">
                    {selectedChat ? (
                      <div className="flex flex-col h-[500px]">
                        {/* Chat Header */}
                        <div className="pb-4 border-b">
                          <div className="flex items-center gap-3">
                            <div className="h-10 w-10 rounded-full bg-green-100 flex items-center justify-center text-green-700 font-semibold">
                              {selectedConversation?.customer_name
                                ? getInitials(selectedConversation.customer_name)
                                : selectedConversation?.profile_name
                                ? getInitials(selectedConversation.profile_name)
                                : selectedChat.slice(-2)}
                            </div>
                            <div>
                              <h3 className="font-semibold">
                                {selectedConversation?.customer_name || selectedConversation?.profile_name || selectedChat}
                              </h3>
                              <p className="text-sm text-gray-500">{selectedChat}</p>
                            </div>
                          </div>
                        </div>

                        {/* Messages */}
                        <div className="flex-1 overflow-y-auto py-4 space-y-3">
                          {isLoadingMessages ? (
                            <div className="text-center py-8">
                              <Loader2 className="h-6 w-6 animate-spin mx-auto text-green-600" />
                            </div>
                          ) : currentMessages.length === 0 ? (
                            <div className="text-center py-8 text-gray-500">
                              <p className="text-sm">No hay mensajes en esta conversación</p>
                            </div>
                          ) : (
                            currentMessages.map((msg) => (
                              <div
                                key={msg.id}
                                className={`flex ${msg.direction === 'inbound' ? 'justify-start' : 'justify-end'}`}
                              >
                                <div
                                  className={`max-w-xs px-4 py-2 rounded-lg ${
                                    msg.direction === 'inbound'
                                      ? 'bg-gray-100 text-gray-900'
                                      : 'bg-green-600 text-white'
                                  }`}
                                >
                                  <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                                  <div className={`flex items-center justify-end gap-1 mt-1 ${
                                    msg.direction === 'inbound' ? 'text-gray-500' : 'text-green-100'
                                  }`}>
                                    <span className="text-xs">
                                      {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                    </span>
                                    {renderMessageStatus(msg.status, msg.direction)}
                                  </div>
                                </div>
                              </div>
                            ))
                          )}
                        </div>

                        {/* Input */}
                        <div className="pt-4 border-t">
                          <div className="flex gap-2">
                            <Input
                              placeholder="Escribe un mensaje..."
                              value={whatsappMessage}
                              onChange={(e) => setWhatsAppMessage(e.target.value)}
                              onKeyPress={(e) => {
                                if (e.key === 'Enter' && !e.shiftKey) {
                                  e.preventDefault();
                                  handleSendWhatsApp();
                                }
                              }}
                            />
                            <Button onClick={handleSendWhatsApp} disabled={isSendingWhatsApp || !whatsappMessage.trim()}>
                              {isSendingWhatsApp ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                <Send className="h-4 w-4" />
                              )}
                            </Button>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center justify-center h-[500px] text-gray-500">
                        <div className="text-center">
                          <MessageSquare className="h-16 w-16 mx-auto mb-4 opacity-50" />
                          <p>Selecciona una conversación para empezar</p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
