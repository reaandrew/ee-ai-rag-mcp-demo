import React from 'react';
import SourceCitation from './SourceCitation';

const ChatMessage = ({ message }) => {
  const { role, content, sources } = message;
  
  // Format the message content to handle line breaks and citations
  const formatContent = (text) => {
    if (!text) return '';
    
    // Replace line breaks with <br /> tags
    return text.split('\n').map((line, i) => (
      <React.Fragment key={i}>
        {line}
        {i < text.split('\n').length - 1 && <br />}
      </React.Fragment>
    ));
  };
  
  return (
    <div 
      className={`chat-message ${role === 'user' ? 'chat-message--user' : 'chat-message--assistant'}`}
      data-testid="message-container"
    >
      <div className="chat-message__avatar">
        {role === 'user' ? '👤' : '🤖'}
      </div>
      <div className="chat-message__content">
        <div className="chat-message__bubble">
          <div className="chat-message__text">
            {formatContent(content)}
          </div>
        </div>
        
        {role === 'assistant' && sources && sources.length > 0 && (
          <div className="chat-message__sources">
            <h4 className="govuk-heading-s">Sources:</h4>
            <ul className="govuk-list">
              {sources.map((source, index) => (
                <li key={index}>
                  <SourceCitation source={source} />
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatMessage;