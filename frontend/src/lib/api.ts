/**
 * NEXUS IMS — API client (Axios + React Query)
 */
import axios, { AxiosInstance } from 'axios';

const API_BASE = import.meta.env.VITE_API_URL ?? '/api/v1';

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE,
  timeout: 5000,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true, // for httpOnly refresh token cookie
});

// Add Bearer token from localStorage (set after login)
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Response envelope: { data, error, meta }
export interface ApiEnvelope<T> {
  data?: T;
  error?: string;
  meta?: { page?: number; page_size?: number; total_count?: number };
}
