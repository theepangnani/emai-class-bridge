# Task Manager & Calendar

## Overview
A personal task/todo manager and visual calendar for all EMAI users. Provides a unified view of upcoming deadlines and personal tasks with role-aware data sources and one-way push to Google Calendar. The calendar is built with **custom React components** (no external calendar library).

## Data Model

### `tasks` Table
See `task-management.md` for full data model, schemas, and CRUD details.

Key fields: `created_by_user_id`, `assigned_to_user_id`, `title`, `due_date`, `priority` (low/medium/high), `is_completed`, `archived_at`, `category`, `linked_assignment_id`.

## Role-Aware Calendar Data Sources

### Student
```
Calendar Items = user's tasks + assignments from student_courses
```

### Parent
```
Calendar Items = user's tasks + children's assignments (filtered by selected child)
```
- Child selector tabs filter which child's assignments appear on the calendar
- Tasks are always the parent's own tasks (not filtered by child)

### Teacher
```
Calendar Items = user's tasks + assignment deadlines for courses they teach
```

### Admin
```
Calendar Items = user's tasks only
```

## API Endpoints

### Task CRUD (all authenticated users)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/tasks/` | GET | List tasks with filters (status, priority, date range, include_archived) |
| `/api/tasks/` | POST | Create a new task (with optional cross-role assignment) |
| `/api/tasks/{id}` | PATCH | Update task (creator: all fields; assignee: completion only) |
| `/api/tasks/{id}` | DELETE | Soft-delete (archive) task |
| `/api/tasks/{id}/restore` | PATCH | Restore archived task |
| `/api/tasks/{id}/permanent` | DELETE | Permanently delete (must be archived first) |
| `/api/tasks/assignable-users` | GET | List users the current user can assign tasks to |

### Calendar (all authenticated users)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/calendar/events` | GET | Get calendar events for date range (role-aware) |
| `/api/calendar/google-sync` | POST | Push a task/reminder to Google Calendar |

## Visual Calendar — Custom Components

The calendar is built entirely with custom React components in `frontend/src/components/calendar/`. **No external calendar library is used.**

### Views
- **Month view**: 7-column grid with day cells showing item chips + "+N more" overflow
- **Week view**: 7-column layout with stacked assignment/task cards
- **3-Day view**: 3-column layout (same component as week view)
- **Day view**: Single-column list of items

### Calendar Component Tree
```
CalendarView (orchestrator)
├── CalendarHeader (navigation, view toggle)
├── CalendarMonthGrid
│   └── CalendarDayCell (per day, with drag-drop target)
│       └── CalendarEntry (chip format)
├── CalendarWeekGrid (week + 3-day views, with drag-drop targets)
│   └── CalendarEntry (card format)
├── CalendarDayGrid (day view)
│   └── CalendarEntry (card format)
└── CalendarEntryPopover (click detail overlay)
```

### Drag-and-Drop Task Rescheduling (#118 — Implemented)
Tasks can be dragged between calendar cells to reschedule them using native HTML5 Drag and Drop API.

- **Drag source**: `CalendarEntry` — only tasks (`itemType === 'task'`) are draggable
- **Drop targets**: `CalendarDayCell` (month), `CalendarWeekGrid` column bodies (week/3-day)
- **Data transfer**: `{ id: calendarId, itemType: 'task' }` as JSON in `text/plain`
- **Optimistic UI**: Task moves immediately, reverts on API failure
- **ID offset**: Tasks use `id + 1_000_000` in calendar IDs to avoid collisions with assignment IDs
- **Visual feedback**: Grab cursor on tasks, blue dashed outline on drop targets, opacity on dragging source

### UI Components
- Event items: color-coded chips/cards — assignments use course color (solid border), tasks use priority color (dashed border)
- Click event: `CalendarEntryPopover` with title, course, due time, description, "Create Study Guide" action
- Day detail modal: Opens on day click — lists assignments + tasks as sticky note cards, inline add task
- Filter: child selector tabs (parent view) filter assignments by child

### Key Types (`calendar/types.ts`)
```typescript
interface CalendarAssignment {
  id: number; title: string; description: string | null;
  courseId: number; courseName: string; courseColor: string;
  dueDate: Date; childName: string; maxPoints: number | null;
  itemType?: 'assignment' | 'task';
  priority?: 'low' | 'medium' | 'high';
  isCompleted?: boolean;
}
type CalendarViewMode = 'day' | '3day' | 'week' | 'month';
```

## Google Calendar Push Integration

### Flow
1. User creates/updates a task with `sync_to_google=True`
2. Backend checks user has Google OAuth tokens
3. Uses Google Calendar API to create/update an event
4. Stores `google_calendar_event_id` on the task
5. On task deletion: delete the Google Calendar event

### Requirements
- `google-api-python-client` scope for `https://www.googleapis.com/auth/calendar.events`
- Existing Google OAuth scopes need to include calendar access

## Key Files

### Backend
| File | Purpose |
|------|---------|
| `app/models/task.py` | Task SQLAlchemy model |
| `app/api/routes/tasks.py` | Task CRUD endpoints |
| `app/api/routes/calendar.py` | Calendar events endpoint |
| `app/schemas/task.py` | Task request/response schemas |
| `app/schemas/calendar.py` | Calendar event schemas |

### Frontend
| File | Purpose |
|------|---------|
| `frontend/src/components/calendar/CalendarView.tsx` | Main calendar orchestrator |
| `frontend/src/components/calendar/CalendarHeader.tsx` | Nav + view toggle |
| `frontend/src/components/calendar/CalendarMonthGrid.tsx` | Month grid layout |
| `frontend/src/components/calendar/CalendarDayCell.tsx` | Single day cell (drag-drop target) |
| `frontend/src/components/calendar/CalendarWeekGrid.tsx` | Week/3-day layout (drag-drop targets) |
| `frontend/src/components/calendar/CalendarDayGrid.tsx` | Day list layout |
| `frontend/src/components/calendar/CalendarEntry.tsx` | Assignment/task chip or card (drag source for tasks) |
| `frontend/src/components/calendar/CalendarEntryPopover.tsx` | Click detail popover |
| `frontend/src/components/calendar/useCalendarNav.ts` | Navigation hook |
| `frontend/src/components/calendar/types.ts` | Shared types, color palette, date utilities |
| `frontend/src/components/calendar/Calendar.css` | All calendar styles including drag-and-drop |
| `frontend/src/pages/ParentDashboard.tsx` | Calendar integration, handleTaskDrop, day detail modal |
| `frontend/src/pages/TasksPage.tsx` | Dedicated full-CRUD tasks page |
| `frontend/src/api/client.ts` | `tasksApi`, `calendarApi` methods |

## Implementation Notes
- The calendar is accessible from all dashboards via nav link — it's a shared feature, not role-specific
- Tasks belong to users, not roles — the role determines what *additional* items (assignments) appear
- Assignment items on the calendar are read-only (can't edit assignment due dates from the calendar)
- Tasks are draggable to reschedule; assignments are not draggable
- Google Calendar sync is optional — the calendar works fully without Google
- See `task-management.md` for full task CRUD, archival, cross-role assignment, and reminder details
