import { apiClient } from '../lib/api';
import type { ApiEnvelope as ApiResponse } from '../lib/api';

export interface Webhook {
    id: string;
    url: string;
    events: string[];
    is_active: boolean;
    created_at: string;
}

export interface WebhookDelivery {
    id: string;
    webhook_id: string;
    event_type: string;
    payload: any;
    status: string;
    response_code: number | null;
    response_body: string | null;
    attempts: number;
    last_attempt_at: string | null;
    delivered_at: string | null;
}

export const webhooksApi = {
    list: () => apiClient.get<ApiResponse<Webhook[]>>('/webhooks'),
    create: (data: Partial<Webhook>) => apiClient.post<ApiResponse<Webhook>>('/webhooks', data),
    delete: (id: string) => apiClient.delete<ApiResponse<any>>(`/webhooks/${id}`),
    listDeliveries: (id: string) => apiClient.get<ApiResponse<WebhookDelivery[]>>(`/webhooks/${id}/deliveries`),
    retryDelivery: (webhook_id: string, delivery_id: string) =>
        apiClient.post<ApiResponse<any>>(`/webhooks/${webhook_id}/deliveries/${delivery_id}/retry`),
};
