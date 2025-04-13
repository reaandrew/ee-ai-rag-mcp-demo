import { render, screen } from '@testing-library/react';
import ChatHistory from './ChatHistory';

// Mock scrollIntoView
Element.prototype.scrollIntoView = jest.fn();

describe('ChatHistory Component', () => {
  test('renders empty state correctly', () => {
    render(<ChatHistory messages={[]} isLoading={false} />);
    
    expect(screen.getByText('Welcome to the Policy Search Assistant!')).toBeInTheDocument();
    expect(screen.getByText('Enter your API details above, then ask any question about company policies.')).toBeInTheDocument();
  });

  test('renders messages correctly', () => {
    const messages = [
      { role: 'user', content: 'What is the password policy?' },
      { role: 'assistant', content: 'Passwords must be changed every 90 days.' }
    ];
    
    render(<ChatHistory messages={messages} isLoading={false} />);
    
    expect(screen.getByText('What is the password policy?')).toBeInTheDocument();
    expect(screen.getByText('Passwords must be changed every 90 days.')).toBeInTheDocument();
    expect(screen.queryByText('Welcome to the Policy Search Assistant!')).not.toBeInTheDocument();
  });

  test('renders loading indicator when isLoading is true', () => {
    render(<ChatHistory messages={[]} isLoading={true} />);
    
    // Check for the loading indicator container
    const loadingIndicator = document.querySelector('.chat-message__typing-indicator');
    expect(loadingIndicator).toBeInTheDocument();
  });
});