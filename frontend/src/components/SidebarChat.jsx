import { useState, useRef, useEffect } from 'react';
import { Send, Bot, ShieldAlert, Sparkles, Loader2 } from 'lucide-react';
import './SidebarChat.css';

const parseInlineMarkdown = (text) => {
  const parts = text.split(/(\*\*.*?\*\*)/);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i} style={{ color: '#fff', fontWeight: 'bold' }}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
};

const renderMessageContent = (content) => {
  if (!content) return null;
  const lines = content.split('\n');
  return lines.map((line, idx) => {
    const trimmed = line.trim();
    if (trimmed.startsWith('```')) {
      return null;
    }
    if (trimmed.startsWith('### ')) {
      return <h4 key={idx} style={{ margin: '8px 0 4px 0', color: '#fff', fontWeight: 600 }}>{trimmed.slice(4)}</h4>;
    }
    if (trimmed.startsWith('## ')) {
      return <h3 key={idx} style={{ margin: '12px 0 6px 0', color: '#fff', fontWeight: 600 }}>{trimmed.slice(3)}</h3>;
    }
    if (trimmed.startsWith('# ')) {
      return <h2 key={idx} style={{ margin: '16px 0 8px 0', color: '#fff', fontWeight: 700 }}>{trimmed.slice(2)}</h2>;
    }
    if (trimmed.startsWith('* ') || trimmed.startsWith('- ')) {
      return (
        <ul key={idx} style={{ margin: '4px 0 4px 20px', listStyleType: 'disc', paddingLeft: '5px' }}>
          <li style={{ color: 'var(--text-primary)' }}>{parseInlineMarkdown(trimmed.slice(2))}</li>
        </ul>
      );
    }
    return <p key={idx} style={{ margin: '6px 0', minHeight: '1em' }}>{parseInlineMarkdown(line)}</p>;
  });
};

