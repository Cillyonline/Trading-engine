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
  it('renders the runtime analysis entrypoint copy on /ui', () => {
    render(
      <MemoryRouter initialEntries={['/ui']}>
        <OwnerDashboard />
      </MemoryRouter>
    );

    expect(screen.getByRole('heading', { name: 'Browser Analysis Entrypoint' })).toBeInTheDocument();
    expect(screen.getByText('/ui')).toBeInTheDocument();
    expect(screen.getByText(/supported runtime analysis flow/i)).toBeInTheDocument();
    expect(screen.getByText(/does not expose owner, broker, or lab workflows/i)).toBeInTheDocument();
  });

  it('sends the canonical manual analysis request and renders the canonical response', async () => {
    const deferredResponse = createDeferred<MockFetchResponse>();
    const fetchMock = vi.fn().mockReturnValue(deferredResponse.promise);
    vi.stubGlobal('fetch', fetchMock);

    render(
      <MemoryRouter>
        <OwnerDashboard />
      </MemoryRouter>
    );

    const ingestionRunIdInput = screen.getByLabelText('Ingestion Run ID');
    const symbolInput = screen.getByLabelText('Symbol');
    const strategyInput = screen.getByLabelText('Strategy');
    const marketTypeInput = screen.getByLabelText('Market Type');
    const lookbackDaysInput = screen.getByLabelText('Lookback Days');
    const runButton = screen.getByRole('button', { name: 'Run Analysis' });

    fireEvent.change(ingestionRunIdInput, { target: { value: 'dbfb3ea6-cef8-49f3-acdb-df0de7115d6f' } });
    fireEvent.change(symbolInput, { target: { value: 'ETHUSDT' } });
    fireEvent.change(strategyInput, { target: { value: 'RSI2' } });
    fireEvent.change(marketTypeInput, { target: { value: 'crypto' } });
    fireEvent.change(lookbackDaysInput, { target: { value: '365' } });
    fireEvent.click(runButton);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith('/analysis/run', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        ingestion_run_id: 'dbfb3ea6-cef8-49f3-acdb-df0de7115d6f',
        symbol: 'ETHUSDT',
        strategy: 'RSI2',
        market_type: 'crypto',
        lookback_days: 365,
      }),
    });
    expect(runButton).toBeDisabled();
    expect(screen.getByText('Loading...')).toBeInTheDocument();

    deferredResponse.resolve({
      ok: true,
      json: async () => ({
        analysis_run_id: '3c8bc4c7e0f16ee05cf5c23d7be8b3f5',
        ingestion_run_id: 'dbfb3ea6-cef8-49f3-acdb-df0de7115d6f',
        symbol: 'ETHUSDT',
        strategy: 'RSI2',
        signals: [
          {
            symbol: 'ETHUSDT',
            strategy: 'RSI2',
            direction: 'long',
            stage: 'setup',
            score: 0.87,
            timestamp: '2026-01-01T00:00:00Z',
          },
        ],
      }),
    } as unknown as MockFetchResponse);

    await waitFor(() => {
      expect(screen.getByText('3c8bc4c7e0f16ee05cf5c23d7be8b3f5')).toBeInTheDocument();
    });

    expect(screen.getByText('dbfb3ea6-cef8-49f3-acdb-df0de7115d6f')).toBeInTheDocument();
    expect(screen.getAllByText('ETHUSDT')[0]).toBeInTheDocument();
    expect(screen.getAllByText('RSI2')[0]).toBeInTheDocument();
    expect(screen.getByRole('cell', { name: 'ETHUSDT' })).toBeInTheDocument();
    expect(screen.getByRole('cell', { name: 'RSI2' })).toBeInTheDocument();
    expect(screen.getByText('long')).toBeInTheDocument();
    expect(screen.getByText('setup')).toBeInTheDocument();
    expect(screen.getByText('0.87')).toBeInTheDocument();
    expect(screen.getByText('2026-01-01T00:00:00Z')).toBeInTheDocument();
    expect(screen.queryByText(/Generated At:/)).not.toBeInTheDocument();
    expect(screen.queryByRole('columnheader', { name: 'Confidence' })).not.toBeInTheDocument();
    expect(runButton).not.toBeDisabled();
  });

  it('renders API detail errors and re-enables button', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      json: async () => ({ detail: 'Bad request' }),
    } as unknown as MockFetchResponse);
    vi.stubGlobal('fetch', fetchMock);

    render(
      <MemoryRouter>
        <OwnerDashboard />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByLabelText('Ingestion Run ID'), {
      target: { value: 'dbfb3ea6-cef8-49f3-acdb-df0de7115d6f' },
    });

    const runButton = screen.getByRole('button', { name: 'Run Analysis' });
    fireEvent.click(runButton);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Bad request');
    });

    expect(runButton).not.toBeDisabled();
  });
});
