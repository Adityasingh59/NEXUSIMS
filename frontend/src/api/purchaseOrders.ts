import { apiClient } from '../lib/api';

export interface POLine {
    id: string;
    sku_id: string;
    quantity_ordered: number;
    quantity_received: number;
    unit_cost: number;
}

export interface PurchaseOrder {
    id: string;
    supplier_name: string;
    status: 'DRAFT' | 'ORDERED' | 'PARTIAL' | 'RECEIVED' | 'CANCELLED';
    warehouse_id: string;
    notes: string | null;
    lines: POLine[];
    created_at: string;
}

export interface ApiResponse<T> {
    data?: T;
    error?: string;
    meta?: { page: number; page_size: number; total_count?: number };
}

export const purchaseOrdersApi = {
    list: (params?: { status?: string }) =>
        apiClient.get<ApiResponse<PurchaseOrder[]>>('/purchase-orders', { params }),

    create: (data: {
        supplier_name: string;
        warehouse_id: string;
        notes?: string;
        lines: Array<{ sku_id: string; quantity_ordered: number; unit_cost: number }>;
    }) => apiClient.post<ApiResponse<PurchaseOrder>>('/purchase-orders', data),

    get: (id: string) => apiClient.get<ApiResponse<PurchaseOrder>>(`/purchase-orders/${id}`),

    receive: (id: string, lines: Array<{ po_line_id: string; quantity_received: number }>) =>
        apiClient.post<ApiResponse<PurchaseOrder>>(`/purchase-orders/${id}/receive`, { lines }),

    cancel: (id: string) =>
        apiClient.post<ApiResponse<PurchaseOrder>>(`/purchase-orders/${id}/cancel`),
};
