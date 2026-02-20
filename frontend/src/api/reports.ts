import { apiClient as api } from '../lib/api';

export function getDashboard() {
    return api.get('/reports/dashboard').then(r => r.data);
}

export function getStockValuation(warehouseId?: string) {
    const params = warehouseId ? { warehouse_id: warehouseId } : {};
    return api.get('/reports/stock-valuation', { params }).then(r => r.data);
}

export function getLowStockSkus() {
    return api.get('/reports/low-stock').then(r => r.data);
}

export function getMovementHistory(params?: { warehouse_id?: string; date_from?: string; date_to?: string }) {
    return api.get('/reports/movement-history', { params }).then(r => r.data);
}

export function getRecentActivity(limit = 20) {
    return api.get('/reports/recent-activity', { params: { limit } }).then(r => r.data);
}
