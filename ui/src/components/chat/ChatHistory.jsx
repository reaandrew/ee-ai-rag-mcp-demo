import React, { useRef, useEffect } from 'react';
import ChatMessage from './ChatMessage';

const ChatHistory = ({ messages, isLoading }) => {
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  return (
    <div className="chat-history">
      {messages.length === 0 ? (
        <div className="chat-history__empty">
          <h2 className="govuk-heading-m">Welcome to the Policy Search Assistant!</h2>
          <p className="govuk-body">Ask any question about company policies and I'll help you find the answers.</p>
        </div>
      ) : (
        messages.map((message, index) => (
          <ChatMessage key={index} message={message} />
        ))
      )}
      
      {isLoading && (
        <div className="chat-history__loading">
          <div className="chat-message chat-message--assistant">
            <div className="chat-message__avatar">
              🤖
            </div>
            <div className="chat-message__content">
              <div className="chat-message__bubble">
                <div className="chat-message__text">
                  <div className="chat-message__typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
      
      <div ref={messagesEndRef} />
    </div>
  );
};

export default ChatHistory;