const parsePartialJson = (rawText) => {
  let response_text = '';
  let dispute_letter = '';
  let is_dispute_request = false;
  let isJson = false;

  const trimmed = rawText.trim();
  if (trimmed.startsWith('{')) {
    isJson = true;
    
    try {
      const parsed = JSON.parse(trimmed);
      return {
        isJson: true,
        response_text: parsed.response_text || '',
        is_dispute_request: !!parsed.is_dispute_request,
        dispute_letter: parsed.dispute_letter || ''
      };
    } catch (e) {
      // Partial parse logic using RegExp for streaming chunks
      const respMatch = trimmed.match(/"response_text"\s*:\s*"(.*?)(?:"\s*,|"\s*}|$)/s);
      if (respMatch) {
        response_text = respMatch[1]
          .replace(/\\n/g, '\n')
          .replace(/\\"/g, '"')
          .replace(/\\r/g, '');
      } else {
        const incompleteMatch = trimmed.match(/"response_text"\s*:\s*"(.*)$/s);
        if (incompleteMatch) {
          response_text = incompleteMatch[1]
            .replace(/\\n/g, '\n')
            .replace(/\\"/g, '"')
            .replace(/\\r/g, '');
        }
      }

      const letterMatch = trimmed.match(/"dispute_letter"\s*:\s*"(.*?)(?:"\s*}|"$)/s);
      if (letterMatch) {
        dispute_letter = letterMatch[1]
          .replace(/\\n/g, '\n')
          .replace(/\\"/g, '"')
          .replace(/\\r/g, '');
      } else {
        const incompleteLetterMatch = trimmed.match(/"dispute_letter"\s*:\s*"(.*)$/s);
        if (incompleteLetterMatch) {
          dispute_letter = incompleteLetterMatch[1]
            .replace(/\\n/g, '\n')
            .replace(/\\"/g, '"')
            .replace(/\\r/g, '');
        }
      }

      const disputeRequestMatch = trimmed.match(/"is_dispute_request"\s*:\s*(true|false)/);
      if (disputeRequestMatch) {
        is_dispute_request = disputeRequestMatch[1] === 'true';
      }
    }
  }

  return { isJson, response_text, is_dispute_request, dispute_letter };
};

export default function SidebarChat({ anomalies }) {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hello! I am SpendWise AI, your local financial copilot. How can I help you analyze your statement today?' }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    try {
      // Create history array without the new message yet
      const history = messages.filter(m => m.role !== 'system');
      
      const res = await fetch('http://127.0.0.1:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage,
          history: history
        })
      });

      if (!res.ok) throw new Error('API Error');

      // Get the stream reader and decoder
      const reader = res.body.getReader();
      const decoder = new TextDecoder('utf-8');

      // Append a blank assistant message to fill in
      setMessages(prev => [...prev, { role: 'assistant', content: '' }]);
      setIsLoading(false); // Hide loader spinner as streaming has begun

      let done = false;
      let accumulatedText = '';

      while (!done) {
        const { value, done: doneReading } = await reader.read();
        done = doneReading;
        if (value) {
          const chunk = decoder.decode(value, { stream: !done });
          accumulatedText += chunk;

          // Update the last message in state
          setMessages(prev => {
            const updated = [...prev];
            if (updated.length > 0) {
              updated[updated.length - 1] = {
                role: 'assistant',
                content: accumulatedText
              };
            }
            return updated;
          });
        }
      }

    } catch (err) {
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: 'I encountered an error connecting to the local backend. Is the FastAPI server running?' 
      }]);
      setIsLoading(false);
    }
  };

  return (
    <div className="sidebar-chat glass-panel">
      <div className="chat-header">
        <div className="chat-title">
          <Bot size={24} className="accent-icon" />
          <div>
            <h3>AI Financial Coach</h3>
            <span className="status-badge">
              <span className="status-dot"></span> Local Network
            </span>
          </div>
        </div>
        
        {anomalies && anomalies.length > 0 && (
          <div className="anomaly-alert">
            <ShieldAlert size={14} />
            <span>{anomalies.length} Anomalies Flagged</span>
          </div>
        )}
      </div>

      <div className="chat-messages">
        {messages.map((msg, i) => {
          const parsed = parsePartialJson(msg.content);
          const displayContent = parsed.isJson ? parsed.response_text : msg.content;
          
          return (
            <div key={i} className={`message ${msg.role}`}>
              <div className="message-content">
                {msg.role === 'assistant' && <Sparkles size={14} className="msg-icon" />}
                <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  <div>{renderMessageContent(displayContent)}</div>
                  
                  {parsed.isJson && parsed.dispute_letter && (
                    <div className="dispute-letter-card animate-fade-in" style={{
                      background: 'rgba(0, 0, 0, 0.4)',
                      border: '1px solid rgba(255, 255, 255, 0.1)',
                      borderRadius: '8px',
                      padding: '1rem',
                      marginTop: '0.5rem',
                      width: '100%',
                      boxSizing: 'border-box'
                    }}>
                      <div style={{ 
                        display: 'flex', 
                        justifyContent: 'space-between', 
                        alignItems: 'center', 
                        marginBottom: '0.75rem', 
                        borderBottom: '1px solid rgba(255, 255, 255, 0.1)', 
                        paddingBottom: '0.5rem' 
                      }}>
                        <span style={{ fontWeight: 600, color: 'var(--accent-color)', fontSize: '0.8rem' }}>DRAFT DISPUTE LETTER</span>
                        <button 
                          onClick={() => navigator.clipboard.writeText(parsed.dispute_letter)}
                          style={{
                            background: 'var(--accent-color)',
                            border: 'none',
                            color: '#fff',
                            padding: '0.2rem 0.5rem',
                            borderRadius: '4px',
                            fontSize: '0.75rem',
                            cursor: 'pointer',
                            transition: 'background 0.2s'
                          }}
                        >
                          Copy
                        </button>
                      </div>
                      <pre style={{ 
                        whiteSpace: 'pre-wrap', 
                        fontFamily: 'Courier New, Courier, monospace', 
                        fontSize: '0.85rem',
                        color: '#cbd5e1', 
                        margin: 0, 
                        lineHeight: '1.4' 
                      }}>
                        {parsed.dispute_letter}
                      </pre>
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
        {isLoading && (
          <div className="message assistant loading">
            <div className="message-content">
              <Loader2 size={16} className="spin-icon" />
              <p>Analyzing local policies...</p>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form className="chat-input-area" onSubmit={handleSend}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about a charge or policy..."
          disabled={isLoading}
        />
        <button type="submit" disabled={!input.trim() || isLoading} className="btn-send">
          <Send size={18} />
        </button>
      </form>
    </div>
  );
}
