import React, { useState } from 'react';
import axios from 'axios';
import ChatHistory from '../components/chat/ChatHistory';
import ChatInput from '../components/chat/ChatInput';
import { useAuth } from '../contexts/AuthContext';

const ChatPage = () => {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const { token } = useAuth();

  const handleSendMessage = async (content) => {
    if (!content.trim()) return;

    // Add user message to chat
    const userMessage = { role: 'user', content };
    setMessages(prevMessages => [...prevMessages, userMessage]);
    
    // Set loading state
    setIsLoading(true);

    try {
      // Send the message to the backend
      const response = await axios.post('/api/search', {
        query: content
      }, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      // Add assistant response to chat
      if (response.data) {
        const assistantMessage = {
          role: 'assistant',
          content: response.data.answer,
          sources: response.data.sources || []
        };
        
        setMessages(prevMessages => [...prevMessages, assistantMessage]);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      
      // Add error message
      const errorMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error while processing your request. Please try again later.'
      };
      
      setMessages(prevMessages => [...prevMessages, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="chat-page">
      <h1 className="govuk-heading-l">Policy Search Assistant</h1>
      
      <div className="chat-container">
        <div className="chat-container__history">
          <ChatHistory messages={messages} isLoading={isLoading} />
        </div>
        
        <div className="chat-container__input">
          <ChatInput onSendMessage={handleSendMessage} isLoading={isLoading} />
        </div>
      </div>
    </div>
  );
};

export default ChatPage;