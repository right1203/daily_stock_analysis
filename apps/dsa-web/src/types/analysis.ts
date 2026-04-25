/**
 * Stock analysis type definitions
 * Aligned with API spec (api_spec.json)
 */

// ============ Request types ============

export interface AnalysisRequest {
  stockCode: string;
  reportType?: 'simple' | 'detailed';
  forceRefresh?: boolean;
  asyncMode?: boolean;
}

// ============ Report types ============

/** Report metadata */
export interface ReportMeta {
  id?: number;  // Analysis history record primary key ID, present for history reports
  queryId: string;
  stockCode: string;
  stockName: string;
  reportType: 'simple' | 'detailed';
  createdAt: string;
  currentPrice?: number;
  changePct?: number;
  modelUsed?: string;  // LLM model used for analysis (Issue #528)
}

/** Sentiment label */
export type SentimentLabel = '매우 부정' | '부정' | '중립' | '긍정' | '매우 긍정';

/** Report overview section */
export interface ReportSummary {
  analysisSummary: string;
  operationAdvice: string;
  trendPrediction: string;
  sentimentScore: number;
  sentimentLabel?: SentimentLabel;
}

/** Strategy price levels section */
export interface ReportStrategy {
  idealBuy?: string;
  secondaryBuy?: string;
  stopLoss?: string;
  takeProfit?: string;
}

/** Details section (collapsible) */
export interface ReportDetails {
  newsContent?: string;
  rawResult?: Record<string, unknown>;
  contextSnapshot?: Record<string, unknown>;
}

/** Full analysis report */
export interface AnalysisReport {
  meta: ReportMeta;
  summary: ReportSummary;
  strategy?: ReportStrategy;
  details?: ReportDetails;
}

// ============ Analysis result types ============

/** Synchronous analysis result */
export interface AnalysisResult {
  queryId: string;
  stockCode: string;
  stockName: string;
  report: AnalysisReport;
  createdAt: string;
}

/** Async task accepted response */
export interface TaskAccepted {
  taskId: string;
  status: 'pending' | 'processing';
  message?: string;
}

/** Task status */
export interface TaskStatus {
  taskId: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress?: number;
  result?: AnalysisResult;
  error?: string;
}

/** Task details for task lists and SSE events */
export interface TaskInfo {
  taskId: string;
  stockCode: string;
  stockName?: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  message?: string;
  reportType: string;
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
  error?: string;
}

/** Task list response */
export interface TaskListResponse {
  total: number;
  pending: number;
  processing: number;
  tasks: TaskInfo[];
}

/** Duplicate task error response */
export interface DuplicateTaskError {
  error: 'duplicate_task';
  message: string;
  stockCode: string;
  existingTaskId: string;
}

// ============ History types ============

/** History summary for list display */
export interface HistoryItem {
  id: number;  // Record primary key ID, always present for persisted history items
  queryId: string;  // query_id linked to the analysis record, repeated in batch analysis
  stockCode: string;
  stockName?: string;
  reportType?: string;
  sentimentScore?: number;
  operationAdvice?: string;
  createdAt: string;
}

/** History list response */
export interface HistoryListResponse {
  total: number;
  page: number;
  limit: number;
  items: HistoryItem[];
}

/** News intelligence item */
export interface NewsIntelItem {
  title: string;
  snippet: string;
  url: string;
}

/** News intelligence response */
export interface NewsIntelResponse {
  total: number;
  items: NewsIntelItem[];
}

/** History list filter parameters */
export interface HistoryFilters {
  stockCode?: string;
  startDate?: string;
  endDate?: string;
}

/** History list pagination parameters */
export interface HistoryPagination {
  page: number;
  limit: number;
}

// ============ Error types ============

export interface ApiError {
  error: string;
  message: string;
  detail?: Record<string, unknown>;
}

// ============ Helper functions ============

/** Get sentiment label from sentiment score */
export const getSentimentLabel = (score: number): SentimentLabel => {
  if (score >= 80) return '매우 긍정';
  if (score >= 60) return '긍정';
  if (score >= 40) return '중립';
  if (score >= 20) return '부정';
  return '매우 부정';
};

/** Get color from sentiment score */
export const getSentimentColor = (score: number): string => {
  if (score >= 80) return '#10b981'; // emerald-500
  if (score >= 60) return '#22c55e'; // green-500
  if (score >= 40) return '#eab308'; // yellow-500
  if (score >= 20) return '#f97316'; // orange-500
  return '#ef4444'; // red-500
};
