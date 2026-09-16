import { authStore } from '@/store/authStore';

const API_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000';

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = authStore.getState().accessToken;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `Request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  auth: {
    signup: (email: string, password: string) =>
      request<{ access_token: string; user: { id: string; email: string } }>('/auth/signup', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }),
    login: (email: string, password: string) =>
      request<{ access_token: string; user: { id: string; email: string } }>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }),
    logout: () => request('/auth/logout', { method: 'POST' }),
    me: () => request<{ user_id: string; email: string }>('/auth/me'),
  },
  uploads: {
    getUrl: (tier: 'free' | 'premium', filename: string) =>
      request<{ upload_url: string; r2_key: string; job_id: string }>('/uploads/url', {
        method: 'POST',
        body: JSON.stringify({ tier, filename }),
      }),
    confirm: (jobId: string) =>
      request<{ status: string }>(`/uploads/${jobId}/confirm`, { method: 'POST' }),
  },
  jobs: {
    list: (page = 1) =>
      request<{ jobs: Job[]; total: number; page: number; page_size: number }>(`/jobs?page=${page}`),
    get: (jobId: string) => request<Job>(`/jobs/${jobId}`),
    getResult: (jobId: string) => request<Result>(`/jobs/${jobId}/result`),
  },
};

export interface Job {
  id: string;
  tier: 'free' | 'premium';
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'rejected';
  rejection_reason?: string;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface Result {
  job_id: string;
  stroke_type: 'forehand' | 'backhand' | 'serve' | 'volley';
  fault_label?: string;
  confidence: number;
  recommendation: string;
  reference_clip_url?: string;
  overlay_video_url?: string;
  skeleton_3d_url?: string;
  delta_summary?: Record<string, number>;
  fault_joints?: string[];
  created_at: string;
}
