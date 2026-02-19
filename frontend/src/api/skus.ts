import { apiClient } from '../lib/api';

export interface SKU {
  id: string;
  tenant_id: string;
  sku_code: string;
  name: string;
  item_type_id: string;
  attributes: Record<string, unknown>;
  reorder_point: number | null;
  unit_cost: number | null;
  is_archived: boolean;
}

export interface ApiResponse<T> {
  data?: T;
  error?: string;
  meta?: { page: number; page_size: number; total_count?: number };
}

export const skusApi = {
  list: (params?: {
    item_type_id?: string;
    search?: string;
    low_stock?: boolean;
    include_archived?: boolean;
    page?: number;
    page_size?: number;
  }) => apiClient.get<ApiResponse<SKU[]>>('/skus', { params }),
  get: (id: string) => apiClient.get<ApiResponse<SKU>>(`/skus/${id}`),
  create: (data: {
    sku_code: string;
    name: string;
    item_type_id: string;
    attributes: Record<string, unknown>;
    reorder_point?: number;
    unit_cost?: number;
  }) => apiClient.post<ApiResponse<SKU>>('/skus', data),
  update: (id: string, data: Partial<Pick<SKU, 'name' | 'attributes' | 'reorder_point' | 'unit_cost'>>) =>
    apiClient.put<ApiResponse<SKU>>(`/skus/${id}`, data),
  archive: (id: string, force?: boolean) =>
    apiClient.delete(`/skus/${id}`, { params: { force } }),
};
