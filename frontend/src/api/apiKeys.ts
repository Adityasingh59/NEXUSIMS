/**
 * NEXUS IMS — API Keys API client (Block 4)
 */
import { apiClient as axios } from "../lib/api";

export interface APIKeyResponse {
    id: string;
    name: string;
    key_prefix: string;
    scopes: string[];
    last_used_at: string | null;
    created_at: string;
}

export interface CreateAPIKeyRequest {
    name: string;
    scopes: string[];
}

export interface CreateAPIKeyResponse {
    id: string;
    name: string;
    key_prefix: string;
    raw_key: string; // Shown once only
    scopes: string[];
}

export async function createAPIKey(
    data: CreateAPIKeyRequest
): Promise<CreateAPIKeyResponse> {
    const res = await axios.post("/api/v1/api-keys", data);
    return res.data.data;
}

export async function listAPIKeys(): Promise<APIKeyResponse[]> {
    const res = await axios.get("/api/v1/api-keys");
    return res.data.data;
}

export async function revokeAPIKey(keyId: string): Promise<void> {
    await axios.delete(`/api/v1/api-keys/${keyId}`);
}
