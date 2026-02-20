import { apiClient } from '../lib/api';

export interface BOMLine {
  id: string;
  component_sku_id: string;
  quantity: number;
  unit_cost_snapshot: number;
}

export interface BOM {
  id: string;
  sku_id: string;
  name: string;
  is_active: boolean;
  lines: BOMLine[];
  created_at: string;
}

export interface ApiResponse<T> {
  data?: T;
  error?: string;
  meta?: { page: number; page_size: number; total_count?: number };
}

export const bomsApi = {
  list: (params?: { sku_id?: string; include_inactive?: boolean }) =>
    apiClient.get<ApiResponse<BOM[]>>('/boms', { params }),

  create: (data: {
    sku_id: string;
    name: string;
    lines: Array<{ component_sku_id: string; quantity: number; unit_cost_snapshot: number }>;
  }) => apiClient.post<ApiResponse<BOM>>('/boms', data),

  get: (id: string) => apiClient.get<ApiResponse<BOM>>(`/boms/${id}`),

  update: (
    id: string,
    data: {
      name?: string;
      lines?: Array<{ component_sku_id: string; quantity: number; unit_cost_snapshot: number }>;
    }
  ) => apiClient.put<ApiResponse<BOM>>(`/boms/${id}`, data),

  archive: (id: string) => apiClient.delete<ApiResponse<BOM>>(`/boms/${id}`),

  explode: (id: string, quantity: number) =>
    apiClient.post<ApiResponse<{ bom_id: string; quantity: number; components: Record<string, number> }>>(
      `/boms/${id}/explode`,
      null,
      { params: { quantity } }
    ),
};
