import { FormEvent, useState } from 'react';
import { runManualAnalysis } from '../services/dashboardApi';

type AnalysisSignal = {
  strategy: string;
  signal: string;
  confidence: number;
};

type AnalysisResult = {
  symbol: string;
  generated_at: string;
  signals: AnalysisSignal[];
};

function OwnerDashboard() {
  const [symbol, setSymbol] = useState('BTCUSDT');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);

  async function handleRunAnalysis(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmedSymbol = symbol.trim();
    if (!trimmedSymbol) {
      setError('Symbol is required.');
      setResult(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const analysisResult = await runManualAnalysis(trimmedSymbol);
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
    <main className="dashboard-layout">
      <h1>Owner Dashboard</h1>

      <section aria-label="manual-analysis-controls">
        <h2>Manual Analysis</h2>
        <form onSubmit={handleRunAnalysis}>
          <label htmlFor="manual-analysis-symbol">Symbol</label>
          <input
            id="manual-analysis-symbol"
            name="manual-analysis-symbol"
            type="text"
            value={symbol}
            onChange={(event) => setSymbol(event.target.value)}
          />
          <button type="submit" disabled={isLoading}>
            Run Analysis
          </button>
          {isLoading ? <p>Loading...</p> : null}
        </form>
      </section>

      {error ? <p role="alert">{error}</p> : null}

      {result ? (
        <section aria-label="manual-analysis-results">
          <h2>Analysis Results</h2>
          <p>Symbol: {result.symbol}</p>
          <p>Generated At: {result.generated_at}</p>
          {result.signals.length === 0 ? (
            <p>No signals returned.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Strategy</th>
                  <th>Signal</th>
                  <th>Confidence</th>
                </tr>
              </thead>
              <tbody>
                {result.signals.map((signal, index) => (
                  <tr key={`${signal.strategy}-${signal.signal}-${index}`}>
                    <td>{signal.strategy}</td>
                    <td>{signal.signal}</td>
                    <td>{signal.confidence.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      ) : null}
    </main>
  );
}

export default OwnerDashboard;
