'use client';

import { useEffect, useState } from 'react';
import { io, Socket } from 'socket.io-client';

import { testingApi } from '@/lib/api';

export interface TestRunProgress {
  runId: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  currentTest?: string;
  completedTests: number;
  totalTests: number;
  score?: number;
  error?: string;
}

export function useTestRunProgress(runId: string | null) {
  const [progress, setProgress] = useState<TestRunProgress | null>(null);
  const [socket, setSocket] = useState<Socket | null>(null);

  useEffect(() => {
    if (!runId) {
      return;
    }

    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4000';
    const newSocket = io(`${API_BASE_URL}/test-runs`, {
      transports: ['websocket'],
    });

    newSocket.on('connect', () => {
      newSocket.emit('subscribe', { runId });
    });

    newSocket.on('test-run-progress', (data: TestRunProgress) => {
      if (data.runId === runId) {
        setProgress(data);
      }
    });

    newSocket.on('disconnect', () => {
      console.log('Disconnected from test run updates');
    });

    setSocket(newSocket);

    return () => {
      if (newSocket) {
        newSocket.emit('unsubscribe', { runId });
        newSocket.disconnect();
      }
    };
  }, [runId]);

  // Fallback poll to keep status fresh even if websockets stall or backend never emits
  useEffect(() => {
    if (!runId) {
      return;
    }

    let isMounted = true;
    let timeout: number | null = null;

    const poll = async () => {
      try {
        const run = await testingApi.getRun(runId);
        if (!isMounted) return;
        setProgress((prev) => ({
          runId,
          status: (run.status || '').toLowerCase() as TestRunProgress['status'],
          completedTests:
            run.status === 'COMPLETED' || run.status === 'FAILED' || run.status === 'CANCELLED'
              ? prev?.totalTests ?? 1
              : prev?.completedTests ?? 0,
          totalTests: prev?.totalTests ?? 1,
          score: run.score ?? prev?.score,
          error: prev?.error,
        }));

        // stop polling if terminal
        if (['COMPLETED', 'FAILED', 'CANCELLED'].includes(run.status)) {
          return;
        }
      } catch (err) {
        console.warn('poll run status failed', err);
      }

      timeout = window.setTimeout(poll, 2000);
    };

    poll();

    return () => {
      isMounted = false;
      if (timeout) clearTimeout(timeout);
    };
  }, [runId]);

  return { progress, socket };
}

