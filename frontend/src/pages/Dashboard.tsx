import { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { googleApi, coursesApi, assignmentsApi, studyApi } from '../api/client';
import type { StudyGuide } from '../api/client';
import { StudyToolsButton } from '../components/StudyToolsButton';
import './Dashboard.css';

interface Course {
  id: number;
  name: string;
  google_classroom_id?: string;
}

interface Assignment {
  id: number;
  title: string;
  description: string | null;
  course_id: number;
  due_date: string | null;
}

export function Dashboard() {
  const { user, logout } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  const [googleConnected, setGoogleConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [courses, setCourses] = useState<Course[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [studyGuides, setStudyGuides] = useState<StudyGuide[]>([]);
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Check Google connection status on mount and handle OAuth callback
  useEffect(() => {
    const checkGoogleStatus = async () => {
      try {
        const status = await googleApi.getStatus();
        setGoogleConnected(status.connected);
      } catch {
        setGoogleConnected(false);
      }
    };

    // Handle OAuth callback params
    const connected = searchParams.get('google_connected');
    const error = searchParams.get('error');

    if (connected === 'true') {
      setGoogleConnected(true);
      setStatusMessage({ type: 'success', text: 'Google Classroom connected successfully!' });
      // Clear the URL params
      setSearchParams({});
    } else if (error) {
      setStatusMessage({ type: 'error', text: `Connection failed: ${error}` });
      setSearchParams({});
    }

    checkGoogleStatus();
    loadCourses();
    loadAssignments();
    loadStudyGuides();
  }, [searchParams, setSearchParams]);

  const loadCourses = async () => {
    try {
      const data = await coursesApi.list();
      setCourses(data);
    } catch {
      // Courses not loaded, that's okay
    }
  };

  const loadAssignments = async () => {
    try {
      const data = await assignmentsApi.list();
      setAssignments(data);
    } catch {
      // Assignments not loaded, that's okay
    }
  };

  const loadStudyGuides = async () => {
    try {
      const data = await studyApi.listGuides();
      setStudyGuides(data);
    } catch {
      // Study guides not loaded, that's okay
    }
  };

  const handleConnectGoogle = async () => {
    setIsConnecting(true);
    try {
      const { authorization_url } = await googleApi.getConnectUrl();
      window.location.href = authorization_url;
    } catch {
      setStatusMessage({ type: 'error', text: 'Failed to initiate Google connection' });
      setIsConnecting(false);
    }
  };

  const handleDisconnectGoogle = async () => {
    try {
      await googleApi.disconnect();
      setGoogleConnected(false);
      setStatusMessage({ type: 'success', text: 'Google Classroom disconnected' });
    } catch {
      setStatusMessage({ type: 'error', text: 'Failed to disconnect Google Classroom' });
    }
  };

  const handleSyncCourses = async () => {
    setIsSyncing(true);
    setStatusMessage(null);
    try {
      const result = await googleApi.syncCourses();
      setStatusMessage({ type: 'success', text: result.message || 'Courses synced successfully' });
      loadCourses();
    } catch {
      setStatusMessage({ type: 'error', text: 'Failed to sync courses' });
    } finally {
      setIsSyncing(false);
    }
  };

  // Clear status message after 5 seconds
  useEffect(() => {
    if (statusMessage) {
      const timer = setTimeout(() => setStatusMessage(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [statusMessage]);

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="header-left">
          <h1 className="logo">EMAI</h1>
        </div>
        <div className="header-right">
          <span className="user-name">{user?.full_name}</span>
          <span className="user-role">{user?.role}</span>
          <button onClick={logout} className="logout-button">
            Sign Out
          </button>
        </div>
      </header>

      <main className="dashboard-main">
        {statusMessage && (
          <div className={`status-message status-${statusMessage.type}`}>
            {statusMessage.text}
          </div>
        )}

        <div className="welcome-section">
          <h2>Welcome back, {user?.full_name?.split(' ')[0]}!</h2>
          <p>Here's your learning overview</p>
        </div>

        <div className="dashboard-grid">
          <div className="dashboard-card">
            <div className="card-icon">📚</div>
            <h3>Courses</h3>
            <p className="card-value">{courses.length || '--'}</p>
            <p className="card-label">Active courses</p>
          </div>

          <div className="dashboard-card">
            <div className="card-icon">📝</div>
            <h3>Assignments</h3>
            <p className="card-value">{assignments.length || '--'}</p>
            <p className="card-label">Total assignments</p>
          </div>

          <div className="dashboard-card">
            <div className="card-icon">📊</div>
            <h3>Average Grade</h3>
            <p className="card-value">--</p>
            <p className="card-label">Overall performance</p>
          </div>

          <div className="dashboard-card">
            <div className="card-icon">🔗</div>
            <h3>Google Classroom</h3>
            <p className="card-value">{googleConnected ? 'Connected' : 'Not Connected'}</p>
            {googleConnected ? (
              <div className="card-buttons">
                <button
                  className="connect-button"
                  onClick={handleSyncCourses}
                  disabled={isSyncing}
                >
                  {isSyncing ? 'Syncing...' : 'Sync Courses'}
                </button>
                <button
                  className="disconnect-button"
                  onClick={handleDisconnectGoogle}
                >
                  Disconnect
                </button>
              </div>
            ) : (
              <button
                className="connect-button"
                onClick={handleConnectGoogle}
                disabled={isConnecting}
              >
                {isConnecting ? 'Connecting...' : 'Connect'}
              </button>
            )}
          </div>
        </div>

        <div className="dashboard-sections">
          <section className="section">
            <h3>Your Assignments</h3>
            {assignments.length > 0 ? (
              <ul className="assignments-list">
                {assignments.map((assignment) => (
                  <li key={assignment.id} className="assignment-item">
                    <div className="assignment-info">
                      <span className="assignment-title">{assignment.title}</span>
                      {assignment.due_date && (
                        <span className="assignment-due">
                          Due: {new Date(assignment.due_date).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                    <StudyToolsButton
                      assignmentId={assignment.id}
                      assignmentTitle={assignment.title}
                    />
                  </li>
                ))}
              </ul>
            ) : (
              <div className="empty-state">
                <p>No assignments yet</p>
                <small>Sync your Google Classroom to see assignments</small>
              </div>
            )}
          </section>

          <section className="section">
            <h3>Your Study Materials</h3>
            {studyGuides.length > 0 ? (
              <ul className="study-guides-list">
                {studyGuides.map((guide) => (
                  <li key={guide.id} className="study-guide-item">
                    <Link
                      to={
                        guide.guide_type === 'quiz'
                          ? `/study/quiz/${guide.id}`
                          : guide.guide_type === 'flashcards'
                          ? `/study/flashcards/${guide.id}`
                          : `/study/guide/${guide.id}`
                      }
                      className="study-guide-link"
                    >
                      <span className="guide-icon">
                        {guide.guide_type === 'quiz' ? '❓' : guide.guide_type === 'flashcards' ? '🃏' : '📖'}
                      </span>
                      <span className="guide-title">{guide.title}</span>
                      <span className="guide-date">
                        {new Date(guide.created_at).toLocaleDateString()}
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="empty-state">
                <p>No study materials yet</p>
                <small>Generate study guides, quizzes, or flashcards from your assignments</small>
              </div>
            )}
          </section>

          <section className="section">
            <h3>Your Courses</h3>
            {courses.length > 0 ? (
              <ul className="courses-list">
                {courses.map((course) => (
                  <li key={course.id} className="course-item">
                    <span className="course-name">{course.name}</span>
                    {course.google_classroom_id && (
                      <span className="google-badge">Google</span>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <div className="empty-state">
                <p>No courses yet</p>
                <small>Connect Google Classroom to sync your courses</small>
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}
