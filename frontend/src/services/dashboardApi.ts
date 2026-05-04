import { z } from 'zod';

const ManualAnalysisSignalSchema = z.object({
  symbol: z.string().optional(),
  strategy: z.string(),
  direction: z.string().optional(),
  score: z.number().optional(),
  timestamp: z.string().optional(),
  stage: z.string().optional(),
});

export type ManualAnalysisSignal = z.infer<typeof ManualAnalysisSignalSchema>;

const ManualAnalysisRequestSchema = z.object({
  ingestion_run_id: z.string(),
  symbol: z.string(),
  strategy: z.string(),
  market_type: z.enum(['stock', 'crypto']),
  lookback_days: z.number(),
});

export type ManualAnalysisRequest = z.infer<typeof ManualAnalysisRequestSchema>;

const ManualAnalysisResponseSchema = z.object({
  analysis_run_id: z.string(),
  ingestion_run_id: z.string(),
  symbol: z.string(),
  strategy: z.string(),
  signals: z.array(ManualAnalysisSignalSchema),
});

export type ManualAnalysisResponse = z.infer<typeof ManualAnalysisResponseSchema>;

export type DashboardStatus = {
  status: 'not-implemented';
};

const PaperRuntimeEvidenceSeriesResponseSchema = z.object({
  state: z.enum(['not_configured', 'missing', 'empty', 'available']),
  run_count: z.number(),
  run_quality_distribution: z.record(z.string(), z.number()),
  eligible_skipped_rejected_totals: z.object({
    eligible: z.number(),
    skipped: z.number(),
    rejected: z.number(),
  }),
  skip_reason_counts: z.record(z.string(), z.number()),
  reconciliation: z.object({
    mismatch_total: z.number(),
    status_counts: z.record(z.string(), z.number()),
  }),
  mismatch_counts: z.record(z.string(), z.number()),
  summary_files: z.array(z.string()),
  message: z.string(),
  target_count: z.number().optional(),
});

export type PaperRuntimeEvidenceSeriesResponse = z.infer<
  typeof PaperRuntimeEvidenceSeriesResponseSchema
>;

const ErrorResponseSchema = z.object({
  detail: z.string().optional(),
  error: z.string().optional(),
});

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

  return PaperRuntimeEvidenceSeriesResponseSchema.parse(await response.json());
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
      const result = ErrorResponseSchema.safeParse(await response.json());
      if (result.success) {
        errorMessage = result.data.detail ?? result.data.error ?? errorMessage;
      }
    } catch {
      // keep default message
    }

    throw new Error(errorMessage);
  }

  return ManualAnalysisResponseSchema.parse(await response.json());
}
