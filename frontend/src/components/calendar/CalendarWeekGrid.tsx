import { useMemo, useState } from 'react';
import { CalendarEntry } from './CalendarEntry';
import type { CalendarAssignment } from './types';
import { dateKey, isSameDay } from './types';

interface CalendarWeekGridProps {
  dates: Date[];
  assignments: CalendarAssignment[];
  onAssignmentClick: (assignment: CalendarAssignment, anchorRect: DOMRect) => void;
  onTaskDrop?: (assignmentId: number, newDate: Date) => void;
}

const DAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

export function CalendarWeekGrid({ dates, assignments, onAssignmentClick, onTaskDrop }: CalendarWeekGridProps) {
  const today = new Date();
  const [dragOverCol, setDragOverCol] = useState<number | null>(null);

  const assignmentsByDate = useMemo(() => {
    const map = new Map<string, CalendarAssignment[]>();
    for (const a of assignments) {
      const key = dateKey(a.dueDate);
      const list = map.get(key) || [];
      list.push(a);
      map.set(key, list);
    }
    return map;
  }, [assignments]);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = (e: React.DragEvent, date: Date) => {
    e.preventDefault();
    setDragOverCol(null);
    try {
      const data = JSON.parse(e.dataTransfer.getData('text/plain'));
      if (data.itemType === 'task' && onTaskDrop) {
        onTaskDrop(data.id, date);
      }
    } catch {
      // Invalid drag data
    }
  };

  return (
    <div className="cal-week-grid" style={{ gridTemplateColumns: `repeat(${dates.length}, 1fr)` }}>
      {dates.map((date, i) => {
        const isToday = isSameDay(date, today);
        const dayAssignments = assignmentsByDate.get(dateKey(date)) || [];
        return (
          <div key={i} className="cal-week-column">
            <div className={`cal-week-column-header${isToday ? ' today' : ''}`}>
              <div className="cal-week-day-name">{DAY_NAMES[date.getDay()]}</div>
              <div className={`cal-week-day-num${isToday ? ' today' : ''}`}>{date.getDate()}</div>
            </div>
            <div
              className={`cal-week-column-body${dragOverCol === i ? ' cal-day-drag-over' : ''}`}
              onDragOver={handleDragOver}
              onDragEnter={(e) => { e.preventDefault(); setDragOverCol(i); }}
              onDragLeave={(e) => {
                if (!e.currentTarget.contains(e.relatedTarget as Node)) setDragOverCol(null);
              }}
              onDrop={(e) => handleDrop(e, date)}
            >
              {dayAssignments.length === 0 ? (
                <div className="cal-week-empty" />
              ) : (
                dayAssignments.map(a => (
                  <CalendarEntry
                    key={a.id}
                    assignment={a}
                    variant="card"
                    onClick={(e) => onAssignmentClick(a, (e.currentTarget as HTMLElement).getBoundingClientRect())}
                  />
                ))
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
