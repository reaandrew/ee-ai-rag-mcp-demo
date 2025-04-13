import React, { useState, useCallback } from 'react';
import axios from 'axios';
import ChatHistory from '../components/chat/ChatHistory';
import ChatInput from '../components/chat/ChatInput';

const ChatPage = () => {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [apiUrl, setApiUrl] = useState('');
  const [jwtToken, setJwtToken] = useState('');

  const handleSendMessage = useCallback(async (content) => {
    if (!content.trim() || !apiUrl || !jwtToken) return;

    // Add user message to chat
    const userMessage = { role: 'user', content };
    setMessages(prevMessages => [...prevMessages, userMessage]);
    
    // Set loading state
    setIsLoading(true);

    try {
      // Make direct API call with JWT token
      const response = await axios({
        method: 'post',
        url: apiUrl,
        data: { query: content },
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${jwtToken}`
        }
      });

      // Add assistant response to chat
      const assistantMessage = {
        role: 'assistant',
        content: response.data.answer,
        sources: response.data.sources || []
      };
      
      setMessages(prevMessages => [...prevMessages, assistantMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      
      // Add error message
      const errorMessage = {
        role: 'assistant',
        content: `Error: ${error.message || 'Unknown error'}`
      };
      
      setMessages(prevMessages => [...prevMessages, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }, [apiUrl, jwtToken]);

  return (
    <div className="chat-page">
      <h1 className="govuk-heading-l">Policy Search Assistant</h1>
      
      <div className="govuk-form-group">
        <label className="govuk-label" htmlFor="api-url">API URL</label>
        <input
          className="govuk-input"
          id="api-url"
          name="api-url"
          type="text"
          value={apiUrl}
          onChange={(e) => setApiUrl(e.target.value)}
          placeholder="https://xxxxx.execute-api.eu-west-2.amazonaws.com/search"
        />
        <span className="govuk-hint">Enter your full API Gateway URL including the /search path</span>
      </div>

      <div className="govuk-form-group">
        <label className="govuk-label" htmlFor="jwt-token">JWT Token</label>
        <input
          className="govuk-input"
          id="jwt-token"
          name="jwt-token"
          type="password"
          value={jwtToken}
          onChange={(e) => setJwtToken(e.target.value)}
          placeholder="Enter your JWT token"
        />
      </div>
      
      <div className="chat-container">
        <div className="chat-container__history">
          <ChatHistory messages={messages} isLoading={isLoading} />
        </div>
        
        <div className="chat-container__input">
          <ChatInput 
            onSendMessage={handleSendMessage} 
            isLoading={isLoading} 
            isDisabled={!apiUrl || !jwtToken}
          />
        </div>
      </div>
    </div>
  );
};

export default ChatPage;