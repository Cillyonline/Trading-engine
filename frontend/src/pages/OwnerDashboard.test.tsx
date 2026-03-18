import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import OwnerDashboard from './OwnerDashboard';

type MockFetchResponse = Pick<Response, 'ok' | 'json' | 'status'>;

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
  it('renders the runtime analysis entrypoint copy on /ui', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ items: [], total: 0 }),
    } as MockFetchResponse);
    vi.stubGlobal('fetch', fetchMock);

    render(
      <MemoryRouter initialEntries={['/ui']}>
        <OwnerDashboard />
      </MemoryRouter>
    );

    expect(screen.getByRole('heading', { name: 'Operator Dashboard' })).toBeInTheDocument();
    expect(screen.getByText('/ui')).toBeInTheDocument();
    expect(screen.getByText(/recent read-only alert history/i)).toBeInTheDocument();
    expect(screen.getByText(/does not expose owner, broker, or lab workflows/i)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Recent Alerts' })).toBeInTheDocument();

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith('/alerts/history', {
        headers: {
          'X-Cilly-Role': 'read_only',
        },
      });
    });
  });

  it('renders recent alerts in deterministic API order', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        items: [
          {
            event_id: 'evt-latest',
            alert_id: 'runtime-critical',
            name: 'Runtime Halted',
            severity: 'critical',
            source: 'runtime',
            triggered_at: '2026-03-16T09:00:00Z',
            summary: 'Runtime entered a blocked state.',
            symbol: null,
            strategy: null,
          },
          {
            event_id: 'evt-older',
            alert_id: 'drawdown-warning',
            name: 'Drawdown Warning',
            severity: 'warning',
            source: 'risk',
            triggered_at: '2026-03-16T08:00:00Z',
            summary: 'Drawdown crossed the warning threshold.',
            symbol: 'BTCUSDT',
            strategy: 'RSI2',
          },
        ],
        total: 2,
      }),
    } as MockFetchResponse);
    vi.stubGlobal('fetch', fetchMock);

    render(
      <MemoryRouter>
        <OwnerDashboard />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Loaded 2 recent alerts from /alerts/history.')).toBeInTheDocument();
    });

    const rows = screen.getAllByRole('row');
    expect(rows[1]).toHaveTextContent('2026-03-16T09:00:00Z');
    expect(rows[1]).toHaveTextContent('Runtime Halted');
    expect(rows[2]).toHaveTextContent('2026-03-16T08:00:00Z');
    expect(rows[2]).toHaveTextContent('Drawdown Warning');
    expect(screen.getByRole('cell', { name: 'critical' })).toBeInTheDocument();
    expect(screen.getByRole('cell', { name: 'BTCUSDT' })).toBeInTheDocument();
  });

  it('renders deterministic empty and error states for alert history', async () => {
    const emptyFetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ items: [], total: 0 }),
    } as MockFetchResponse);
    vi.stubGlobal('fetch', emptyFetchMock);

    const { unmount } = render(
      <MemoryRouter>
        <OwnerDashboard />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('No recent alerts returned by /alerts/history.')).toBeInTheDocument();
    });
    expect(
      screen.getByText('No recent alerts available for this dashboard session.')
    ).toBeInTheDocument();

    unmount();

    const errorFetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({ detail: 'service unavailable' }),
    } as MockFetchResponse);
    vi.stubGlobal('fetch', errorFetchMock);

    render(
      <MemoryRouter>
        <OwnerDashboard />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Alert history unavailable.')).toBeInTheDocument();
    });
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Alert history request failed with HTTP 503.'
    );
  });

  it('sends the canonical manual analysis request and renders the canonical response', async () => {
    const deferredResponse = createDeferred<MockFetchResponse>();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ items: [], total: 0 }),
      } as MockFetchResponse)
      .mockReturnValueOnce(deferredResponse.promise);
    vi.stubGlobal('fetch', fetchMock);

    render(
      <MemoryRouter>
        <OwnerDashboard />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith('/alerts/history', {
        headers: {
          'X-Cilly-Role': 'read_only',
        },
      });
    });

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

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock).toHaveBeenLastCalledWith('/analysis/run', {
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
      status: 200,
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
    } as MockFetchResponse);

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
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ items: [], total: 0 }),
      } as MockFetchResponse)
      .mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ detail: 'Bad request' }),
      } as MockFetchResponse);
    vi.stubGlobal('fetch', fetchMock);

    render(
      <MemoryRouter>
        <OwnerDashboard />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(1);
    });

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
