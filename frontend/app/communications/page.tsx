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
  const [whatsappMessages, setWhatsAppMessages] = useState<WhatsAppMessage[]>([]);
  const [selectedChat, setSelectedChat] = useState<string | null>(null);
  const [whatsappMessage, setWhatsAppMessage] = useState('');
  const [isSendingWhatsApp, setIsSendingWhatsApp] = useState(false);

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

  // Mock data for development
  useEffect(() => {
    // Simulate loading emails
    const mockEmails: Email[] = [
      {
        id: '1',
        from: 'williamsmith@example.com',
        fromName: 'William Smith',
        to: 'info@miempresa.com',
        subject: 'Meeting Tomorrow',
        body: `Hi, let's have a meeting tomorrow to discuss the project. I've been reviewing the project details and have some ideas I'd like to share. It's crucial that we align on our next steps to ensure the project's success.

Please come prepared with any questions or insights you may have. Looking forward to our meeting!

Best regards,
William`,
        date: new Date(Date.now() - 120000).toISOString(), // about 2 minutes ago
        read: false,
        folder: 'inbox',
        labels: ['meeting', 'work', 'important'],
        important: true,
      },
      {
        id: '2',
        from: 'alicesmith@example.com',
        fromName: 'Alice Smith',
        to: 'info@miempresa.com',
        subject: 'Re: Project Update',
        body: `Thank you for the project update. It looks great! I've gone through the report, and the progress is impressive. The team has done a fantastic job, and I appreciate the hard work everyone has put in.

Let's schedule a follow-up meeting to discuss the next steps.`,
        date: new Date(Date.now() - 7200000).toISOString(), // 2 hours ago
        read: true,
        folder: 'inbox',
        labels: ['work', 'important'],
        important: false,
      },
      {
        id: '3',
        from: 'bobjohnson@example.com',
        fromName: 'Bob Johnson',
        to: 'info@miempresa.com',
        subject: 'Weekend Plans',
        body: `Any plans for the weekend? I was thinking of going hiking in the nearby mountains. It's been a while since we had some outdoor fun. If you're interested, let me know!`,
        date: new Date(Date.now() - 172800000).toISOString(), // 2 days ago
        read: true,
        folder: 'inbox',
        labels: ['personal'],
        important: false,
      },
      {
        id: '4',
        from: 'emilydavis@example.com',
        fromName: 'Emily Davis',
        to: 'info@miempresa.com',
        subject: 'Re: Question about Budget',
        body: `I have a question about the budget for the upcoming project. It seems like there's a discrepancy in the allocation of resources. I've reviewed the documents and think we need to discuss this further.

Can we schedule a call to go over the details?`,
        date: new Date(Date.now() - 259200000).toISOString(), // 3 days ago
        read: false,
        folder: 'inbox',
        labels: ['work', 'budget'],
        important: false,
      },
      {
        id: '5',
        from: 'michaelwilson@example.com',
        fromName: 'Michael Wilson',
        to: 'info@miempresa.com',
        subject: 'Important Announcement',
        body: `I have an important announcement to make during our team meeting. It pertains to a strategic shift in our approach and some exciting upcoming changes. Please make sure to attend.`,
        date: new Date(Date.now() - 345600000).toISOString(), // 4 days ago
        read: false,
        folder: 'inbox',
        labels: ['work', 'important'],
        important: true,
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
