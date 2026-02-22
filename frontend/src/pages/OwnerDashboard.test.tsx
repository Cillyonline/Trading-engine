import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import OwnerDashboard from './OwnerDashboard';

describe('OwnerDashboard', () => {
  it('renders dashboard headline and placeholder copy', () => {
    render(
      <MemoryRouter>
        <OwnerDashboard />
      </MemoryRouter>
    );

    expect(screen.getByRole('heading', { name: 'Owner Dashboard' })).toBeInTheDocument();
    expect(screen.getByText('Manual analysis controls will appear here.')).toBeInTheDocument();
  });
});
