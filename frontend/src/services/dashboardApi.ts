export type ManualAnalysisSignal = {
  strategy: string;
  signal: string;
  confidence: number;
};

export type ManualAnalysisResponse = {
  symbol: string;
  signals: ManualAnalysisSignal[];
  generated_at: string;
};

export type DashboardStatus = {
  status: 'not-implemented';
};

export async function fetchDashboardStatus(): Promise<DashboardStatus> {
  return Promise.resolve({ status: 'not-implemented' });
}

export async function runManualAnalysis(symbol: string): Promise<ManualAnalysisResponse> {
  const response = await fetch('/analysis/run', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ symbol }),
  });

  if (!response.ok) {
    let errorMessage = 'Analysis request failed.';

    try {
      const errorData = (await response.json()) as { error?: string };
      if (errorData.error) {
        errorMessage = errorData.error;
      }
    } catch {
      // keep default message
    }

    throw new Error(errorMessage);
  }

  return (await response.json()) as ManualAnalysisResponse;
}
