import { apiClient as api } from '../lib/api';

export interface ScanLookupResult {
    sku_id: string;
    sku_code: string;
    sku_name: string;
    unit_cost: number | null;
    current_stock: number;
    reorder_point: number | null;
    warehouse_id: string;
}

export interface ScanConfirmation {
    success: boolean;
    event_type: string;
    sku_code: string;
    sku_name: string;
    quantity: number;
    new_balance: number;
    message: string;
}

export function scanLookup(barcode: string, warehouseId: string) {
    return api.post<{ data: ScanLookupResult }>('/scan/lookup', { barcode, warehouse_id: warehouseId }).then(r => r.data);
}

export function scanReceive(barcode: string, warehouseId: string, quantity: number, notes?: string) {
    return api.post<{ data: ScanConfirmation }>('/scan/receive', { barcode, warehouse_id: warehouseId, quantity, notes }).then(r => r.data);
}

export function scanPick(barcode: string, warehouseId: string, quantity = 1, notes?: string) {
    return api.post<{ data: ScanConfirmation }>('/scan/pick', { barcode, warehouse_id: warehouseId, quantity, notes }).then(r => r.data);
}

export function scanAdjust(barcode: string, warehouseId: string, quantityDelta: number, reasonCode: string, notes?: string) {
    return api.post<{ data: ScanConfirmation }>('/scan/adjust', { barcode, warehouse_id: warehouseId, quantity_delta: quantityDelta, reason_code: reasonCode, notes }).then(r => r.data);
}
