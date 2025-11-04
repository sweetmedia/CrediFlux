'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/lib/contexts/AuthContext';
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
} from 'lucide-react';

interface Email {
  id: string;
  from: string;
  to: string;
  subject: string;
  body: string;
  date: string;
  read: boolean;
}

interface WhatsAppMessage {
  id: string;
  from: string;
  to: string;
  message: string;
  timestamp: string;
  status: 'sent' | 'delivered' | 'read' | 'failed';
}

export default function CommunicationsPage() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const [activeTab, setActiveTab] = useState<'email' | 'whatsapp'>('email');
  const [emailView, setEmailView] = useState<'inbox' | 'compose'>('inbox');

  // Email states
  const [emails, setEmails] = useState<Email[]>([]);
  const [selectedEmail, setSelectedEmail] = useState<Email | null>(null);
  const [isLoadingEmails, setIsLoadingEmails] = useState(false);

  // Compose email states
  const [composeTo, setComposeTo] = useState('');
  const [composeSubject, setComposeSubject] = useState('');
  const [composeBody, setComposeBody] = useState('');
  const [isSendingEmail, setIsSendingEmail] = useState(false);

  // WhatsApp states
  const [whatsappMessages, setWhatsAppMessages] = useState<WhatsAppMessage[]>([]);
  const [selectedChat, setSelectedChat] = useState<string | null>(null);
  const [whatsappMessage, setWhatsAppMessage] = useState('');
  const [isSendingWhatsApp, setIsSendingWhatsApp] = useState(false);

  // Mock data for development
  useEffect(() => {
    // Simulate loading emails
    const mockEmails: Email[] = [
      {
        id: '1',
        from: 'cliente@example.com',
        to: 'info@miempresa.com',
        subject: 'Consulta sobre mi préstamo',
        body: 'Hola, tengo una pregunta sobre mi préstamo...',
        date: new Date().toISOString(),
        read: false,
      },
      {
        id: '2',
        from: 'otro@example.com',
        to: 'info@miempresa.com',
        subject: 'Solicitud de información',
        body: 'Buenos días, quisiera información sobre...',
        date: new Date(Date.now() - 86400000).toISOString(),
        read: true,
      },
    ];
    setEmails(mockEmails);

    // Simulate WhatsApp messages
    const mockWhatsApp: WhatsAppMessage[] = [
      {
        id: '1',
        from: '+18095551234',
        to: '+18099999999',
        message: 'Hola, recibí el recordatorio de pago',
        timestamp: new Date().toISOString(),
        status: 'read',
      },
    ];
    setWhatsAppMessages(mockWhatsApp);
  }, []);

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
      // TODO: Implementar llamada a API para enviar WhatsApp
      await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate API call

      const newMessage: WhatsAppMessage = {
        id: Date.now().toString(),
        from: '+18099999999',
        to: selectedChat,
        message: whatsappMessage,
        timestamp: new Date().toISOString(),
        status: 'sent',
      };

      setWhatsAppMessages([...whatsappMessages, newMessage]);
      setWhatsAppMessage('');
    } catch (error) {
      console.error('Error sending WhatsApp:', error);
      alert('Error al enviar mensaje de WhatsApp');
    } finally {
      setIsSendingWhatsApp(false);
    }
  };

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="container mx-auto max-w-7xl">
        {/* Header */}
        <div className="mb-8">
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
          <TabsContent value="email">
            <div className="grid grid-cols-12 gap-6">
              {/* Sidebar */}
              <div className="col-span-3">
                <Card className="border-slate-200">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base">Email</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <Button
                      variant={emailView === 'inbox' ? 'default' : 'ghost'}
                      className="w-full justify-start"
                      onClick={() => setEmailView('inbox')}
                    >
                      <Inbox className="mr-2 h-4 w-4" />
                      Bandeja de Entrada
                      {emails.filter(e => !e.read).length > 0 && (
                        <span className="ml-auto bg-blue-600 text-white text-xs rounded-full px-2 py-0.5">
                          {emails.filter(e => !e.read).length}
                        </span>
                      )}
                    </Button>
                    <Button
                      variant={emailView === 'compose' ? 'default' : 'ghost'}
                      className="w-full justify-start"
                      onClick={() => setEmailView('compose')}
                    >
                      <Plus className="mr-2 h-4 w-4" />
                      Redactar
                    </Button>
                  </CardContent>
                </Card>
              </div>

              {/* Main Content */}
              <div className="col-span-9">
                {/* INBOX VIEW */}
                {emailView === 'inbox' && (
                  <Card className="border-slate-200">
                    <CardHeader className="flex flex-row items-center justify-between">
                      <div>
                        <CardTitle>Bandeja de Entrada</CardTitle>
                        <CardDescription>
                          {emails.length} email(s) - {emails.filter(e => !e.read).length} no leído(s)
                        </CardDescription>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleRefreshEmails}
                        disabled={isLoadingEmails}
                      >
                        {isLoadingEmails ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <RefreshCw className="h-4 w-4" />
                        )}
                        <span className="ml-2">Actualizar</span>
                      </Button>
                    </CardHeader>
                    <CardContent>
                      {emails.length === 0 ? (
                        <div className="text-center py-12 text-gray-500">
                          <Inbox className="h-12 w-12 mx-auto mb-4 opacity-50" />
                          <p>No hay emails</p>
                          <p className="text-sm mt-2">Configura tu servidor SMTP para empezar a recibir emails</p>
                        </div>
                      ) : (
                        <div className="space-y-2">
                          {emails.map((email) => (
                            <div
                              key={email.id}
                              className={`p-4 border rounded-lg cursor-pointer transition-colors hover:bg-slate-50 ${
                                !email.read ? 'bg-blue-50 border-blue-200' : 'border-slate-200'
                              } ${selectedEmail?.id === email.id ? 'ring-2 ring-blue-500' : ''}`}
                              onClick={() => setSelectedEmail(email)}
                            >
                              <div className="flex items-start justify-between">
                                <div className="flex-1">
                                  <div className="flex items-center gap-2">
                                    {!email.read && (
                                      <div className="w-2 h-2 bg-blue-600 rounded-full"></div>
                                    )}
                                    <span className="font-semibold text-sm">{email.from}</span>
                                  </div>
                                  <p className="font-medium text-slate-900 mt-1">{email.subject}</p>
                                  <p className="text-sm text-slate-600 mt-1 line-clamp-2">{email.body}</p>
                                </div>
                                <div className="text-xs text-slate-500 ml-4">
                                  <Clock className="h-3 w-3 inline mr-1" />
                                  {new Date(email.date).toLocaleDateString()}
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Email Detail View */}
                      {selectedEmail && (
                        <div className="mt-6 p-6 border border-slate-200 rounded-lg bg-white">
                          <div className="flex items-start justify-between mb-4">
                            <div>
                              <h3 className="text-lg font-semibold">{selectedEmail.subject}</h3>
                              <p className="text-sm text-slate-600 mt-1">
                                De: <span className="font-medium">{selectedEmail.from}</span>
                              </p>
                              <p className="text-sm text-slate-600">
                                Para: <span className="font-medium">{selectedEmail.to}</span>
                              </p>
                            </div>
                            <span className="text-sm text-slate-500">
                              {new Date(selectedEmail.date).toLocaleString()}
                            </span>
                          </div>
                          <div className="prose max-w-none">
                            <p className="whitespace-pre-wrap">{selectedEmail.body}</p>
                          </div>
                          <div className="flex gap-2 mt-6 pt-4 border-t">
                            <Button size="sm">
                              <Send className="h-4 w-4 mr-2" />
                              Responder
                            </Button>
                            <Button variant="outline" size="sm">
                              Reenviar
                            </Button>
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )}

                {/* COMPOSE VIEW */}
                {emailView === 'compose' && (
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
                )}
              </div>
            </div>
          </TabsContent>

          {/* WHATSAPP TAB */}
          <TabsContent value="whatsapp">
            <Card className="border-slate-200">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <MessageSquare className="h-5 w-5 text-green-600" />
                  Conversaciones de WhatsApp
                </CardTitle>
                <CardDescription>
                  Gestiona tus conversaciones de WhatsApp con clientes
                </CardDescription>
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
                        />
                      </div>
                    </div>
                    <div className="space-y-2">
                      {whatsappMessages.length === 0 ? (
                        <div className="text-center py-8 text-gray-500">
                          <MessageSquare className="h-12 w-12 mx-auto mb-4 opacity-50" />
                          <p className="text-sm">No hay conversaciones</p>
                        </div>
                      ) : (
                        whatsappMessages.map((msg) => (
                          <div
                            key={msg.id}
                            className={`p-3 border rounded-lg cursor-pointer transition-colors hover:bg-slate-50 ${
                              selectedChat === msg.from ? 'bg-green-50 border-green-200' : 'border-slate-200'
                            }`}
                            onClick={() => setSelectedChat(msg.from)}
                          >
                            <div className="flex items-center justify-between">
                              <span className="font-semibold text-sm">{msg.from}</span>
                              <span className="text-xs text-gray-500">
                                {new Date(msg.timestamp).toLocaleTimeString()}
                              </span>
                            </div>
                            <p className="text-sm text-gray-600 mt-1 line-clamp-1">{msg.message}</p>
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
                          <h3 className="font-semibold">{selectedChat}</h3>
                          <p className="text-sm text-gray-500">WhatsApp</p>
                        </div>

                        {/* Messages */}
                        <div className="flex-1 overflow-y-auto py-4 space-y-3">
                          {whatsappMessages
                            .filter(m => m.from === selectedChat || m.to === selectedChat)
                            .map((msg) => (
                              <div
                                key={msg.id}
                                className={`flex ${msg.from === selectedChat ? 'justify-start' : 'justify-end'}`}
                              >
                                <div
                                  className={`max-w-xs px-4 py-2 rounded-lg ${
                                    msg.from === selectedChat
                                      ? 'bg-gray-100 text-gray-900'
                                      : 'bg-green-600 text-white'
                                  }`}
                                >
                                  <p className="text-sm">{msg.message}</p>
                                  <p className={`text-xs mt-1 ${
                                    msg.from === selectedChat ? 'text-gray-500' : 'text-green-100'
                                  }`}>
                                    {new Date(msg.timestamp).toLocaleTimeString()}
                                  </p>
                                </div>
                              </div>
                            ))}
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
