import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Header from './Header';

describe('Header Component', () => {
  test('renders header with correct title', () => {
    render(
      <BrowserRouter>
        <Header />
      </BrowserRouter>
    );
    
    expect(screen.getByText('Policy Search')).toBeInTheDocument();
    expect(screen.getByText('RAG Policy Assistant')).toBeInTheDocument();
    expect(screen.getByRole('banner')).toHaveClass('govuk-header');
  });
});