import type { CalendarAssignment } from './types';
import { TASK_PRIORITY_COLORS } from './types';

interface CalendarEntryProps {
  assignment: CalendarAssignment;
  variant: 'chip' | 'card';
  onClick: (e: React.MouseEvent) => void;
}

export function CalendarEntry({ assignment, variant, onClick }: CalendarEntryProps) {
  const isTask = assignment.itemType === 'task';
  const color = isTask
    ? TASK_PRIORITY_COLORS[assignment.priority || 'medium']
    : assignment.courseColor;
  const completedClass = isTask && assignment.isCompleted ? ' cal-entry-completed' : '';

  if (variant === 'chip') {
    return (
      <div
        className={`cal-entry-chip${isTask ? ' cal-entry-task' : ''}${completedClass}`}
        style={{ background: `${color}18` }}
        onClick={onClick}
        title={assignment.title}
      >
        <span className="cal-entry-dot" style={{ background: color }} />
        <span className="cal-entry-chip-title">{assignment.title}</span>
        {assignment.childName && (
          <span className="cal-entry-chip-child">{assignment.childName.split(' ')[0]}</span>
        )}
      </div>
    );
  }

  return (
    <div
      className={`cal-entry-card${isTask ? ' cal-entry-task' : ''}${completedClass}`}
      style={{ borderLeftColor: color }}
      onClick={onClick}
    >
      <div className="cal-entry-title">{assignment.title}</div>
      <div className="cal-entry-meta">
        <span className="cal-entry-dot" style={{ background: color }} />
        {isTask ? (assignment.priority || 'medium') + ' priority' : assignment.courseName}
        {assignment.dueDate && (
          <span className="cal-entry-time">
            {assignment.dueDate.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })}
          </span>
        )}
      </div>
      {assignment.childName && (
        <div className="cal-entry-child">{assignment.childName}</div>
      )}
    </div>
  );
}
