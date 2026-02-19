import { apiClient } from '../lib/api';

export interface AttributeFieldSchema {
  name: string;
  type: 'text' | 'number' | 'date' | 'boolean' | 'enum';
  required?: boolean;
  options?: string[];
}

export interface ItemType {
  id: string;
  tenant_id: string;
  name: string;
  code: string;
  attribute_schema: AttributeFieldSchema[];
  version: number;
  is_archived: boolean;
}

export interface ApiResponse<T> {
  data?: T;
  error?: string;
  meta?: { page: number; page_size: number; total_count?: number };
}

export const itemTypesApi = {
  list: (includeArchived = false) =>
    apiClient.get<ApiResponse<ItemType[]>>('/item-types', {
      params: { include_archived: includeArchived },
    }),
  get: (id: string) => apiClient.get<ApiResponse<ItemType>>(`/item-types/${id}`),
  create: (data: { name: string; code: string; attribute_schema: AttributeFieldSchema[] }) =>
    apiClient.post<ApiResponse<ItemType>>('/item-types', data),
  update: (id: string, data: { name?: string; attribute_schema?: AttributeFieldSchema[] }) =>
    apiClient.put<ApiResponse<ItemType>>(`/item-types/${id}`, data),
  archive: (id: string) => apiClient.delete(`/item-types/${id}`),
};
