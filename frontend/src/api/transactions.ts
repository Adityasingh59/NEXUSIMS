import { apiClient } from '../lib/api';

export interface ApiResponse<T> {
  data?: T;
  error?: string;
  meta?: { page: number; page_size: number; total_count?: number };
}

export const transactionsApi = {
  receive: (data: { sku_id: string; warehouse_id: string; quantity: number; notes?: string }) =>
    apiClient.post<ApiResponse<unknown>>('/transactions/receive', data),
  pick: (data: { sku_id: string; warehouse_id: string; quantity: number; reference_id?: string; notes?: string }) =>
    apiClient.post<ApiResponse<unknown>>('/transactions/pick', data),
  adjust: (data: { sku_id: string; warehouse_id: string; quantity: number; reason_code: string; notes?: string }) =>
    apiClient.post<ApiResponse<unknown>>('/transactions/adjust', data),
  return: (data: { sku_id: string; warehouse_id: string; quantity: number; disposition: string; notes?: string }) =>
    apiClient.post<ApiResponse<unknown>>('/transactions/return', data),
  getStock: (sku_id: string, warehouse_id: string) =>
    apiClient.get<ApiResponse<{ sku_id: string; warehouse_id: string; quantity: number }>>('/transactions/stock', {
      params: { sku_id, warehouse_id },
    }),
  list: (params?: { sku_id?: string; warehouse_id?: string; event_type?: string; page?: number; page_size?: number }) =>
    apiClient.get<ApiResponse<Array<{
      id: string;
      sku_id: string;
      warehouse_id: string;
      event_type: string;
      quantity_delta: number;
      running_balance: number;
      created_at: string;
    }>>>('/transactions', { params }),
};
