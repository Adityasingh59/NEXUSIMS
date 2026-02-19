import { apiClient } from '../lib/api';

export interface Warehouse {
  id: string;
  tenant_id: string;
  name: string;
  code: string;
  address: string | null;
  timezone: string;
  is_active: boolean;
}

export interface ApiResponse<T> {
  data?: T;
  error?: string;
  meta?: { page: number; page_size: number; total_count?: number };
}

export const warehousesApi = {
  list: () => apiClient.get<ApiResponse<Warehouse[]>>('/warehouses'),
  get: (id: string) => apiClient.get<ApiResponse<Warehouse>>(`/warehouses/${id}`),
  create: (data: { name: string; code: string; address?: string; timezone?: string }) =>
    apiClient.post<ApiResponse<Warehouse>>('/warehouses', data),
};
