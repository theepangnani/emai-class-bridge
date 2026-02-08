import { useMemo, useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { messagesApi } from '../api/client';
import { NotificationBell } from './NotificationBell';
import '../pages/Dashboard.css';

interface SidebarAction {
  label: string;
  onClick: () => void;
}

interface DashboardLayoutProps {
  children: React.ReactNode;
  welcomeSubtitle?: string;
  sidebarActions?: SidebarAction[];
}

export function DashboardLayout({ children, welcomeSubtitle, sidebarActions }: DashboardLayoutProps) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [unreadCount, setUnreadCount] = useState(0);

  const dashboardTitle = useMemo(() => {
    switch (user?.role) {
      case 'parent': return "Parent's Dashboard";
      case 'student': return "Student's Dashboard";
      case 'teacher': return "Teacher's Dashboard";
      case 'admin': return "Admin Dashboard";
      default: return 'Dashboard';
    }
  }, [user?.role]);

  const navItems = useMemo(() => {
    const items: Array<{ label: string; path: string }> = [
      { label: 'Dashboard', path: '/dashboard' },
    ];

    if (user?.role === 'parent') {
      items.push(
        { label: 'Courses', path: '/courses' },
        { label: 'Study Guides', path: '/study-guides' },
      );
    }

    items.push({ label: 'Messages', path: '/messages' });

    if (user?.role === 'teacher') {
      items.push({ label: 'Teacher Comms', path: '/teacher-communications' });
    }

    return items;
  }, [user?.role]);

  useEffect(() => {
    const loadUnreadCount = async () => {
      try {
        const data = await messagesApi.getUnreadCount();
        setUnreadCount(data.total_unread);
      } catch {
        // Silently fail
      }
    };

    loadUnreadCount();
    const interval = setInterval(loadUnreadCount, 60000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="header-left">
          <img src="/logo-icon.png" alt="ClassBridge" className="header-logo" onClick={() => navigate('/dashboard')} style={{ cursor: 'pointer' }} />
          <h1 className="logo" onClick={() => navigate('/dashboard')} style={{ cursor: 'pointer' }}>{dashboardTitle}</h1>
        </div>
        <div className="header-right">
          <NotificationBell />
          <div className="user-chip">
            <span className="user-name">{user?.full_name}</span>
            <span className="user-role">{user?.role}</span>
          </div>
          <button onClick={logout} className="logout-button">
            Sign Out
          </button>
        </div>
      </header>

      <div className="dashboard-body">
        <aside className="dashboard-sidebar">
          <div className="sidebar-title">Navigation</div>
          <nav className="sidebar-nav">
            {navItems.map((item) => (
              <button
                key={item.path}
                className={`sidebar-link${location.pathname === item.path ? ' active' : ''}`}
                onClick={() => navigate(item.path)}
              >
                {item.label}
                {item.path === '/messages' && unreadCount > 0 && (
                  <span className="sidebar-badge">{unreadCount}</span>
                )}
              </button>
            ))}
          </nav>
          {sidebarActions && sidebarActions.length > 0 && (
            <>
              <div className="sidebar-divider" />
              <div className="sidebar-title">Quick Actions</div>
              <div className="sidebar-nav">
                {sidebarActions.map((action, i) => (
                  <button
                    key={i}
                    className="sidebar-action"
                    onClick={action.onClick}
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            </>
          )}
          <div className="sidebar-footer">
            <div className="sidebar-stat">
              <span>Unread</span>
              <strong>{unreadCount}</strong>
            </div>
          </div>
        </aside>

        <main className="dashboard-main">
          <div className="welcome-section">
            <h2>Welcome back, {user?.full_name?.split(' ')[0]}!</h2>
            <p>{welcomeSubtitle || "Here's your overview"}</p>
          </div>

          {children}
        </main>
      </div>
    </div>
  );
}
