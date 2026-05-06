import { FormEvent, useEffect, useState } from 'react';
import {
  ManualAnalysisResponse,
  PaperRuntimeEvidenceSeriesResponse,
  fetchPaperRuntimeEvidenceSeries,
  runManualAnalysis,
} from '../services/dashboardApi';

type AnalysisSignal = {
  symbol?: string;
  strategy: string;
  direction?: string;
  score?: number;
  timestamp?: string;
  stage?: string;
};

type AnalysisResult = {
  analysis_run_id: string;
  ingestion_run_id: string;
  symbol: string;
  strategy: string;
  signals: AnalysisSignal[];
};

const paperRuntimeQualityLabels = ['healthy', 'no_eligible', 'degraded'];

function formatCounts(counts: Record<string, number>): string {
  const entries = Object.entries(counts).sort(([left], [right]) => left.localeCompare(right));
  if (entries.length === 0) {
    return 'None reported';
  }
  return entries.map(([key, value]) => `${key}: ${value}`).join(', ');
}

function formatTargetCount(payload: PaperRuntimeEvidenceSeriesResponse): string {
  return typeof payload.target_count === 'number'
    ? String(payload.target_count)
    : 'Not available';
}

function OwnerDashboard() {
  const [ingestionRunId, setIngestionRunId] = useState('');
  const [symbol, setSymbol] = useState('BTCUSDT');
  const [strategy, setStrategy] = useState('RSI2');
  const [marketType, setMarketType] = useState<'stock' | 'crypto'>('crypto');
  const [lookbackDays, setLookbackDays] = useState('200');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [evidenceSeries, setEvidenceSeries] = useState<PaperRuntimeEvidenceSeriesResponse | null>(null);
  const [evidenceLoading, setEvidenceLoading] = useState(true);
  const [evidenceError, setEvidenceError] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;

    async function loadEvidenceSeries() {
      setEvidenceLoading(true);
      setEvidenceError(null);

      try {
        const payload = await fetchPaperRuntimeEvidenceSeries();
        if (isActive) {
          setEvidenceSeries(payload);
        }
      } catch (requestError) {
        if (isActive) {
          const errorMessage =
            requestError instanceof Error ? requestError.message : 'Evidence series request failed.';
          setEvidenceError(errorMessage);
          setEvidenceSeries(null);
        }
      } finally {
        if (isActive) {
          setEvidenceLoading(false);
        }
      }
    }

    void loadEvidenceSeries();

    return () => {
      isActive = false;
    };
  }, []);

  async function handleRunAnalysis(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmedIngestionRunId = ingestionRunId.trim();
    const trimmedSymbol = symbol.trim();
    const trimmedStrategy = strategy.trim();
    const parsedLookbackDays = Number.parseInt(lookbackDays, 10);

    if (!trimmedIngestionRunId) {
      setError('Ingestion Run ID is required.');
      setResult(null);
      return;
    }

    if (!trimmedSymbol) {
      setError('Symbol is required.');
      setResult(null);
      return;
    }

    if (!trimmedStrategy) {
      setError('Strategy is required.');
      setResult(null);
      return;
    }

    if (Number.isNaN(parsedLookbackDays) || parsedLookbackDays < 30 || parsedLookbackDays > 1000) {
      setError('Lookback Days must be between 30 and 1000.');
      setResult(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const analysisResult: ManualAnalysisResponse = await runManualAnalysis({
        ingestion_run_id: trimmedIngestionRunId,
        symbol: trimmedSymbol,
        strategy: trimmedStrategy,
        market_type: marketType,
        lookback_days: parsedLookbackDays,
      });
      setResult(analysisResult);
    } catch (requestError) {
      const errorMessage = requestError instanceof Error ? requestError.message : 'Analysis request failed.';
      setError(errorMessage);
      setResult(null);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="runtime-entry-layout">
      <section className="runtime-entry-hero">
        <div>
          <p className="eyebrow">Phase 36 Runtime UI</p>
          <h1>Browser Analysis Entrypoint</h1>
          <p className="hero-copy">
            Use <code>/ui</code> to launch the supported runtime analysis flow, review the selected
            input set, and inspect the returned signal package.
          </p>
        </div>
        <nav className="runtime-entry-nav" aria-label="Runtime entry navigation">
          <a href="#run-analysis">Start Analysis</a>
          <a href="#entry-flow">Entry Flow</a>
          <a href="#paper-runtime-evidence">Paper Runtime Evidence</a>
          <a href="#analysis-results">Results</a>
        </nav>
      </section>

      <section id="entry-flow" className="runtime-card-grid" aria-label="runtime-entry-flow">
        <article className="runtime-card">
          <h2>Primary workflow</h2>
          <p>Provide an ingestion run, market, symbol, strategy, and lookback window.</p>
        </article>
        <article className="runtime-card">
          <h2>Runtime-only scope</h2>
          <p>This surface is limited to browser analysis. It does not expose owner, broker, or lab workflows.</p>
        </article>
        <article className="runtime-card">
          <h2>Expected outcome</h2>
          <p>Each run returns the canonical analysis run id together with any signals emitted for the request.</p>
        </article>
      </section>

      <section id="run-analysis" className="runtime-card" aria-label="manual-analysis-controls">
        <div className="section-heading">
          <h2>Run Analysis</h2>
          <p>Submit the supported browser analysis request directly from the runtime entrypoint.</p>
        </div>
        <form className="runtime-analysis-form" onSubmit={handleRunAnalysis}>
          <label htmlFor="manual-analysis-ingestion-run-id">Ingestion Run ID</label>
          <input
            id="manual-analysis-ingestion-run-id"
            name="manual-analysis-ingestion-run-id"
            type="text"
            value={ingestionRunId}
            onChange={(event) => setIngestionRunId(event.target.value)}
          />
          <label htmlFor="manual-analysis-symbol">Symbol</label>
          <input
            id="manual-analysis-symbol"
            name="manual-analysis-symbol"
            type="text"
            value={symbol}
            onChange={(event) => setSymbol(event.target.value)}
          />
          <label htmlFor="manual-analysis-strategy">Strategy</label>
          <input
            id="manual-analysis-strategy"
            name="manual-analysis-strategy"
            type="text"
            value={strategy}
            onChange={(event) => setStrategy(event.target.value)}
          />
          <label htmlFor="manual-analysis-market-type">Market Type</label>
          <select
            id="manual-analysis-market-type"
            name="manual-analysis-market-type"
            value={marketType}
            onChange={(event) => {
              const value = event.target.value;
              if (value === 'stock' || value === 'crypto') setMarketType(value);
            }}
          >
            <option value="crypto">crypto</option>
            <option value="stock">stock</option>
          </select>
          <label htmlFor="manual-analysis-lookback-days">Lookback Days</label>
          <input
            id="manual-analysis-lookback-days"
            name="manual-analysis-lookback-days"
            type="number"
            min={30}
            max={1000}
            value={lookbackDays}
            onChange={(event) => setLookbackDays(event.target.value)}
          />
          <button type="submit" disabled={isLoading}>
            Run Analysis
          </button>
          {isLoading ? <p className="form-status">Loading...</p> : null}
        </form>
      </section>

      <section
        id="paper-runtime-evidence"
        className="runtime-card"
        aria-label="paper-runtime-evidence-series"
      >
        <div className="section-heading">
          <h2>Paper Runtime Evidence</h2>
          <p>
            Read-only bounded paper-runtime evidence series inspection from{' '}
            <code>/paper/runtime/evidence-series</code>. This panel does not trigger runs.
          </p>
        </div>
        {evidenceLoading ? <p className="form-status">Loading paper-runtime evidence...</p> : null}
        {evidenceError ? <p role="alert" className="runtime-alert">{evidenceError}</p> : null}
        {!evidenceLoading && !evidenceError && evidenceSeries ? (
          <>
            <p className="empty-state">{evidenceSeries.message}</p>
            <dl className="result-summary">
              <div>
                <dt>State</dt>
                <dd>{evidenceSeries.state}</dd>
              </div>
              <div>
                <dt>Run Count</dt>
                <dd>{evidenceSeries.run_count}</dd>
              </div>
              <div>
                <dt>Target Count</dt>
                <dd>{formatTargetCount(evidenceSeries)}</dd>
              </div>
              <div>
                <dt>Latest Summary File</dt>
                <dd>
                  {evidenceSeries.summary_files.length > 0
                    ? evidenceSeries.summary_files[evidenceSeries.summary_files.length - 1]
                    : 'Not available'}
                </dd>
              </div>
            </dl>
            <dl className="result-summary">
              {paperRuntimeQualityLabels.map((quality) => (
                <div key={quality}>
                  <dt>{quality}</dt>
                  <dd>{evidenceSeries.run_quality_distribution[quality] ?? 0}</dd>
                </div>
              ))}
              <div>
                <dt>Eligible</dt>
                <dd>{evidenceSeries.eligible_skipped_rejected_totals.eligible}</dd>
              </div>
              <div>
                <dt>Skipped</dt>
                <dd>{evidenceSeries.eligible_skipped_rejected_totals.skipped}</dd>
              </div>
              <div>
                <dt>Rejected</dt>
                <dd>{evidenceSeries.eligible_skipped_rejected_totals.rejected}</dd>
              </div>
              <div>
                <dt>Mismatch Total</dt>
                <dd>{evidenceSeries.reconciliation.mismatch_total}</dd>
              </div>
            </dl>
            <div className="table-wrap">
              <table aria-label="Paper runtime evidence counts">
                <thead>
                  <tr>
                    <th>Metric</th>
                    <th>Counts</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>Skip Reasons</td>
                    <td>{formatCounts(evidenceSeries.skip_reason_counts)}</td>
                  </tr>
                  <tr>
                    <td>Reconciliation Status</td>
                    <td>{formatCounts(evidenceSeries.reconciliation.status_counts)}</td>
                  </tr>
                  <tr>
                    <td>Mismatch Counts</td>
                    <td>{formatCounts(evidenceSeries.mismatch_counts)}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </>
        ) : null}
        {!evidenceLoading && !evidenceError && !evidenceSeries ? (
          <p className="empty-state">Paper-runtime evidence is not configured for this browser session.</p>
        ) : null}
      </section>

      {error ? <p role="alert" className="runtime-alert">{error}</p> : null}

      <section id="analysis-results" className="runtime-card" aria-label="manual-analysis-results">
        <div className="section-heading">
          <h2>Analysis Results</h2>
          <p>Review the canonical response returned by the runtime analysis endpoint.</p>
        </div>
        {result ? (
          <>
            <dl className="result-summary">
              <div>
                <dt>Analysis Run ID</dt>
                <dd>{result.analysis_run_id}</dd>
              </div>
              <div>
                <dt>Ingestion Run ID</dt>
                <dd>{result.ingestion_run_id}</dd>
              </div>
              <div>
                <dt>Symbol</dt>
                <dd>{result.symbol}</dd>
              </div>
              <div>
                <dt>Strategy</dt>
                <dd>{result.strategy}</dd>
              </div>
            </dl>
            {result.signals.length === 0 ? (
              <p>No signals returned.</p>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Symbol</th>
                      <th>Strategy</th>
                      <th>Direction</th>
                      <th>Stage</th>
                      <th>Score</th>
                      <th>Timestamp</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.signals.map((signal, index) => (
                      <tr key={`${signal.strategy}-${signal.timestamp ?? index}-${index}`}>
                        <td>{signal.symbol ?? result.symbol}</td>
                        <td>{signal.strategy}</td>
                        <td>{signal.direction ?? '-'}</td>
                        <td>{signal.stage ?? '-'}</td>
                        <td>{typeof signal.score === 'number' ? signal.score.toFixed(2) : '-'}</td>
                        <td>{signal.timestamp ?? '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        ) : (
          <p className="empty-state">No analysis has been run yet from this browser session.</p>
        )}
      </section>
    </main>
  );
}

export default OwnerDashboard;
