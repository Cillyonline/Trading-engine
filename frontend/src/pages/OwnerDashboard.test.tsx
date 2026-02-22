import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import OwnerDashboard from './OwnerDashboard';

type MockFetchResponse = Pick<Response, 'ok' | 'json'>;

type Deferred<T> = {
  promise: Promise<T>;
  resolve: (value: T) => void;
  reject: (reason?: unknown) => void;
};

function createDeferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;

  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });

  return { promise, resolve, reject };
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('OwnerDashboard', () => {
  it('sends manual analysis request and renders results', async () => {
    const deferredResponse = createDeferred<MockFetchResponse>();
    const fetchMock = vi.fn().mockReturnValue(deferredResponse.promise);
    vi.stubGlobal('fetch', fetchMock);

    render(
      <MemoryRouter>
        <OwnerDashboard />
      </MemoryRouter>
    );

    const symbolInput = screen.getByLabelText('Symbol');
    const runButton = screen.getByRole('button', { name: 'Run Analysis' });

    fireEvent.change(symbolInput, { target: { value: 'ETHUSDT' } });
    fireEvent.click(runButton);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith('/analysis/run', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ symbol: 'ETHUSDT' }),
    });
    expect(runButton).toBeDisabled();
    expect(screen.getByText('Loading...')).toBeInTheDocument();

    deferredResponse.resolve({
      ok: true,
      json: async () => ({
        symbol: 'ETHUSDT',
        generated_at: '2026-01-01T00:00:00Z',
        signals: [{ strategy: 'ema_cross', signal: 'BUY', confidence: 0.87 }],
      }),
    } as unknown as MockFetchResponse);

    await waitFor(() => {
      expect(screen.getByText('Generated At: 2026-01-01T00:00:00Z')).toBeInTheDocument();
    });

    expect(screen.getByText('ema_cross')).toBeInTheDocument();
    expect(screen.getByText('BUY')).toBeInTheDocument();
    expect(screen.getByText('0.87')).toBeInTheDocument();
    expect(runButton).not.toBeDisabled();
  });

  it('renders API error and re-enables button', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      json: async () => ({ error: 'Bad request' }),
    } as unknown as MockFetchResponse);
    vi.stubGlobal('fetch', fetchMock);

    render(
      <MemoryRouter>
        <OwnerDashboard />
      </MemoryRouter>
    );

    const runButton = screen.getByRole('button', { name: 'Run Analysis' });
    fireEvent.click(runButton);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Bad request');
    });

    expect(runButton).not.toBeDisabled();
  });
});
