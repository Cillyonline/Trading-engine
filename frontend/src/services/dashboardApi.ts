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

export type PaperRuntimeEvidenceSeriesResponse = {
  state: 'not_configured' | 'missing' | 'empty' | 'available';
  run_count: number;
  run_quality_distribution: Record<string, number>;
  eligible_skipped_rejected_totals: {
    eligible: number;
    skipped: number;
    rejected: number;
  };
  skip_reason_counts: Record<string, number>;
  reconciliation: {
    mismatch_total: number;
    status_counts: Record<string, number>;
  };
  mismatch_counts: Record<string, number>;
  summary_files: string[];
  message: string;
};

export async function fetchDashboardStatus(): Promise<DashboardStatus> {
  return Promise.resolve({ status: 'not-implemented' });
}

export async function fetchPaperRuntimeEvidenceSeries(): Promise<PaperRuntimeEvidenceSeriesResponse> {
  const response = await fetch('/paper/runtime/evidence-series', {
    headers: {
      'X-Cilly-Role': 'read_only',
    },
  });

  if (!response.ok) {
    throw new Error(`Evidence series request failed with HTTP ${response.status}.`);
  }

  return (await response.json()) as PaperRuntimeEvidenceSeriesResponse;
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
