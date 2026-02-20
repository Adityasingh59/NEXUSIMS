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

export function listWarehouses() {
  return apiClient.get<ApiResponse<Warehouse[]>>('/warehouses');
}

export function getWarehouse(id: string) {
  return apiClient.get<ApiResponse<Warehouse>>(`/warehouses/${id}`);
}

export function createWarehouse(data: { name: string; code: string; address?: string; timezone?: string }) {
  return apiClient.post<ApiResponse<Warehouse>>('/warehouses', data);
}

export const warehousesApi = {
  list: listWarehouses,
  get: getWarehouse,
  create: createWarehouse,
};
