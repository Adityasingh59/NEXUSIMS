import { apiClient as api } from '../lib/api';

export interface Meta {
    page: number;
    page_size: number;
    total_count?: number;
}

export interface ApiResponse<T> {
    data: T;
    error?: string;
    meta?: Meta;
}

export interface BOMLineCreate {
    component_sku_id: string;
    quantity: number;
    unit: string | null;
}

export interface BOMCreate {
    finished_sku_id: string;
    landed_cost: number;
    landed_cost_description: string | null;
    lines: BOMLineCreate[];
}

export interface BOMLineResponse {
    id: string;
    component_sku_id: string;
    quantity: number;
    unit: string | null;
}

export interface BOMResponse {
    id: string;
    finished_sku_id: string;
    version: number;
    is_active: boolean;
    landed_cost: number;
    landed_cost_description: string | null;
    lines: BOMLineResponse[];
    created_at: string;
}

export interface BOMAvailabilityResponse {
    is_available: boolean;
    shortages: Record<string, { required: number; available: number; shortage: number }>;
}

export interface AssemblyOrderCreate {
    bom_id: string;
    warehouse_id: string;
    planned_qty: number;
}

export interface AssemblyOrderComplete {
    produced_qty: number;
    waste_qty?: number;
    waste_reason?: string | null;
}

export interface AssemblyOrderResponse {
    id: string;
    tenant_id: string;
    bom_id: string;
    bom_version: number;
    warehouse_id: string;
    planned_qty: number;
    produced_qty: number | null;
    waste_qty: number | null;
    waste_reason: string | null;
    cogs_per_unit: number | null;
    status: string;
    started_at: string;
    completed_at: string | null;
}

// -- BOMs API --

export const getBOMs = async (
    params?: { finished_sku_id?: string; include_inactive?: boolean; page?: number; page_size?: number }
): Promise<{ data: BOMResponse[]; meta?: Meta }> => {
    const response = await api.get<ApiResponse<BOMResponse[]>>('/boms', { params });
    return { data: response.data.data, meta: response.data.meta };
};

export const getBOM = async (bomId: string): Promise<BOMResponse> => {
    const response = await api.get<ApiResponse<BOMResponse>>(`/boms/${bomId}`);
    return response.data.data;
};

export const createBOM = async (data: BOMCreate): Promise<BOMResponse> => {
    const response = await api.post<ApiResponse<BOMResponse>>('/boms', data);
    return response.data.data;
};

export const checkBOMAvailability = async (bomId: string, plannedQty: number): Promise<BOMAvailabilityResponse> => {
    const response = await api.get<ApiResponse<BOMAvailabilityResponse>>(`/boms/${bomId}/availability`, {
        params: { planned_qty: plannedQty }
    });
    return response.data.data;
};

// -- Assembly Orders API --

export const getAssemblyOrders = async (
    params?: { status?: string; page?: number; page_size?: number }
): Promise<{ data: AssemblyOrderResponse[]; meta?: Meta }> => {
    const response = await api.get<ApiResponse<AssemblyOrderResponse[]>>('/assembly-orders', { params });
    return { data: response.data.data, meta: response.data.meta };
};

export const createAssemblyOrder = async (data: AssemblyOrderCreate): Promise<AssemblyOrderResponse> => {
    const response = await api.post<ApiResponse<AssemblyOrderResponse>>('/assembly-orders', data);
    return response.data.data;
};

export const completeAssemblyOrder = async (orderId: string, data: AssemblyOrderComplete): Promise<AssemblyOrderResponse> => {
    const response = await api.post<ApiResponse<AssemblyOrderResponse>>(`/assembly-orders/${orderId}/complete`, data);
    return response.data.data;
};

export const cancelAssemblyOrder = async (orderId: string): Promise<AssemblyOrderResponse> => {
    const response = await api.post<ApiResponse<AssemblyOrderResponse>>(`/assembly-orders/${orderId}/cancel`);
    return response.data.data;
};
