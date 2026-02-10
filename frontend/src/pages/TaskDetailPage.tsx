import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { tasksApi, type TaskItem } from '../api/client';
import { DashboardLayout } from '../components/DashboardLayout';
import { useConfirm } from '../components/ConfirmModal';
import './TaskDetailPage.css';

export function TaskDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { confirm, confirmModal } = useConfirm();
  const [task, setTask] = useState<TaskItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const taskId = parseInt(id || '0');

  useEffect(() => {
    if (!taskId) return;
    (async () => {
      try {
        const data = await tasksApi.get(taskId);
        setTask(data);
      } catch {
        setError('Task not found or not accessible');
      } finally {
        setLoading(false);
      }
    })();
  }, [taskId]);

  const handleToggleComplete = async () => {
    if (!task) return;
    try {
      const updated = await tasksApi.update(task.id, { is_completed: !task.is_completed });
      setTask(updated);
    } catch { /* ignore */ }
  };

  const handleDelete = async () => {
    if (!task) return;
    const ok = await confirm({
      title: 'Delete Task',
      message: `Delete "${task.title}"? This cannot be undone.`,
      confirmLabel: 'Delete',
      variant: 'danger',
    });
    if (!ok) return;
    try {
      await tasksApi.delete(task.id);
      navigate('/tasks');
    } catch { /* ignore */ }
  };

  const getStudyGuideRoute = (task: TaskItem): string | null => {
    if (!task.study_guide_id) return null;
    const guideType = task.study_guide_type || 'study_guide';
    if (guideType === 'quiz') return `/study/quiz/${task.study_guide_id}`;
    if (guideType === 'flashcards') return `/study/flashcards/${task.study_guide_id}`;
    return `/study/guide/${task.study_guide_id}`;
  };

  const guideTypeIcon = (type: string | null) => {
    if (type === 'quiz') return '\u2753';
    if (type === 'flashcards') return '\uD83C\uDCCF';
    return '\uD83D\uDCD6';
  };

  const priorityLabel = (p: string | null) => {
    if (p === 'high') return 'High';
    if (p === 'low') return 'Low';
    return 'Medium';
  };

  if (loading) return <DashboardLayout><div className="td-loading">Loading...</div></DashboardLayout>;
  if (error || !task) return (
    <DashboardLayout>
      <div className="td-error">
        <p>{error || 'Task not found'}</p>
        <Link to="/tasks" className="td-back-link">Back to Tasks</Link>
      </div>
    </DashboardLayout>
  );

  const studyGuideRoute = getStudyGuideRoute(task);
  const hasLinkedResources = !!(task.study_guide_id || task.course_content_id || task.course_id);

  return (
    <DashboardLayout>
      <div className="td-page">
        <div className="td-header">
          <Link to="/tasks" className="td-back-link">&larr; Back to Tasks</Link>
        </div>

        {/* Task Info Card */}
        <div className="td-card">
          <div className="td-title-row">
            <button
              className={`td-check${task.is_completed ? ' checked' : ''}`}
              onClick={handleToggleComplete}
              title={task.is_completed ? 'Mark incomplete' : 'Mark complete'}
            >
              {task.is_completed ? '\u2705' : '\u2B1C'}
            </button>
            <h2 className={task.is_completed ? 'td-completed' : ''}>{task.title}</h2>
          </div>

          {task.description && (
            <p className="td-description">{task.description}</p>
          )}

          <div className="td-meta">
            {task.due_date && (
              <div className="td-meta-item">
                <span className="td-meta-label">Due</span>
                <span className="td-meta-value">
                  {new Date(task.due_date).toLocaleDateString(undefined, {
                    weekday: 'short', month: 'short', day: 'numeric', year: 'numeric',
                  })}
                  {' at '}
                  {new Date(task.due_date).toLocaleTimeString(undefined, {
                    hour: 'numeric', minute: '2-digit',
                  })}
                </span>
              </div>
            )}
            <div className="td-meta-item">
              <span className="td-meta-label">Priority</span>
              <span className={`td-priority-badge ${task.priority || 'medium'}`}>
                {priorityLabel(task.priority)}
              </span>
            </div>
            <div className="td-meta-item">
              <span className="td-meta-label">Status</span>
              <span className={`td-status-badge ${task.is_completed ? 'done' : 'pending'}`}>
                {task.is_completed ? 'Completed' : 'Pending'}
              </span>
            </div>
            {task.assignee_name && (
              <div className="td-meta-item">
                <span className="td-meta-label">Assigned to</span>
                <span className="td-meta-value">{task.assignee_name}</span>
              </div>
            )}
            <div className="td-meta-item">
              <span className="td-meta-label">Created by</span>
              <span className="td-meta-value">{task.creator_name}</span>
            </div>
            <div className="td-meta-item">
              <span className="td-meta-label">Created</span>
              <span className="td-meta-value">
                {new Date(task.created_at).toLocaleDateString()}
              </span>
            </div>
          </div>

          <div className="td-actions">
            <button className="td-action-btn" onClick={handleToggleComplete}>
              {task.is_completed ? 'Mark Incomplete' : 'Mark Complete'}
            </button>
            <button className="td-action-btn danger" onClick={handleDelete}>
              Delete
            </button>
          </div>
        </div>

        {/* Linked Resources */}
        {hasLinkedResources && (
          <div className="td-section">
            <h3>Linked Resources</h3>
            <div className="td-resources">
              {task.study_guide_id && studyGuideRoute && (
                <Link to={studyGuideRoute} className="td-resource-card">
                  <span className="td-resource-icon">{guideTypeIcon(task.study_guide_type)}</span>
                  <div className="td-resource-info">
                    <span className="td-resource-type">
                      {task.study_guide_type === 'quiz' ? 'Quiz' : task.study_guide_type === 'flashcards' ? 'Flashcards' : 'Study Guide'}
                    </span>
                    <span className="td-resource-title">{task.study_guide_title}</span>
                  </div>
                  <span className="td-resource-arrow">&rarr;</span>
                </Link>
              )}
              {task.course_content_id && (
                <Link to={`/study-guides/${task.course_content_id}`} className="td-resource-card">
                  <span className="td-resource-icon">{'\uD83D\uDCC4'}</span>
                  <div className="td-resource-info">
                    <span className="td-resource-type">Course Material</span>
                    <span className="td-resource-title">{task.course_content_title || 'View Material'}</span>
                  </div>
                  <span className="td-resource-arrow">&rarr;</span>
                </Link>
              )}
              {task.course_id && (
                <Link to={`/courses/${task.course_id}`} className="td-resource-card">
                  <span className="td-resource-icon">{'\uD83D\uDCDA'}</span>
                  <div className="td-resource-info">
                    <span className="td-resource-type">Course</span>
                    <span className="td-resource-title">{task.course_name || 'View Course'}</span>
                  </div>
                  <span className="td-resource-arrow">&rarr;</span>
                </Link>
              )}
            </div>
          </div>
        )}

        {!hasLinkedResources && (
          <div className="td-section">
            <h3>Linked Resources</h3>
            <div className="td-empty-resources">
              <p>No study guides or course materials linked to this task.</p>
            </div>
          </div>
        )}
      </div>
      {confirmModal}
    </DashboardLayout>
  );
}
