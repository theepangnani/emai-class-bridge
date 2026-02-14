import { api } from './client';

// Notification Types
export interface NotificationResponse {
  id: number;
  user_id: number;
  type: 'assignment_due' | 'grade_posted' | 'message' | 'system';
  title: string;
  content: string | null;
  link: string | null;
  read: boolean;
  created_at: string;
}

export interface NotificationPreferences {
  email_notifications: boolean;
  assignment_reminder_days: string;
}

// Notifications API
export const notificationsApi = {
  list: async (skip = 0, limit = 20, unreadOnly = false) => {
    const response = await api.get('/api/notifications/', { params: { skip, limit, unread_only: unreadOnly } });
    return response.data as NotificationResponse[];
  },

  getUnreadCount: async () => {
    const response = await api.get('/api/notifications/unread-count');
    return response.data as { count: number };
  },

  markAsRead: async (id: number) => {
    const response = await api.put(`/api/notifications/${id}/read`);
    return response.data as NotificationResponse;
  },

  markAllAsRead: async () => {
    await api.put('/api/notifications/read-all');
  },

  delete: async (id: number) => {
    await api.delete(`/api/notifications/${id}`);
  },

  getSettings: async () => {
    const response = await api.get('/api/notifications/settings');
    return response.data as NotificationPreferences;
  },

  updateSettings: async (settings: NotificationPreferences) => {
    const response = await api.put('/api/notifications/settings', settings);
    return response.data as NotificationPreferences;
  },
};
