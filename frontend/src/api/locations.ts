import { apiClient } from '../lib/api';

export interface Location {
  id: string;
  tenant_id: string;
  warehouse_id: string;
  parent_id: string | null;
  name: string;
  code: string;
  location_type: string;
  is_active: boolean;
}

export interface ApiResponse<T> {
  data?: T;
  error?: string;
  meta?: { page: number; page_size: number; total_count?: number };
}

export const locationsApi = {
  list: (warehouse_id: string, parent_id?: string) =>
    apiClient.get<ApiResponse<Location[]>>('/locations', { params: { warehouse_id, parent_id } }),
  create: (data: { warehouse_id: string; name: string; code: string; location_type: string; parent_id?: string }) =>
    apiClient.post<ApiResponse<Location>>('/locations', data),
  getPath: (id: string) => apiClient.get<ApiResponse<string[]>>(`/locations/${id}/path`),
};
