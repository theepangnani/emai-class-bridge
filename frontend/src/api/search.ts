import { api } from './client';

// Search Types
export interface SearchResultItem {
  id: number;
  title: string;
  subtitle: string | null;
  entity_type: string;
  url: string;
}

export interface SearchResultGroup {
  entity_type: string;
  label: string;
  items: SearchResultItem[];
  total: number;
}

export interface SearchResponse {
  query: string;
  groups: SearchResultGroup[];
  total: number;
}

// Search API
export const searchApi = {
  search: async (query: string, types?: string, limit?: number) => {
    const params: Record<string, string | number> = { q: query };
    if (types) params.types = types;
    if (limit) params.limit = limit;
    const response = await api.get('/api/search', { params });
    return response.data as SearchResponse;
  },
};
