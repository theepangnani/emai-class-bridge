import { api } from './client';

// Inspiration Message Types
export interface InspirationMessage {
  id: number;
  text: string;
  author: string | null;
  role: string;
}

export interface InspirationMessageFull {
  id: number;
  role: string;
  text: string;
  author: string | null;
  is_active: boolean;
  created_at: string | null;
}

// Inspiration API
export const inspirationApi = {
  getRandom: async () => {
    const response = await api.get('/api/inspiration/random');
    return response.data as InspirationMessage | null;
  },
  list: async (params?: { role?: string; is_active?: boolean }) => {
    const response = await api.get('/api/inspiration/messages', { params });
    return response.data as InspirationMessageFull[];
  },
  create: async (data: { role: string; text: string; author?: string }) => {
    const response = await api.post('/api/inspiration/messages', data);
    return response.data as InspirationMessageFull;
  },
  update: async (id: number, data: { text?: string; author?: string; is_active?: boolean }) => {
    const response = await api.patch(`/api/inspiration/messages/${id}`, data);
    return response.data as InspirationMessageFull;
  },
  delete: async (id: number) => {
    await api.delete(`/api/inspiration/messages/${id}`);
  },
  seed: async () => {
    const response = await api.post('/api/inspiration/seed');
    return response.data as { seeded: number };
  },
};
