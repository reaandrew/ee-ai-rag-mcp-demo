import { render, screen } from '@testing-library/react';
import Footer from './Footer';

describe('Footer Component', () => {
  test('renders footer with correct content', () => {
    render(<Footer />);
    
    expect(screen.getByText('RAG Policy Search Demo Application')).toBeInTheDocument();
    expect(screen.getByRole('contentinfo')).toHaveClass('govuk-footer');
  });
});