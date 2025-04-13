import React, { useState } from 'react';

const ChatInput = ({ onSendMessage, isLoading }) => {
  const [message, setMessage] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    
    if (message.trim() && !isLoading) {
      onSendMessage(message);
      setMessage('');
    }
  };

  return (
    <div className="chat-input">
      <form onSubmit={handleSubmit} className="chat-input__form">
        <div className="govuk-form-group">
          <label className="govuk-label govuk-visually-hidden" htmlFor="message">
            Enter your message
          </label>
          <div className="chat-input__container">
            <textarea
              className="govuk-textarea chat-input__textarea"
              id="message"
              name="message"
              rows="3"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Type your question about company policies..."
              disabled={isLoading}
            />
            <button
              type="submit"
              className="govuk-button chat-input__button"
              data-module="govuk-button"
              disabled={isLoading || !message.trim()}
            >
              {isLoading ? 'Sending...' : 'Send'}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
};

export default ChatInput;