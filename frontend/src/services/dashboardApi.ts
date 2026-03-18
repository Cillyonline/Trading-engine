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

export type AlertHistoryItem = {
  event_id: string;
  alert_id: string;
  name: string;
  severity: 'info' | 'warning' | 'critical';
  source: string;
  triggered_at: string;
  summary: string;
  symbol?: string | null;
  strategy?: string | null;
};

export type AlertHistoryResponse = {
  items: AlertHistoryItem[];
  total: number;
};

export type DashboardStatus = {
  status: 'not-implemented';
};

export async function fetchDashboardStatus(): Promise<DashboardStatus> {
  return Promise.resolve({ status: 'not-implemented' });
}

function isAlertHistoryItem(value: unknown): value is AlertHistoryItem {
  if (!value || typeof value !== 'object') {
    return false;
  }

  const item = value as Record<string, unknown>;
  const severity = item.severity;

  return (
    typeof item.event_id === 'string' &&
    typeof item.alert_id === 'string' &&
    typeof item.name === 'string' &&
    (severity === 'info' || severity === 'warning' || severity === 'critical') &&
    typeof item.source === 'string' &&
    typeof item.triggered_at === 'string' &&
    typeof item.summary === 'string' &&
    (item.symbol == null || typeof item.symbol === 'string') &&
    (item.strategy == null || typeof item.strategy === 'string')
  );
}

export async function fetchAlertHistory(): Promise<AlertHistoryResponse> {
  const response = await fetch('/alerts/history', {
    headers: {
      'X-Cilly-Role': 'read_only',
    },
  });

  if (!response.ok) {
    throw new Error(`Alert history request failed with HTTP ${response.status}.`);
  }

  const payload = (await response.json()) as {
    items?: unknown;
    total?: unknown;
  };

  if (!Array.isArray(payload.items) || typeof payload.total !== 'number') {
    throw new Error('Alert history response is invalid.');
  }

  if (!payload.items.every(isAlertHistoryItem)) {
    throw new Error('Alert history response is invalid.');
  }

  return {
    items: payload.items,
    total: payload.total,
  };
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
