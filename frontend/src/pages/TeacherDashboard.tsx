import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { coursesApi, googleApi, invitesApi } from '../api/client';
import { DashboardLayout } from '../components/DashboardLayout';
import { PageSkeleton } from '../components/Skeleton';
import './TeacherDashboard.css';

interface Course {
  id: number;
  name: string;
  description: string | null;
  subject: string | null;
  google_classroom_id: string | null;
}

export function TeacherDashboard() {
  const navigate = useNavigate();
  const [courses, setCourses] = useState<Course[]>([]);
  const [googleConnected, setGoogleConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  // Create course modal state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [courseName, setCourseName] = useState('');
  const [courseSubject, setCourseSubject] = useState('');
  const [courseDescription, setCourseDescription] = useState('');
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState('');

  // Invite parent modal state
  const [showInviteParentModal, setShowInviteParentModal] = useState(false);
  const [inviteParentEmail, setInviteParentEmail] = useState('');
  const [inviteStudentId, setInviteStudentId] = useState<number | null>(null);
  const [inviteLoading, setInviteLoading] = useState(false);
  const [inviteError, setInviteError] = useState('');
  const [inviteSuccess, setInviteSuccess] = useState('');
  const [students, setStudents] = useState<{ id: number; name: string }[]>([]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [coursesData, googleStatus] = await Promise.allSettled([
        coursesApi.teachingList(),
        googleApi.getStatus(),
      ]);

      let loadedCourses: Course[] = [];
      if (coursesData.status === 'fulfilled') {
        loadedCourses = coursesData.value;
        setCourses(loadedCourses);
      }
      if (googleStatus.status === 'fulfilled') {
        setGoogleConnected(googleStatus.value.connected);
      }

      // Load unique students across all courses for invite-parent feature
      if (loadedCourses.length > 0) {
        const allStudents = new Map<number, string>();
        const studentResults = await Promise.allSettled(
          loadedCourses.map(c => coursesApi.listStudents(c.id))
        );
        for (const r of studentResults) {
          if (r.status === 'fulfilled') {
            for (const s of r.value) {
              allStudents.set(s.student_id, s.full_name || s.email || `Student #${s.student_id}`);
            }
          }
        }
        setStudents(Array.from(allStudents.entries()).map(([id, name]) => ({ id, name })));
      }
    } finally {
      setLoading(false);
    }
  };

  const handleConnectGoogle = async () => {
    try {
      const { authorization_url } = await googleApi.getConnectUrl();
      window.location.href = authorization_url;
    } catch {
      // Failed to connect
    }
  };

  const handleSyncCourses = async () => {
    setSyncing(true);
    try {
      await googleApi.syncCourses();
      // Reload courses after sync
      const coursesData = await coursesApi.teachingList();
      setCourses(coursesData);
    } catch {
      // Sync failed
    } finally {
      setSyncing(false);
    }
  };

  const closeCreateModal = () => {
    setShowCreateModal(false);
    setCourseName('');
    setCourseSubject('');
    setCourseDescription('');
    setCreateError('');
  };

  const handleCreateCourse = async () => {
    if (!courseName.trim()) return;
    setCreateLoading(true);
    setCreateError('');
    try {
      await coursesApi.create({
        name: courseName.trim(),
        description: courseDescription.trim() || undefined,
        subject: courseSubject.trim() || undefined,
      });
      closeCreateModal();
      const coursesData = await coursesApi.teachingList();
      setCourses(coursesData);
    } catch (err: any) {
      setCreateError(err.response?.data?.detail || 'Failed to create course');
    } finally {
      setCreateLoading(false);
    }
  };

  const closeInviteParentModal = () => {
    setShowInviteParentModal(false);
    setInviteParentEmail('');
    setInviteStudentId(null);
    setInviteError('');
    setInviteSuccess('');
  };

  const handleInviteParent = async () => {
    if (!inviteParentEmail.trim() || !inviteStudentId) return;
    setInviteLoading(true);
    setInviteError('');
    setInviteSuccess('');
    try {
      await invitesApi.inviteParent(inviteParentEmail.trim(), inviteStudentId);
      setInviteSuccess(`Invitation sent to ${inviteParentEmail.trim()}`);
      setInviteParentEmail('');
      setInviteStudentId(null);
    } catch (err: any) {
      setInviteError(err.response?.data?.detail || 'Failed to send invitation');
    } finally {
      setInviteLoading(false);
    }
  };

  if (loading) {
    return (
      <DashboardLayout welcomeSubtitle="Your classroom overview">
        <PageSkeleton />
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout welcomeSubtitle="Your classroom overview">
      <div className="dashboard-grid">
        <div className="dashboard-card">
          <div className="card-icon">📚</div>
          <h3>Courses</h3>
          <p className="card-value">{courses.length}</p>
          <p className="card-label">Courses teaching</p>
        </div>

        <div className="dashboard-card clickable" onClick={() => navigate('/messages')}>
          <div className="card-icon">💬</div>
          <h3>Messages</h3>
          <p className="card-value">View</p>
          <p className="card-label">Parent messages</p>
        </div>

        <div className="dashboard-card clickable" onClick={() => navigate('/teacher-communications')}>
          <div className="card-icon">📧</div>
          <h3>Communications</h3>
          <p className="card-value">View</p>
          <p className="card-label">Email monitoring</p>
        </div>

        <div className="dashboard-card clickable" onClick={() => setShowInviteParentModal(true)}>
          <div className="card-icon">👨‍👩‍👧</div>
          <h3>Invite Parent</h3>
          <p className="card-value">Invite</p>
          <p className="card-label">Connect families</p>
        </div>

        <div className="dashboard-card">
          <div className="card-icon">🔗</div>
          <h3>Google Classroom</h3>
          <p className="card-value">{googleConnected ? 'Connected' : 'Not Connected'}</p>
          {!googleConnected ? (
            <button className="connect-button" onClick={handleConnectGoogle}>
              Connect
            </button>
          ) : (
            <button className="connect-button" onClick={handleSyncCourses} disabled={syncing}>
              {syncing ? 'Syncing...' : 'Sync Courses'}
            </button>
          )}
        </div>
      </div>

      <div className="dashboard-sections">
        <section className="section teacher-courses-section">
          <div className="section-header">
            <h3>Your Courses</h3>
            <button className="create-custom-btn" onClick={() => setShowCreateModal(true)}>
              + Create Course
            </button>
          </div>
          {courses.length > 0 ? (
            <div className="teacher-courses-grid">
              {courses.map((course) => (
                <div key={course.id} className="teacher-course-card">
                  <h4>{course.name}</h4>
                  {course.subject && <span className="course-subject-tag">{course.subject}</span>}
                  {course.description && (
                    <p className="course-desc">{course.description}</p>
                  )}
                  {course.google_classroom_id && (
                    <span className="google-badge">Google Classroom</span>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <p>No courses yet</p>
              <small>
                Create a course manually{googleConnected
                  ? ' or click "Sync Courses" to import from Google Classroom'
                  : ' or connect Google Classroom to sync your courses'}
              </small>
              <div style={{ display: 'flex', gap: '8px', justifyContent: 'center', marginTop: '12px' }}>
                <button className="connect-button" onClick={() => setShowCreateModal(true)}>
                  + Create Course
                </button>
                {googleConnected && (
                  <button className="connect-button" onClick={handleSyncCourses} disabled={syncing}>
                    {syncing ? 'Syncing...' : 'Sync Courses'}
                  </button>
                )}
              </div>
            </div>
          )}
        </section>
      </div>
      {/* Create Course Modal */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={closeCreateModal}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Create Course</h2>
            <div className="modal-form">
              <label>
                Course Name *
                <input
                  type="text"
                  value={courseName}
                  onChange={(e) => { setCourseName(e.target.value); setCreateError(''); }}
                  placeholder="e.g. Algebra I"
                  disabled={createLoading}
                  onKeyDown={(e) => e.key === 'Enter' && handleCreateCourse()}
                />
              </label>
              <label>
                Subject
                <input
                  type="text"
                  value={courseSubject}
                  onChange={(e) => setCourseSubject(e.target.value)}
                  placeholder="e.g. Mathematics"
                  disabled={createLoading}
                />
              </label>
              <label>
                Description
                <textarea
                  value={courseDescription}
                  onChange={(e) => setCourseDescription(e.target.value)}
                  placeholder="Brief description of the course..."
                  rows={3}
                  disabled={createLoading}
                />
              </label>
              {createError && <p className="link-error">{createError}</p>}
            </div>
            <div className="modal-actions">
              <button className="cancel-btn" onClick={closeCreateModal} disabled={createLoading}>
                Cancel
              </button>
              <button
                className="generate-btn"
                onClick={handleCreateCourse}
                disabled={createLoading || !courseName.trim()}
              >
                {createLoading ? 'Creating...' : 'Create Course'}
              </button>
            </div>
          </div>
        </div>
      )}
      {/* Invite Parent Modal */}
      {showInviteParentModal && (
        <div className="modal-overlay" onClick={closeInviteParentModal}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Invite Parent</h2>
            <p style={{ color: 'var(--color-ink-muted)', fontSize: '14px', margin: '0 0 16px' }}>
              Send an email invitation to a parent to join ClassBridge and link with their child.
            </p>
            <div className="modal-form">
              <label>
                Parent Email *
                <input
                  type="email"
                  value={inviteParentEmail}
                  onChange={(e) => { setInviteParentEmail(e.target.value); setInviteError(''); setInviteSuccess(''); }}
                  placeholder="parent@example.com"
                  disabled={inviteLoading}
                />
              </label>
              <label>
                Student *
                <select
                  value={inviteStudentId ?? ''}
                  onChange={(e) => setInviteStudentId(e.target.value ? Number(e.target.value) : null)}
                  disabled={inviteLoading}
                >
                  <option value="">Select a student...</option>
                  {students.map((s) => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
              </label>
              {inviteError && <p className="link-error">{inviteError}</p>}
              {inviteSuccess && <p className="link-success">{inviteSuccess}</p>}
            </div>
            <div className="modal-actions">
              <button className="cancel-btn" onClick={closeInviteParentModal} disabled={inviteLoading}>
                {inviteSuccess ? 'Close' : 'Cancel'}
              </button>
              <button
                className="generate-btn"
                onClick={handleInviteParent}
                disabled={inviteLoading || !inviteParentEmail.trim() || !inviteStudentId}
              >
                {inviteLoading ? 'Sending...' : 'Send Invitation'}
              </button>
            </div>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
