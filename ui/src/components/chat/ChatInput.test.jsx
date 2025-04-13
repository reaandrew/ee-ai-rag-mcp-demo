import { render, screen, fireEvent } from '@testing-library/react';
import ChatInput from './ChatInput';

describe('ChatInput Component', () => {
  const mockSendMessage = jest.fn();
  
  beforeEach(() => {
    mockSendMessage.mockClear();
  });
  
  test('renders input field and send button', () => {
    render(<ChatInput onSendMessage={mockSendMessage} isLoading={false} />);
    
    expect(screen.getByPlaceholderText('Type your question about company policies...')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Send' })).toBeInTheDocument();
  });
  
  test('button is disabled when input is empty', () => {
    render(<ChatInput onSendMessage={mockSendMessage} isLoading={false} />);
    
    const button = screen.getByRole('button', { name: 'Send' });
    expect(button).toBeDisabled();
  });
  
  test('button is enabled when input has text', () => {
    render(<ChatInput onSendMessage={mockSendMessage} isLoading={false} />);
    
    const input = screen.getByPlaceholderText('Type your question about company policies...');
    fireEvent.change(input, { target: { value: 'What is our password policy?' } });
    
    const button = screen.getByRole('button', { name: 'Send' });
    expect(button).not.toBeDisabled();
  });
  
  test('calls onSendMessage when form is submitted', () => {
    render(<ChatInput onSendMessage={mockSendMessage} isLoading={false} />);
    
    const input = screen.getByPlaceholderText('Type your question about company policies...');
    fireEvent.change(input, { target: { value: 'What is our password policy?' } });
    
    const button = screen.getByRole('button', { name: 'Send' });
    fireEvent.click(button);
    
    expect(mockSendMessage).toHaveBeenCalledWith('What is our password policy?');
    expect(input.value).toBe('');
  });
  
  test('does not call onSendMessage when form is submitted with empty input', () => {
    render(<ChatInput onSendMessage={mockSendMessage} isLoading={false} />);
    
    const button = screen.getByRole('button', { name: 'Send' });
    fireEvent.click(button);
    
    expect(mockSendMessage).not.toHaveBeenCalled();
  });
  
  test('disables input and button when isLoading is true', () => {
    render(<ChatInput onSendMessage={mockSendMessage} isLoading={true} />);
    
    const input = screen.getByPlaceholderText('Type your question about company policies...');
    const button = screen.getByRole('button', { name: 'Sending...' });
    
    expect(input).toBeDisabled();
    expect(button).toBeDisabled();
  });
});