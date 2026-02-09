import { useState, useEffect } from 'react';
import { parentApi, coursesApi, googleApi, courseContentsApi } from '../api/client';
import type { ChildSummary, ChildOverview, CourseContentItem } from '../api/client';
import { DashboardLayout } from '../components/DashboardLayout';
import { getCourseColor } from '../components/calendar/types';
import './CoursesPage.css';

interface ParentCourse {
  id: number;
  name: string;
  description: string | null;
  subject: string | null;
  created_at: string;
}

type SyncState = 'idle' | 'syncing' | 'done' | 'error';

const CONTENT_TYPES = [
  { value: 'notes', label: 'Notes' },
  { value: 'syllabus', label: 'Syllabus' },
  { value: 'labs', label: 'Labs' },
  { value: 'assignments', label: 'Assignments' },
  { value: 'readings', label: 'Readings' },
  { value: 'resources', label: 'Resources' },
  { value: 'other', label: 'Other' },
];

export function CoursesPage() {
  const [children, setChildren] = useState<ChildSummary[]>([]);
  const [selectedChild, setSelectedChild] = useState<number | null>(null);
  const [childOverview, setChildOverview] = useState<ChildOverview | null>(null);
  const [parentCourses, setParentCourses] = useState<ParentCourse[]>([]);
  const [loading, setLoading] = useState(true);
  const [overviewLoading, setOverviewLoading] = useState(false);
  const [googleConnected, setGoogleConnected] = useState(false);

  // Sync state
  const [syncState, setSyncState] = useState<SyncState>('idle');
  const [syncMessage, setSyncMessage] = useState('');

  // Create course modal
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [courseName, setCourseName] = useState('');
  const [courseSubject, setCourseSubject] = useState('');
  const [courseDescription, setCourseDescription] = useState('');
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState('');

  // Assign course modal
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [selectedCoursesForAssign, setSelectedCoursesForAssign] = useState<Set<number>>(new Set());
  const [assignLoading, setAssignLoading] = useState(false);

  // Course content state
  const [expandedCourseId, setExpandedCourseId] = useState<number | null>(null);
  const [courseContents, setCourseContents] = useState<Record<number, CourseContentItem[]>>({});
  const [contentsLoading, setContentsLoading] = useState<number | null>(null);

  // Add/Edit content modal
  const [showContentModal, setShowContentModal] = useState(false);
  const [editingContent, setEditingContent] = useState<CourseContentItem | null>(null);
  const [contentTitle, setContentTitle] = useState('');
  const [contentDescription, setContentDescription] = useState('');
  const [contentType, setContentType] = useState('notes');
  const [referenceUrl, setReferenceUrl] = useState('');
  const [googleClassroomUrl, setGoogleClassroomUrl] = useState('');
  const [contentCourseId, setContentCourseId] = useState<number | null>(null);
  const [contentSaving, setContentSaving] = useState(false);
  const [contentError, setContentError] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (selectedChild) loadChildOverview(selectedChild);
  }, [selectedChild]);

  const loadData = async () => {
    try {
      const [childrenData, courses] = await Promise.all([
        parentApi.getChildren(),
        coursesApi.createdByMe(),
      ]);
      setChildren(childrenData);
      setParentCourses(courses);
      if (childrenData.length > 0) {
        setSelectedChild(childrenData[0].student_id);
      }
      try {
        const status = await googleApi.getStatus();
        setGoogleConnected(status.connected);
      } catch { /* ignore */ }
    } catch { /* ignore */ } finally {
      setLoading(false);
    }
  };

  const loadChildOverview = async (studentId: number) => {
    setOverviewLoading(true);
    try {
      const data = await parentApi.getChildOverview(studentId);
      setChildOverview(data);
    } catch {
      setChildOverview(null);
    } finally {
      setOverviewLoading(false);
    }
  };

  const handleCreateCourse = async () => {
    if (!courseName.trim()) return;
    setCreateError('');
    setCreateLoading(true);
    try {
      await coursesApi.create({
        name: courseName.trim(),
        subject: courseSubject.trim() || undefined,
        description: courseDescription.trim() || undefined,
      });
      closeCreateModal();
      const courses = await coursesApi.createdByMe();
      setParentCourses(courses);
      if (selectedChild) loadChildOverview(selectedChild);
    } catch (err: any) {
      setCreateError(err.response?.data?.detail || 'Failed to create course');
    } finally {
      setCreateLoading(false);
    }
  };

  const closeCreateModal = () => {
    setShowCreateModal(false);
    setCourseName('');
    setCourseSubject('');
    setCourseDescription('');
    setCreateError('');
  };

  const handleAssignCourses = async () => {
    if (!selectedChild || selectedCoursesForAssign.size === 0) return;
    setAssignLoading(true);
    try {
      await parentApi.assignCoursesToChild(selectedChild, Array.from(selectedCoursesForAssign));
      setShowAssignModal(false);
      setSelectedCoursesForAssign(new Set());
      loadChildOverview(selectedChild);
    } catch { /* ignore */ } finally {
      setAssignLoading(false);
    }
  };

  const handleSyncCourses = async () => {
    if (!selectedChild) return;
    setSyncState('syncing');
    setSyncMessage('');
    try {
      const result = await parentApi.syncChildCourses(selectedChild);
      setSyncMessage(result.message);
      setSyncState('done');
      loadChildOverview(selectedChild);
      setTimeout(() => { setSyncState('idle'); setSyncMessage(''); }, 4000);
    } catch (err: any) {
      setSyncMessage(err.response?.data?.detail || 'Failed to sync courses');
      setSyncState('error');
      setTimeout(() => { setSyncState('idle'); setSyncMessage(''); }, 4000);
    }
  };

  // Course content handlers
  const loadCourseContents = async (courseId: number) => {
    setContentsLoading(courseId);
    try {
      const items = await courseContentsApi.list(courseId);
      setCourseContents(prev => ({ ...prev, [courseId]: items }));
    } catch { /* ignore */ } finally {
      setContentsLoading(null);
    }
  };

  const handleToggleCourseExpand = (courseId: number) => {
    if (expandedCourseId === courseId) {
      setExpandedCourseId(null);
    } else {
      setExpandedCourseId(courseId);
      if (!courseContents[courseId]) {
        loadCourseContents(courseId);
      }
    }
  };

  const openAddContentModal = (courseId: number) => {
    setContentCourseId(courseId);
    setEditingContent(null);
    setContentTitle('');
    setContentDescription('');
    setContentType('notes');
    setReferenceUrl('');
    setGoogleClassroomUrl('');
    setContentError('');
    setShowContentModal(true);
  };

  const openEditContentModal = (item: CourseContentItem) => {
    setContentCourseId(item.course_id);
    setEditingContent(item);
    setContentTitle(item.title);
    setContentDescription(item.description || '');
    setContentType(item.content_type);
    setReferenceUrl(item.reference_url || '');
    setGoogleClassroomUrl(item.google_classroom_url || '');
    setContentError('');
    setShowContentModal(true);
  };

  const closeContentModal = () => {
    setShowContentModal(false);
    setEditingContent(null);
    setContentTitle('');
    setContentDescription('');
    setContentType('notes');
    setReferenceUrl('');
    setGoogleClassroomUrl('');
    setContentError('');
    setContentCourseId(null);
  };

  const handleSaveContent = async () => {
    if (!contentTitle.trim() || !contentCourseId) return;
    setContentSaving(true);
    setContentError('');
    try {
      if (editingContent) {
        await courseContentsApi.update(editingContent.id, {
          title: contentTitle.trim(),
          description: contentDescription.trim() || undefined,
          content_type: contentType,
          reference_url: referenceUrl.trim() || undefined,
          google_classroom_url: googleClassroomUrl.trim() || undefined,
        });
      } else {
        await courseContentsApi.create({
          course_id: contentCourseId,
          title: contentTitle.trim(),
          description: contentDescription.trim() || undefined,
          content_type: contentType,
          reference_url: referenceUrl.trim() || undefined,
          google_classroom_url: googleClassroomUrl.trim() || undefined,
        });
      }
      closeContentModal();
      loadCourseContents(contentCourseId);
    } catch (err: any) {
      setContentError(err.response?.data?.detail || 'Failed to save content');
    } finally {
      setContentSaving(false);
    }
  };

  const handleDeleteContent = async (contentId: number, courseId: number) => {
    if (!window.confirm('Delete this content item?')) return;
    try {
      await courseContentsApi.delete(contentId);
      loadCourseContents(courseId);
    } catch { /* ignore */ }
  };

  const childName = childOverview?.full_name || children.find(c => c.student_id === selectedChild)?.full_name || '';
  const courseIds = (childOverview?.courses || []).map(c => c.id);

  const renderContentPanel = (courseId: number) => {
    if (expandedCourseId !== courseId) return null;
    const items = courseContents[courseId] || [];
    return (
      <div className="course-content-panel">
        <div className="course-content-header">
          <h5>Course Content</h5>
          <button className="courses-btn secondary" onClick={(e) => { e.stopPropagation(); openAddContentModal(courseId); }}>
            + Add Content
          </button>
        </div>
        {contentsLoading === courseId ? (
          <div className="loading-state" style={{ padding: '12px 0', fontSize: 13 }}>Loading content...</div>
        ) : items.length === 0 ? (
          <div className="course-content-empty">
            <p>No content items yet. Add notes, links, or resources.</p>
          </div>
        ) : (
          <div className="course-content-list">
            {items.map((item) => (
              <div key={item.id} className="content-item">
                <div className="content-item-info">
                  <span className={`content-type-badge ${item.content_type}`}>
                    {CONTENT_TYPES.find(t => t.value === item.content_type)?.label || item.content_type}
                  </span>
                  <span className="content-item-title">{item.title}</span>
                  {item.description && <p className="content-item-desc">{item.description}</p>}
                </div>
                <div className="content-item-links">
                  {item.reference_url && (
                    <a href={item.reference_url} target="_blank" rel="noopener noreferrer" className="content-link" onClick={(e) => e.stopPropagation()}>
                      Link
                    </a>
                  )}
                  {item.google_classroom_url && (
                    <a href={item.google_classroom_url} target="_blank" rel="noopener noreferrer" className="content-link google" onClick={(e) => e.stopPropagation()}>
                      Google
                    </a>
                  )}
                </div>
                <div className="content-item-actions">
                  <button className="content-action-btn" onClick={(e) => { e.stopPropagation(); openEditContentModal(item); }}>Edit</button>
                  <button className="content-action-btn danger" onClick={(e) => { e.stopPropagation(); handleDeleteContent(item.id, courseId); }}>Delete</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <DashboardLayout welcomeSubtitle="Manage courses">
        <div className="loading-state">Loading...</div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout
      welcomeSubtitle="Manage courses"
      sidebarActions={[
        { label: '+ Add Course', onClick: () => setShowCreateModal(true) },
      ]}
    >
      <div className="courses-page">
        {/* Child selector */}
        {children.length > 1 && (
          <div className="child-selector" style={{ marginBottom: 20 }}>
            {children.map((child) => (
              <button
                key={child.student_id}
                className={`child-tab ${selectedChild === child.student_id ? 'active' : ''}`}
                onClick={() => setSelectedChild(child.student_id)}
              >
                {child.full_name}
              </button>
            ))}
          </div>
        )}

        {/* Child's courses */}
        <div className="courses-section">
          <div className="courses-section-header">
            <h3>{childName ? `${childName}'s Courses` : 'Courses'}</h3>
            <div className="courses-header-actions">
              <button className="generate-btn" onClick={() => setShowCreateModal(true)}>
                + Create Course
              </button>
              {parentCourses.length > 0 && selectedChild && (
                <button className="courses-btn secondary" onClick={() => { setSelectedCoursesForAssign(new Set()); setShowAssignModal(true); }}>
                  Assign Course
                </button>
              )}
              {googleConnected && childOverview?.google_connected && (
                <button className="courses-btn secondary" onClick={handleSyncCourses} disabled={syncState === 'syncing'}>
                  {syncState === 'syncing' ? 'Syncing...' : 'Sync Google'}
                </button>
              )}
            </div>
          </div>
          {syncMessage && (
            <div className={`courses-sync-msg ${syncState === 'error' ? 'error' : ''}`}>{syncMessage}</div>
          )}
          {overviewLoading ? (
            <div className="loading-state">Loading courses...</div>
          ) : childOverview && childOverview.courses.length > 0 ? (
            <div className="courses-grid">
              {childOverview.courses.map((course) => (
                <div key={course.id} className="course-card-wrapper">
                  <div
                    className={`course-card ${expandedCourseId === course.id ? 'expanded' : ''}`}
                    onClick={() => handleToggleCourseExpand(course.id)}
                    style={{ cursor: 'pointer' }}
                  >
                    <div className="course-card-color" style={{ background: getCourseColor(course.id, courseIds) }} />
                    <div className="course-card-body">
                      <h4>{course.name}</h4>
                      {course.subject && <span className="course-card-subject">{course.subject}</span>}
                      {course.teacher_name && <span className="course-card-teacher">{course.teacher_name}</span>}
                      {course.google_classroom_id && <span className="course-card-badge google">Google</span>}
                      <span className="course-card-expand">{expandedCourseId === course.id ? '\u25BE' : '\u25B8'}</span>
                    </div>
                  </div>
                  {renderContentPanel(course.id)}
                </div>
              ))}
            </div>
          ) : (
            <div className="courses-empty">
              <p>No courses yet. Create a course or sync from Google Classroom.</p>
            </div>
          )}
        </div>

        {/* Parent-created courses */}
        {parentCourses.length > 0 && (
          <div className="courses-section">
            <h3>My Created Courses</h3>
            <div className="courses-grid">
              {parentCourses.map((course) => (
                <div key={course.id} className="course-card-wrapper">
                  <div
                    className={`course-card ${expandedCourseId === course.id ? 'expanded' : ''}`}
                    onClick={() => handleToggleCourseExpand(course.id)}
                    style={{ cursor: 'pointer' }}
                  >
                    <div className="course-card-color" style={{ background: 'var(--color-accent)' }} />
                    <div className="course-card-body">
                      <h4>{course.name}</h4>
                      {course.subject && <span className="course-card-subject">{course.subject}</span>}
                      {course.description && <p className="course-card-desc">{course.description}</p>}
                      <span className="course-card-expand">{expandedCourseId === course.id ? '\u25BE' : '\u25B8'}</span>
                    </div>
                  </div>
                  {renderContentPanel(course.id)}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Create Course Modal */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={closeCreateModal}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Create Course</h2>
            <p className="modal-desc">Create a course for your child. No teacher or school required.</p>
            <div className="modal-form">
              <label>
                Course Name *
                <input type="text" value={courseName} onChange={(e) => setCourseName(e.target.value)} placeholder="e.g. Math Grade 5" disabled={createLoading} onKeyDown={(e) => e.key === 'Enter' && handleCreateCourse()} />
              </label>
              <label>
                Subject (optional)
                <input type="text" value={courseSubject} onChange={(e) => setCourseSubject(e.target.value)} placeholder="e.g. Mathematics" disabled={createLoading} />
              </label>
              <label>
                Description (optional)
                <textarea value={courseDescription} onChange={(e) => setCourseDescription(e.target.value)} placeholder="Course details..." rows={3} disabled={createLoading} />
              </label>
              {createError && <p className="link-error">{createError}</p>}
            </div>
            <div className="modal-actions">
              <button className="cancel-btn" onClick={closeCreateModal} disabled={createLoading}>Cancel</button>
              <button className="generate-btn" onClick={handleCreateCourse} disabled={createLoading || !courseName.trim()}>
                {createLoading ? 'Creating...' : 'Create Course'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Assign Course to Child Modal */}
      {showAssignModal && selectedChild && (
        <div className="modal-overlay" onClick={() => setShowAssignModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Assign Course to {childName}</h2>
            <p className="modal-desc">Select courses to assign to your child.</p>
            <div className="modal-form">
              {parentCourses.length === 0 ? (
                <div className="empty-state">
                  <p>No courses created yet</p>
                  <button className="link-child-btn-small" onClick={() => { setShowAssignModal(false); setShowCreateModal(true); }}>+ Create Course</button>
                </div>
              ) : (
                <div className="discovered-list">
                  {parentCourses.map((course) => {
                    const alreadyAssigned = childOverview?.courses.some(c => c.id === course.id) ?? false;
                    return (
                      <label key={course.id} className={`discovered-item ${alreadyAssigned ? 'disabled' : ''}`}>
                        <input type="checkbox" checked={selectedCoursesForAssign.has(course.id)} onChange={() => { setSelectedCoursesForAssign(prev => { const next = new Set(prev); if (next.has(course.id)) next.delete(course.id); else next.add(course.id); return next; }); }} disabled={alreadyAssigned} />
                        <div className="discovered-info">
                          <span className="discovered-name">{course.name}</span>
                          {course.subject && <span className="discovered-email">{course.subject}</span>}
                          {alreadyAssigned && <span className="discovered-linked-badge">Already assigned</span>}
                        </div>
                      </label>
                    );
                  })}
                </div>
              )}
            </div>
            <div className="modal-actions">
              <button className="cancel-btn" onClick={() => setShowAssignModal(false)} disabled={assignLoading}>Cancel</button>
              <button className="generate-btn" onClick={handleAssignCourses} disabled={assignLoading || selectedCoursesForAssign.size === 0}>
                {assignLoading ? 'Assigning...' : `Assign ${selectedCoursesForAssign.size} Course${selectedCoursesForAssign.size !== 1 ? 's' : ''}`}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add/Edit Content Modal */}
      {showContentModal && (
        <div className="modal-overlay" onClick={closeContentModal}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>{editingContent ? 'Edit Content' : 'Add Content'}</h2>
            <p className="modal-desc">Add a reference link or resource to this course.</p>
            <div className="modal-form">
              <label>
                Title *
                <input type="text" value={contentTitle} onChange={(e) => setContentTitle(e.target.value)} placeholder="e.g. Chapter 5 Notes" disabled={contentSaving} onKeyDown={(e) => e.key === 'Enter' && handleSaveContent()} />
              </label>
              <label>
                Type
                <select value={contentType} onChange={(e) => setContentType(e.target.value)} disabled={contentSaving}>
                  {CONTENT_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </label>
              <label>
                Description (optional)
                <textarea value={contentDescription} onChange={(e) => setContentDescription(e.target.value)} placeholder="Brief description..." rows={2} disabled={contentSaving} />
              </label>
              <label>
                Reference URL (optional)
                <input type="url" value={referenceUrl} onChange={(e) => setReferenceUrl(e.target.value)} placeholder="https://..." disabled={contentSaving} />
              </label>
              <label>
                Google Classroom URL (optional)
                <input type="url" value={googleClassroomUrl} onChange={(e) => setGoogleClassroomUrl(e.target.value)} placeholder="https://classroom.google.com/..." disabled={contentSaving} />
              </label>
              {contentError && <p className="link-error">{contentError}</p>}
            </div>
            <div className="modal-actions">
              <button className="cancel-btn" onClick={closeContentModal} disabled={contentSaving}>Cancel</button>
              <button className="generate-btn" onClick={handleSaveContent} disabled={contentSaving || !contentTitle.trim()}>
                {contentSaving ? 'Saving...' : editingContent ? 'Save Changes' : 'Add Content'}
              </button>
            </div>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
