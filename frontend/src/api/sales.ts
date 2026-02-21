import { apiClient } from '../lib/api';
import type { SKU } from './skus';

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

export interface SalesOrderLine {
    id: string;
    sales_order_id: string;
    sku_id: string;
    quantity: number;
    unit_price: number;
    fulfilled_qty: number;
    sku?: SKU;
}

export interface SalesOrder {
    id: string;
    tenant_id: string;
    customer_name: string;
    order_reference: string | null;
    status: 'PENDING' | 'PROCESSING' | 'SHIPPED' | 'CANCELLED';
    shipping_address: string | null;
    created_at: string;
    lines: SalesOrderLine[];
}

export interface CreateSalesOrderLine {
    sku_id: string;
    quantity: number;
    unit_price: number;
}

export interface CreateSalesOrderValues {
    customer_name: string;
    order_reference?: string;
    shipping_address?: string;
    lines: CreateSalesOrderLine[];
}

export const getSalesOrders = async (): Promise<SalesOrder[]> => {
    const response = await apiClient.get<ApiResponse<SalesOrder[]>>('/sales-orders');
    return response.data.data;
};

export const getSalesOrder = async (orderId: string): Promise<SalesOrder> => {
    const response = await apiClient.get<ApiResponse<SalesOrder>>(`/sales-orders/${orderId}`);
    return response.data.data;
};

export const createSalesOrder = async (values: CreateSalesOrderValues): Promise<SalesOrder> => {
    const response = await apiClient.post<ApiResponse<SalesOrder>>('/sales-orders', values);
    return response.data.data;
};

export const allocateSalesOrder = async (orderId: string, warehouseId: string): Promise<any> => {
    const response = await apiClient.post<ApiResponse<any>>(`/sales-orders/${orderId}/allocate`, {
        warehouse_id: warehouseId,
    });
    return response.data.data;
};

export const shipSalesOrder = async (orderId: string, warehouseId: string): Promise<SalesOrder> => {
    const response = await apiClient.post<ApiResponse<SalesOrder>>(`/sales-orders/${orderId}/ship`, {
        warehouse_id: warehouseId,
    });
    return response.data.data;
};

export const cancelSalesOrder = async (orderId: string, warehouseId: string): Promise<SalesOrder> => {
    const response = await apiClient.post<ApiResponse<SalesOrder>>(`/sales-orders/${orderId}/cancel`, {
        warehouse_id: warehouseId,
    });
    return response.data.data;
};
