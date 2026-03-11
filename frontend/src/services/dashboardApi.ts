export type ManualAnalysisSignal = {
  symbol?: string;
  strategy: string;
  direction?: string;
  score?: number;
  timestamp?: string;
  stage?: string;
};

export type ManualAnalysisRequest = {
  ingestion_run_id: string;
  symbol: string;
  strategy: string;
  market_type: 'stock' | 'crypto';
  lookback_days: number;
};

export type ManualAnalysisResponse = {
  analysis_run_id: string;
  ingestion_run_id: string;
  symbol: string;
  strategy: string;
  signals: ManualAnalysisSignal[];
};

export type DashboardStatus = {
  status: 'not-implemented';
};

export async function fetchDashboardStatus(): Promise<DashboardStatus> {
  return Promise.resolve({ status: 'not-implemented' });
}

export async function runManualAnalysis(
  request: ManualAnalysisRequest
): Promise<ManualAnalysisResponse> {
  const response = await fetch('/analysis/run', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    let errorMessage = 'Analysis request failed.';

    try {
      const errorData = (await response.json()) as { detail?: string; error?: string };
      if (errorData.detail) {
        errorMessage = errorData.detail;
      } else if (errorData.error) {
        errorMessage = errorData.error;
      }
    } catch {
      // keep default message
    }

    throw new Error(errorMessage);
  }

  return (await response.json()) as ManualAnalysisResponse;
}
