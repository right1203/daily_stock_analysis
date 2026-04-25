import { useEffect, useRef, useCallback, useState } from 'react';
import { analysisApi } from '../api/analysis';
import type { TaskInfo } from '../types/analysis';

/**
 * SSE event type
 */
export type SSEEventType =
  | 'connected'
  | 'task_created'
  | 'task_started'
  | 'task_completed'
  | 'task_failed'
  | 'heartbeat';

/**
 * SSE event data
 */
export interface SSEEvent {
  type: SSEEventType;
  task?: TaskInfo;
  timestamp?: string;
}

/**
 * SSE hook options
 */
export interface UseTaskStreamOptions {
  /** Task-created callback */
  onTaskCreated?: (task: TaskInfo) => void;
  /** Task-started callback */
  onTaskStarted?: (task: TaskInfo) => void;
  /** Task-completed callback */
  onTaskCompleted?: (task: TaskInfo) => void;
  /** Task-failed callback */
  onTaskFailed?: (task: TaskInfo) => void;
  /** Connection-success callback */
  onConnected?: () => void;
  /** Connection-error callback */
  onError?: (error: Event) => void;
  /** Whether to reconnect automatically */
  autoReconnect?: boolean;
  /** Reconnect delay (ms) */
  reconnectDelay?: number;
  /** Whether enabled */
  enabled?: boolean;
}

/**
 * SSE hook result
 */
export interface UseTaskStreamResult {
  /** Whether connected */
  isConnected: boolean;
  /** Manual reconnect */
  reconnect: () => void;
  /** Manual disconnect */
  disconnect: () => void;
}

/**
 * Task stream SSE hook
 * Receives real-time task status updates
 *
 * @example
 * ```tsx
 * const { isConnected } = useTaskStream({
 *   onTaskCompleted: (task) => {
 *     console.log('Task completed:', task);
 *     refreshHistory();
 *   },
 *   onTaskFailed: (task) => {
 *     showError(task.error);
 *   },
 * });
 * ```
 */
export function useTaskStream(options: UseTaskStreamOptions = {}): UseTaskStreamResult {
  const {
    onTaskCreated,
    onTaskStarted,
    onTaskCompleted,
    onTaskFailed,
    onConnected,
    onError,
    autoReconnect = true,
    reconnectDelay = 3000,
    enabled = true,
  } = options;

  const eventSourceRef = useRef<EventSource | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const connectRef = useRef<() => void>(() => {});

  // Store callbacks in a ref to avoid frequent SSE reconnects when callbacks change
  const callbacksRef = useRef({
    onTaskCreated,
    onTaskStarted,
    onTaskCompleted,
    onTaskFailed,
    onConnected,
    onError,
  });

  // Update the callback ref on each render so event handlers use the latest callbacks
  useEffect(() => {
    callbacksRef.current = {
      onTaskCreated,
      onTaskStarted,
      onTaskCompleted,
      onTaskFailed,
      onConnected,
      onError,
    };
  });

  // Convert snake_case to camelCase
  const toCamelCase = (data: Record<string, unknown>): TaskInfo => {
    return {
      taskId: data.task_id as string,
      stockCode: data.stock_code as string,
      stockName: data.stock_name as string | undefined,
      status: data.status as TaskInfo['status'],
      progress: data.progress as number,
      message: data.message as string | undefined,
      reportType: data.report_type as string,
      createdAt: data.created_at as string,
      startedAt: data.started_at as string | undefined,
      completedAt: data.completed_at as string | undefined,
      error: data.error as string | undefined,
    };
  };

  // Parse SSE data
  const parseEventData = useCallback((eventData: string): TaskInfo | null => {
    try {
      const data = JSON.parse(eventData);
      return toCamelCase(data);
    } catch (e) {
      console.error('Failed to parse SSE event data:', e);
      return null;
    }
  }, []);

  // Create the EventSource connection
  const connect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const url = analysisApi.getTaskStreamUrl();
    const eventSource = new EventSource(url, { withCredentials: true });
    eventSourceRef.current = eventSource;

    // Connection succeeded
    eventSource.addEventListener('connected', () => {
      setIsConnected(true);
      callbacksRef.current.onConnected?.();
    });

    // Task created
    eventSource.addEventListener('task_created', (e) => {
      const task = parseEventData(e.data);
      if (task) callbacksRef.current.onTaskCreated?.(task);
    });

    // Task started
    eventSource.addEventListener('task_started', (e) => {
      const task = parseEventData(e.data);
      if (task) callbacksRef.current.onTaskStarted?.(task);
    });

    // Task completed
    eventSource.addEventListener('task_completed', (e) => {
      const task = parseEventData(e.data);
      if (task) callbacksRef.current.onTaskCompleted?.(task);
    });

    // Task failed
    eventSource.addEventListener('task_failed', (e) => {
      const task = parseEventData(e.data);
      if (task) callbacksRef.current.onTaskFailed?.(task);
    });

    // Heartbeat, used only to keep the connection alive
    eventSource.addEventListener('heartbeat', () => {
      // Optional: update the last heartbeat time
    });

    // Error handling
    eventSource.onerror = (error) => {
      setIsConnected(false);
      callbacksRef.current.onError?.(error);

      // Automatic reconnect, using the ref to avoid a closure over an undeclared connect
      if (autoReconnect && enabled) {
        eventSource.close();
        reconnectTimeoutRef.current = setTimeout(() => {
          connectRef.current();
        }, reconnectDelay);
      }
    };
  }, [
    autoReconnect,
    reconnectDelay,
    enabled,
    parseEventData,
  ]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  // Disconnect, deferring setState to avoid cascading renders from synchronous setState inside an effect
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    queueMicrotask(() => setIsConnected(false));
  }, []);

  // Reconnect
  const reconnect = useCallback(() => {
    disconnect();
    connect();
  }, [disconnect, connect]);

  // Connect or disconnect when enabled changes
  useEffect(() => {
    if (enabled) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [enabled, connect, disconnect]);

  return {
    isConnected,
    reconnect,
    disconnect,
  };
}

export default useTaskStream;
