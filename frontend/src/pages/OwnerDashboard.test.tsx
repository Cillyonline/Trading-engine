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

const populatedEvidencePayload = {
  state: 'available',
  run_count: 3,
  run_quality_distribution: {
    degraded: 1,
    healthy: 1,
    no_eligible: 1,
  },
  eligible_skipped_rejected_totals: {
    eligible: 4,
    skipped: 2,
    rejected: 1,
  },
  skip_reason_counts: {
    duplicate_entry: 1,
    score_below_threshold: 1,
  },
  reconciliation: {
    mismatch_total: 2,
    status_counts: {
      fail: 1,
      pass: 2,
    },
  },
  mismatch_counts: {
    '2026-04-08/run-003.json': 2,
  },
  summary_files: [
    '/data/artifacts/daily-runtime/2026-04-06/daily-runtime-summary.json',
    '/data/artifacts/daily-runtime/2026-04-08/daily-runtime-summary.json',
  ],
  message: 'Paper-runtime evidence series summary is available for read-only inspection.',
};

function stubEvidenceFetch(payload: unknown = populatedEvidencePayload) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => payload,
  } as unknown as MockFetchResponse);
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('OwnerDashboard', () => {
  it('renders the runtime analysis entrypoint copy on /ui', async () => {
    stubEvidenceFetch();

    render(
      <MemoryRouter initialEntries={['/ui']}>
        <OwnerDashboard />
      </MemoryRouter>
    );

    expect(screen.getByRole('heading', { name: 'Browser Analysis Entrypoint' })).toBeInTheDocument();
    expect(screen.getByText('/ui')).toBeInTheDocument();
    expect(screen.getByText(/supported runtime analysis flow/i)).toBeInTheDocument();
    expect(screen.getByText(/does not expose owner, broker, or lab workflows/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText('Paper-runtime evidence series summary is available for read-only inspection.')).toBeInTheDocument();
    });
  });

  it('sends the canonical manual analysis request and renders the canonical response', async () => {
    const deferredResponse = createDeferred<MockFetchResponse>();
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      if (String(input) === '/paper/runtime/evidence-series') {
        return Promise.resolve({
          ok: true,
          json: async () => populatedEvidencePayload,
        } as unknown as MockFetchResponse);
      }
      return deferredResponse.promise;
    });
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
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      if (String(input) === '/paper/runtime/evidence-series') {
        return Promise.resolve({
          ok: true,
          json: async () => populatedEvidencePayload,
        } as unknown as MockFetchResponse);
      }
      return Promise.resolve({
        ok: false,
        json: async () => ({ detail: 'Bad request' }),
      } as unknown as MockFetchResponse);
    });
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

  it('renders populated paper-runtime evidence metrics without execution controls', async () => {
    const fetchMock = stubEvidenceFetch();

    render(
      <MemoryRouter>
        <OwnerDashboard />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Paper-runtime evidence series summary is available for read-only inspection.')).toBeInTheDocument();
    });

    expect(fetchMock).toHaveBeenCalledWith('/paper/runtime/evidence-series', {
      headers: {
        'X-Cilly-Role': 'read_only',
      },
    });
    expect(screen.getByRole('heading', { name: 'Paper Runtime Evidence' })).toBeInTheDocument();
    expect(screen.getByText('/paper/runtime/evidence-series')).toBeInTheDocument();
    expect(screen.getByText('available')).toBeInTheDocument();
    expect(screen.getAllByText('3')[0]).toBeInTheDocument();
    expect(screen.getByText('Not available')).toBeInTheDocument();
    expect(screen.getByText('/data/artifacts/daily-runtime/2026-04-08/daily-runtime-summary.json')).toBeInTheDocument();
    expect(screen.getByText('duplicate_entry: 1, score_below_threshold: 1')).toBeInTheDocument();
    expect(screen.getByText('fail: 1, pass: 2')).toBeInTheDocument();
    expect(screen.getByText('2026-04-08/run-003.json: 2')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /paper runtime/i })).not.toBeInTheDocument();
  });

  it('renders empty paper-runtime evidence state clearly', async () => {
    stubEvidenceFetch({
      ...populatedEvidencePayload,
      state: 'empty',
      run_count: 0,
      run_quality_distribution: { degraded: 0, healthy: 0, no_eligible: 0 },
      eligible_skipped_rejected_totals: { eligible: 0, skipped: 0, rejected: 0 },
      skip_reason_counts: {},
      reconciliation: { mismatch_total: 0, status_counts: {} },
      mismatch_counts: {},
      summary_files: [],
      message: 'Configured paper-runtime evidence series directory contains no matching run files.',
    });

    render(
      <MemoryRouter>
        <OwnerDashboard />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Configured paper-runtime evidence series directory contains no matching run files.')).toBeInTheDocument();
    });

    expect(screen.getByText('empty')).toBeInTheDocument();
    expect(screen.getAllByText('Not available')).toHaveLength(2);
    expect(screen.getAllByText('None reported')).toHaveLength(3);
  });
});
