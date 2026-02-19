import { apiClient } from '../lib/api';

export interface TransferOrder {
  id: string;
  from_warehouse_id: string;
  to_warehouse_id: string;
  status: string;
  created_at: string | null;
  received_at: string | null;
  lines: Array<{ id: string; sku_id: string; quantity_requested: number; quantity_received: number | null }>;
}

export interface ApiResponse<T> {
  data?: T;
  error?: string;
  meta?: { page: number; page_size: number; total_count?: number };
}

export const transfersApi = {
  create: (data: {
    from_warehouse_id: string;
    to_warehouse_id: string;
    lines: Array<{ sku_id: string; quantity_requested: number }>;
  }) => apiClient.post<ApiResponse<TransferOrder>>('/transfers', data),
  list: (params?: { status?: string; warehouse_id?: string }) =>
    apiClient.get<ApiResponse<TransferOrder[]>>('/transfers', { params }),
  receive: (id: string, line_quantities?: Record<string, number>) =>
    apiClient.post<ApiResponse<{ id: string; status: string }>>(`/transfers/${id}/receive`, { line_quantities }),
  cancel: (id: string) =>
    apiClient.post<ApiResponse<{ id: string; status: string }>>(`/transfers/${id}/cancel`),
};
