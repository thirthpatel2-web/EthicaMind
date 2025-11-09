import React, { useState, useRef, useEffect } from "react";

export default function ChatWindow() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]); // {from: 'user'|'ai', text: '...'}
  const [showCrisisModal, setShowCrisisModal] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    scrollToBottom();
  }, [messages, showCrisisModal]);

  function scrollToBottom() {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }

  async function sendMessage() {
    const trimmed = input.trim();
    if (!trimmed) return;

    // Add user message locally
    setMessages((m) => [...m, { from: "user", text: trimmed }]);
    setInput("");

    try {
     
const BACKEND_URL = process.env.REACT_APP_API_URL || "http://localhost:5000";
const resp = await fetch(`${BACKEND_URL}/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: trimmed }),
      });

      if (!resp.ok) {
        const text = await resp.text();
        setMessages((m) => [...m, { from: "ai", text: `Error: ${resp.status} ${text}` }]);
        return;
      }

      const data = await resp.json();

      // CRITICAL TRIAGE LOGIC: if backend signals crisis, show full-screen modal and stop chat.
      if (data && data.type === "CRISIS_TRIAGE") {
        setShowCrisisModal(true);
        return;
      }

      if (data && data.type === "chat") {
        setMessages((m) => [...m, { from: "ai", text: data.message }]);
        return;
      }

      // Unknown response shape
      setMessages((m) => [...m, { from: "ai", text: "Sorry, I didn't understand the response." }]);
    } catch (err) {
      setMessages((m) => [...m, { from: "ai", text: `Network error: ${err.message}` }]);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  return (
    <div className="chat-window">
      <div className="chat-header">
        <h2>Chat with EthicaMind</h2>
        <p className="sub">A responsible wellness assistant (prototype)</p>
      </div>

      <div className="chat-history" role="log" aria-live="polite">
        {messages.map((m, idx) => (
          <div key={idx} className={`bubble ${m.from === "user" ? "user" : "ai"}`}>
            <div className="bubble-text">{m.text}</div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-area">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your message..."
          rows={2}
        />
        <button className="send-btn" onClick={sendMessage}>
          Send
        </button>
      </div>

      {showCrisisModal && (
        <div className="crisis-modal">
          <div className="crisis-content" role="dialog" aria-modal="true">
            <h2>It sounds like you are in serious distress</h2>
            <p>Your safety is most important. Here are resources that can help you right now:</p>
            <div className="crisis-actions">
              <a href="tel:911" className="crisis-button">Call 911</a>
              <a href="sms:741741" className="crisis-button">Text Crisis Line</a>
            </div>
            <button className="crisis-close" onClick={() => setShowCrisisModal(false)}>Close</button>
          </div>
        </div>
      )}
    </div>
  );
}
