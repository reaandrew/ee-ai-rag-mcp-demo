import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import axios from 'axios';
import ChatPage from './ChatPage';

// Mock scrollIntoView
Element.prototype.scrollIntoView = jest.fn();

// Helper function to render with router
const renderWithRouter = (ui) => {
  return render(
    <BrowserRouter>
      {ui}
    </BrowserRouter>
  );
};

// Mock axios
jest.mock('axios');

describe('ChatPage Component', () => {
  beforeEach(() => {
    // Reset axios mock before each test
    axios.mockReset();
  });
  
  test('renders input fields for API URL and JWT token', () => {
    renderWithRouter(<ChatPage />);
    
    expect(screen.getByLabelText(/API URL/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/JWT Token/i)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Policy Search Assistant/i })).toBeInTheDocument();
  });
  
  test('chat input is disabled when API URL or JWT token is missing', () => {
    renderWithRouter(<ChatPage />);
    
    // Find the chat input (textarea)
    const textarea = screen.getByPlaceholderText(/Type your question about company policies/i);
    expect(textarea).toBeDisabled();
    
    // Find the send button
    const sendButton = screen.getByRole('button', { name: /send/i });
    expect(sendButton).toBeDisabled();
    
    // Add API URL
    const apiUrlInput = screen.getByLabelText(/API URL/i);
    fireEvent.change(apiUrlInput, { target: { value: 'https://api.example.com/search' } });
    
    // Input should still be disabled since JWT token is missing
    expect(textarea).toBeDisabled();
    expect(sendButton).toBeDisabled();
    
    // Add JWT token
    const jwtTokenInput = screen.getByLabelText(/JWT Token/i);
    fireEvent.change(jwtTokenInput, { target: { value: 'test-token' } });
    
    // Now input should be enabled
    expect(textarea).not.toBeDisabled();
    // Button is still disabled because there's no text in the textarea
    expect(sendButton).toBeDisabled();
  });
  
  test('sends message and displays response', async () => {
    const user = userEvent.setup();
    
    // Mock axios response
    axios.mockResolvedValueOnce({
      data: {
        answer: 'This is the answer',
        sources: [{ document_name: 'Test Document', page_number: 1 }]
      }
    });
    
    renderWithRouter(<ChatPage />);
    
    // Fill API URL and JWT token
    const apiUrlInput = screen.getByLabelText(/API URL/i);
    await user.type(apiUrlInput, 'https://api.example.com/search');
    
    const jwtTokenInput = screen.getByLabelText(/JWT Token/i);
    await user.type(jwtTokenInput, 'test-token');
    
    // Type message
    const textarea = screen.getByPlaceholderText(/Type your question about company policies/i);
    await user.type(textarea, 'What is the policy?');
    
    // Click send button
    const sendButton = screen.getByRole('button', { name: /send/i });
    await user.click(sendButton);
    
    // Verify axios was called with correct parameters
    expect(axios).toHaveBeenCalledWith({
      method: 'post',
      url: 'https://api.example.com/search',
      data: { query: 'What is the policy?' },
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer test-token'
      }
    });
    
    // Verify user message and response are displayed
    await waitFor(() => {
      expect(screen.getByText('What is the policy?')).toBeInTheDocument();
      expect(screen.getByText('This is the answer')).toBeInTheDocument();
      expect(screen.getByText('Test Document')).toBeInTheDocument();
    });
  });
  
  test('displays error message when API call fails', async () => {
    const user = userEvent.setup();
    
    // Mock axios error
    axios.mockRejectedValueOnce(new Error('API Error'));
    
    renderWithRouter(<ChatPage />);
    
    // Fill API URL and JWT token
    const apiUrlInput = screen.getByLabelText(/API URL/i);
    await user.type(apiUrlInput, 'https://api.example.com/search');
    
    const jwtTokenInput = screen.getByLabelText(/JWT Token/i);
    await user.type(jwtTokenInput, 'test-token');
    
    // Type message
    const textarea = screen.getByPlaceholderText(/Type your question about company policies/i);
    await user.type(textarea, 'What is the policy?');
    
    // Click send button
    const sendButton = screen.getByRole('button', { name: /send/i });
    await user.click(sendButton);
    
    // Verify error message is displayed
    await waitFor(() => {
      expect(screen.getByText('Error: API Error')).toBeInTheDocument();
    });
  });
});