import React, { useState, useEffect, useContext } from 'react';
import { useSearchParams } from 'react-router-dom';
import api from '../api/axios';
import { AuthContext } from '../context/AuthContext';
import { MessageSquare, Send } from 'lucide-react';

const Messages = () => {
  const { user } = useContext(AuthContext);
  const [searchParams] = useSearchParams();

  const [conversations, setConversations] = useState([]);
  const [activePartner, setActivePartner] = useState(searchParams.get('hub_id') ? `hub_${searchParams.get('hub_id')}` : null);
  const [activePartnerName, setActivePartnerName] = useState(searchParams.get('hub_name') || '');
  const [messages, setMessages] = useState([]);
  const [newText, setNewText] = useState('');

  useEffect(() => {
    fetchConversations();
  }, []);

  useEffect(() => {
    if (activePartner) {
      fetchThread(activePartner);
    }
  }, [activePartner]);

  const fetchConversations = async () => {
    try {
      const res = await api.get('/api/messages/conversations');
      setConversations(res.data || []);
      if (!activePartner && res.data.length > 0) {
        const first = res.data[0];
        const key = first.recipient_id === user?.id ? first.sender_id : (first.recipient_id || `hub_${first.hub_directory_id}`);
        setActivePartner(key);
        setActivePartnerName(first.hub_name || first.recipient_name || first.sender_name || 'Conversation');
      }
    } catch (err) {
      console.error(err);
    }
  };

  const fetchThread = async (partnerId) => {
    try {
      const res = await api.get(`/api/messages/thread/${partnerId}`);
      setMessages(res.data || []);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!newText.trim() || !activePartner) return;

    try {
      const payload = { message_text: newText };
      if (activePartner.startsWith('hub_')) {
        payload.hub_directory_id = activePartner.replace('hub_', '');
      } else {
        payload.recipient_id = activePartner;
      }

      await api.post('/api/messages', payload);
      setNewText('');
      fetchThread(activePartner);
      fetchConversations();
    } catch (err) {
      alert('Failed to send message');
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
      <div className="border-b pb-4">
        <h1 className="text-2xl font-extrabold text-gray-900 flex items-center gap-2">
          <MessageSquare className="w-6 h-6 text-emerald-700" /> Messaging & Buyer Pitches
        </h1>
      </div>

      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm grid grid-cols-1 md:grid-cols-3 min-h-[500px] overflow-hidden">
        {/* Conversations List */}
        <div className="border-r border-gray-100 p-4 space-y-2 bg-gray-50/50">
          <span className="text-xs font-bold text-gray-500 uppercase tracking-wider block mb-2">Conversations & Hub Pitches</span>
          {conversations.map((c) => {
            const key = c.recipient_id === user?.id ? c.sender_id : (c.recipient_id || `hub_${c.hub_directory_id}`);
            const name = c.hub_name || (c.recipient_id === user?.id ? c.sender_name : c.recipient_name) || 'Buyer Pitch';

            return (
              <button
                key={c.id}
                onClick={() => { setActivePartner(key); setActivePartnerName(name); }}
                className={`w-full text-left p-3 rounded-xl border text-xs transition-all ${activePartner === key ? 'bg-emerald-800 text-white border-emerald-900 font-bold' : 'bg-white text-gray-800 border-gray-200 hover:bg-emerald-50'}`}
              >
                <div className="font-bold truncate">{name}</div>
                <div className="text-[10px] opacity-80 truncate mt-0.5">{c.message_text}</div>
              </button>
            );
          })}
        </div>

        {/* Message Thread */}
        <div className="md:col-span-2 p-6 flex flex-col justify-between space-y-4">
          <div className="border-b pb-3 font-bold text-gray-900 text-sm">
            {activePartnerName || 'Select a conversation'}
          </div>

          <div className="flex-1 space-y-3 overflow-y-auto max-h-[350px] p-2">
            {messages.map((m) => {
              const isMine = m.sender_id === user?.id;
              return (
                <div key={m.id} className={`flex ${isMine ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[75%] p-3 rounded-2xl text-xs ${isMine ? 'bg-emerald-700 text-white rounded-br-none' : 'bg-gray-100 text-gray-800 rounded-bl-none'}`}>
                    <p>{m.message_text}</p>
                    <span className="text-[9px] opacity-75 block text-right mt-1">{new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                  </div>
                </div>
              );
            })}
          </div>

          <form onSubmit={handleSendMessage} className="flex gap-2 pt-2 border-t">
            <input
              type="text"
              value={newText}
              onChange={e=>setNewText(e.target.value)}
              placeholder="Type message or surplus pitch..."
              className="flex-1 border p-2.5 rounded-xl text-xs"
            />
            <button type="submit" className="bg-emerald-700 hover:bg-emerald-800 text-white font-bold px-4 py-2.5 rounded-xl text-xs flex items-center gap-1">
              <Send className="w-4 h-4" /> Send
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default Messages;
