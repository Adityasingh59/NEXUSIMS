import { apiClient } from '../lib/api';
import type { ApiEnvelope as ApiResponse } from '../lib/api';

export interface RMALine {
    id: string;
    sku_id: string;
    quantity_expected: number;
    quantity_received: number;
    condition: string | null;
    reason: string | null;
}

export interface RMA {
    id: string;
    tenant_id: string;
    warehouse_id: string;
    customer_name: string | null;
    order_reference: string | null;
    status: string;
    notes: string | null;
    created_at: string;
    lines: RMALine[];
}

export const rmaApi = {
    list: (status?: string) =>
        apiClient.get<ApiResponse<RMA[]>>('/rma', { params: { status } }),

    get: (id: string) =>
        apiClient.get<ApiResponse<RMA>>(`/rma/${id}`),

    create: (data: any) =>
        apiClient.post<ApiResponse<RMA>>('/rma', data),

    receive: (id: string, lines: { rma_line_id: string, quantity: number, condition?: string }[]) =>
        apiClient.post<ApiResponse<RMA>>(`/rma/${id}/receive`, { lines }),

    updateStatus: (id: string, status: string) =>
        apiClient.post<ApiResponse<RMA>>(`/rma/${id}/status`, { status }),
};
