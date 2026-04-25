import apiClient from './index';
import { toCamelCase } from './utils';
import type {
  AnalysisRequest,
  AnalysisResult,
  AnalysisReport,
  TaskStatus,
  TaskListResponse,
} from '../types/analysis';

// ============ API interface ============

export const analysisApi = {
  /**
   * Trigger stock analysis
   * @param data Analysis request parameters
   * @returns Sync mode returns AnalysisResult, async mode returns TaskAccepted (check the status code)
   */
  analyze: async (data: AnalysisRequest): Promise<AnalysisResult> => {
    const requestData = {
      stock_code: data.stockCode,
      report_type: data.reportType || 'detailed',
      force_refresh: data.forceRefresh || false,
      async_mode: data.asyncMode || false,
    };

    const response = await apiClient.post<Record<string, unknown>>(
      '/api/v1/analysis/analyze',
      requestData
    );

    const result = toCamelCase<AnalysisResult>(response.data);

    // Ensure the report field is converted correctly
    if (result.report) {
      result.report = toCamelCase<AnalysisReport>(result.report);
    }

    return result;
  },

  /**
   * Trigger analysis in async mode
   * Returns task_id; use SSE or polling to get the result
   * @param data Analysis request parameters
   * @returns Task accepted response or a thrown 409 error
   */
  analyzeAsync: async (data: AnalysisRequest): Promise<{ taskId: string; status: string; message?: string }> => {
    const requestData = {
      stock_code: data.stockCode,
      report_type: data.reportType || 'detailed',
      force_refresh: data.forceRefresh || false,
      async_mode: true,
    };

    const response = await apiClient.post<Record<string, unknown>>(
      '/api/v1/analysis/analyze',
      requestData,
      {
        // Allow HTTP 202
        validateStatus: (status) => status === 200 || status === 202 || status === 409,
      }
    );

    // Handle 409 duplicate submission errors
    if (response.status === 409) {
      const errorData = toCamelCase<{
        error: string;
        message: string;
        stockCode: string;
        existingTaskId: string;
      }>(response.data);
      throw new DuplicateTaskError(errorData.stockCode, errorData.existingTaskId, errorData.message);
    }

    return toCamelCase<{ taskId: string; status: string; message?: string }>(response.data);
  },

  /**
   * Get async task status
   * @param taskId Task ID
   */
  getStatus: async (taskId: string): Promise<TaskStatus> => {
    const response = await apiClient.get<Record<string, unknown>>(
      `/api/v1/analysis/status/${taskId}`
    );

    const data = toCamelCase<TaskStatus>(response.data);

    // Ensure nested result is also converted correctly
    if (data.result) {
      data.result = toCamelCase<AnalysisResult>(data.result);
      if (data.result.report) {
        data.result.report = toCamelCase<AnalysisReport>(data.result.report);
      }
    }

    return data;
  },

  /**
   * Get task list
   * @param params Filter parameters
   */
  getTasks: async (params?: {
    status?: string;
    limit?: number;
  }): Promise<TaskListResponse> => {
    const response = await apiClient.get<Record<string, unknown>>(
      '/api/v1/analysis/tasks',
      { params }
    );

    const data = toCamelCase<TaskListResponse>(response.data);

    return data;
  },

  /**
   * Get SSE stream URL
   * Used by EventSource connections
   */
  getTaskStreamUrl: (): string => {
    // Get the API base URL
    const baseUrl = apiClient.defaults.baseURL || '';
    return `${baseUrl}/api/v1/analysis/tasks/stream`;
  },
};

// ============ Custom error classes ============

/**
 * Duplicate task error
 * Thrown when the stock is already being analyzed
 */
export class DuplicateTaskError extends Error {
  stockCode: string;
  existingTaskId: string;

  constructor(stockCode: string, existingTaskId: string, message?: string) {
    super(message || `종목 ${stockCode} 분석이 이미 진행 중입니다`);
    this.name = 'DuplicateTaskError';
    this.stockCode = stockCode;
    this.existingTaskId = existingTaskId;
  }
}
