import { render, screen } from '@testing-library/react';
import ChatMessage from './ChatMessage';

describe('ChatMessage Component', () => {
  test('renders user message correctly', () => {
    const message = {
      role: 'user',
      content: 'What is our password policy?'
    };
    
    render(<ChatMessage message={message} />);
    
    expect(screen.getByText('What is our password policy?')).toBeInTheDocument();
    expect(screen.getByText('👤')).toBeInTheDocument();
  });
  
  test('renders assistant message correctly', () => {
    const message = {
      role: 'assistant',
      content: 'Passwords must be changed every 90 days.',
      sources: [
        {
          document_name: 'Password Policy',
          page_number: 2
        }
      ]
    };
    
    render(<ChatMessage message={message} />);
    
    expect(screen.getByText('Passwords must be changed every 90 days.')).toBeInTheDocument();
    expect(screen.getByText('🤖')).toBeInTheDocument();
    expect(screen.getByText('Sources:')).toBeInTheDocument();
    expect(screen.getByText('Password Policy')).toBeInTheDocument();
    expect(screen.getByText(', Page 2')).toBeInTheDocument();
  });
  
  test('handles multiline content correctly', () => {
    const message = {
      role: 'assistant',
      content: 'Line 1\nLine 2\nLine 3'
    };
    
    render(<ChatMessage message={message} />);
    
    expect(screen.getByText('Line 1')).toBeInTheDocument();
    expect(screen.getByText('Line 2')).toBeInTheDocument();
    expect(screen.getByText('Line 3')).toBeInTheDocument();
  });
});