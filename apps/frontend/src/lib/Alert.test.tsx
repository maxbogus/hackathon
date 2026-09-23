/**
 * T-129: RED phase — tests for the tiny homegrown <Alert> component.
 *
 * We avoid pulling in @mui/material just for one component. <Alert> here is
 * a pure visual shim with three severity levels (success | warning | info)
 * and a configurable emoji icon.
 */

import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';

import { Alert } from './Alert';

describe('<Alert>', () => {
  it('renders the children text inside the banner', () => {
    render(<Alert severity="success">Садитесь — будет комфортно</Alert>);
    expect(screen.getByText(/садитесь/i)).toBeInTheDocument();
  });

  it('renders the emoji prefix when an icon prop is provided', () => {
    render(
      <Alert severity="success" icon="✅">
        Садитесь
      </Alert>,
    );
    // The emoji is in the document; using toBeInTheDocument is more robust
    // than relying on a particular DOM structure.
    expect(screen.getByText('✅')).toBeInTheDocument();
  });

  it('applies a role="status" attribute for accessibility', () => {
    render(<Alert severity="info">Нет данных</Alert>);
    const alert = screen.getByRole('status');
    expect(alert.textContent).toMatch(/нет данных/i);
  });
});
