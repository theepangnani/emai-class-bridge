# Task Management System

## Overview
ClassBridge includes a cross-role task manager integrated into the calendar. Any authenticated user can create tasks and optionally assign them to related users. Tasks appear alongside assignments on the calendar with distinct visual treatment. A dedicated `/tasks` page provides full CRUD management.

## Cross-Role Task Assignment

| Creator Role | Can Assign To | Relationship Check |
|-------------|---------------|-------------------|
| **Parent** | Linked children (students) | `parent_students` join table |
| **Teacher** | Students in their courses | `courses` + `student_courses` enrollment |
| **Student** | Linked parents | `parent_students` join table (reverse) |
| **Admin** | Self only | N/A |

- Assigned tasks appear in both creator's and assignee's task lists
- Assignee can view and complete but not edit/delete
- Creator can edit, reassign, or delete

## Data Model

### `tasks` Table
```python
class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_to_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    reminder_at = Column(DateTime(timezone=True), nullable=True)
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    priority = Column(Enum(TaskPriority), default=TaskPriority.MEDIUM)
    category = Column(String(50), nullable=True)
    linked_assignment_id = Column(Integer, ForeignKey("assignments.id"), nullable=True)
    google_calendar_event_id = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

### Key Relationships
- `created_by_user_id` → User who created the task (any role)
- `assigned_to_user_id` → User the task is assigned to (nullable = personal/self task)
- `linked_assignment_id` → Optional link to an assignment

## API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/tasks/` | GET | Any role | List tasks (creator OR assignee). Filters: assigned_to_user_id, is_completed, priority, include_archived |
| `/api/tasks/` | POST | Any role | Create task (with optional assignment) |
| `/api/tasks/{id}` | PATCH | Any role | Update task (creator: all fields; assignee: completion only) |
| `/api/tasks/{id}` | DELETE | Any role | Soft-delete (archive) task (creator only) |
| `/api/tasks/{id}/restore` | PATCH | Any role | Restore archived task (creator only) |
| `/api/tasks/{id}/permanent` | DELETE | Any role | Permanently delete archived task (creator only) |
| `/api/tasks/assignable-users` | GET | Any role | List users the current user can assign tasks to |

### Relationship Verification on Assignment
When `assigned_to_user_id` is provided, the API verifies:
- **Parent → Student**: `parent_students` where parent_id = current_user.id AND student_id links to assigned user
- **Teacher → Student**: teacher's courses contain the student
- **Student → Parent**: `parent_students` where student has link to assigned parent user

## Pydantic Schemas

### TaskCreate
```python
class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    due_date: datetime | None = None
    assigned_to_user_id: int | None = None
    priority: str = "medium"  # low, medium, high
    category: str | None = None
    linked_assignment_id: int | None = None
```

### TaskUpdate
```python
class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    due_date: datetime | None = None
    assigned_to_user_id: int | None = None
    is_completed: bool | None = None
    priority: str | None = None
    category: str | None = None
```

### TaskResponse
```python
class TaskResponse(BaseModel):
    id: int
    created_by_user_id: int
    assigned_to_user_id: int | None
    title: str
    description: str | None
    due_date: datetime | None
    is_completed: bool
    completed_at: datetime | None
    priority: str
    category: str | None
    creator_name: str
    assignee_name: str | None
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
```

## Reminder System

### How Reminders Work
1. When a task is created/updated with `reminder_at`, schedule an APScheduler job
2. Job ID format: `task_reminder_{task_id}`
3. When the job fires, create an in-app notification for the user
4. If the task is deleted or `reminder_at` is cleared, remove the scheduled job

### Implementation Pattern
```python
from apscheduler.schedulers.background import BackgroundScheduler

def schedule_task_reminder(scheduler: BackgroundScheduler, task: Task):
    job_id = f"task_reminder_{task.id}"
    try:
        scheduler.remove_job(job_id)
    except JobLookupError:
        pass
    if task.reminder_at and not task.is_completed:
        scheduler.add_job(
            send_task_reminder,
            trigger='date',
            run_date=task.reminder_at,
            id=job_id,
            args=[task.id],
        )

def send_task_reminder(task_id: int):
    # Create in-app notification
    pass
```

## Calendar Integration

### How Tasks Appear on Calendar
Tasks with `due_date` appear on the calendar alongside assignments. They use a distinct visual style:

```typescript
interface CalendarAssignment {
  id: number;
  title: string;
  description: string | null;
  courseId: number;
  courseName: string;
  courseColor: string;
  dueDate: Date;
  childName: string;
  maxPoints: number | null;
  itemType?: 'assignment' | 'task';     // distinguishes tasks from assignments
  priority?: 'low' | 'medium' | 'high'; // task priority
  isCompleted?: boolean;                 // task completion state
}
```

### Task Colors (by priority)
```typescript
const TASK_PRIORITY_COLORS = {
  high: '#ef5350',    // red
  medium: '#ff9800',  // orange
  low: '#66bb6a',     // green
};
```

### Visual Distinction
- **Assignments**: Solid left border with course color
- **Tasks**: Dashed left border with priority color
- **Completed tasks**: Strikethrough text + muted opacity

## Task Archival System

Tasks use **soft-delete** (archive) instead of hard-delete. This preserves task history and allows users to restore accidentally deleted tasks.

### How It Works
- **Delete** (`DELETE /api/tasks/{id}`) → Sets `archived_at = now()` instead of removing the row
- **Restore** (`PATCH /api/tasks/{id}/restore`) → Clears `archived_at`, resets `is_completed` to false
- **Permanent Delete** (`DELETE /api/tasks/{id}/permanent`) → Hard-deletes from database (task must be archived first)
- **Auto-Archive on Completion** → When `is_completed` is set to `true`, `archived_at` is also set
- **Un-Archive on Un-Completion** → When `is_completed` is set back to `false`, `archived_at` is cleared

### Listing Behavior
- `GET /api/tasks/` → Returns only **active** tasks (where `archived_at IS NULL`) by default
- `GET /api/tasks/?include_archived=true` → Returns ALL tasks including archived ones

### Frontend (TasksPage)
- Status filter has 4 options: Active, Pending, Completed, Archived
- Selecting "Archived" fetches with `include_archived=true` and filters client-side to only show tasks with `archived_at`
- Archived tasks show dashed border, muted opacity, strikethrough title
- Archived rows show "Restore" (↺) and "Delete Forever" (🗑) buttons instead of Edit/Delete
- Permanent delete prompts `window.confirm` before executing

### Data Model Addition
```python
archived_at = Column(DateTime(timezone=True), nullable=True)
# Index: ix_tasks_archived on archived_at
```

## Drag-and-Drop Task Rescheduling (#118 — Implemented)

Tasks can be dragged between calendar cells to change their due date using native HTML5 Drag and Drop API.

- Only tasks are draggable (not assignments)
- `CalendarEntry` sets `draggable={true}` and `dataTransfer` with `{ id, itemType: 'task' }`
- `CalendarDayCell` and `CalendarWeekGrid` columns are drop targets
- `ParentDashboard.handleTaskDrop()` does optimistic UI update + `PATCH /api/tasks/{id}` with rollback on failure
- Calendar task IDs use `id + 1_000_000` offset to avoid collisions with assignment IDs

See `task-calendar.md` for full calendar drag-and-drop details.

## Day Detail Modal — Sticky Note Cards

When a date is clicked on the calendar, the Day Detail Modal opens. Tasks are displayed as **sticky note cards** with priority-colored left borders and expandable details.

### Sticky Note Visual Treatment
- Each task rendered as a card with:
  - **Priority-colored left border** (4px solid): red (high), orange (medium), green (low)
  - **Tinted background** matching priority color (5% opacity)
  - **Box shadow** for card-like feel
  - **Hover elevation** (shadow increases on hover)
- Completed tasks have reduced opacity (0.5)
- Click anywhere on the card body to **expand/collapse** details

### Expanded View
When a sticky note is clicked, it expands to show:
- Description (if present)
- Due date/time
- Creator name
- Category (if set)

### CSS Classes
- `.task-sticky-note` — Base card styling
- `.task-sticky-note.high` / `.medium` / `.low` — Priority variants
- `.task-sticky-note.completed` — Muted completed state
- `.task-sticky-header` — Checkbox + title + delete button row
- `.task-sticky-detail` — Expandable detail section (animated slide-down)

```
┌─────────────────────────────────────┐
│  February 8, 2026          [Close]  │
│─────────────────────────────────────│
│  ASSIGNMENTS                        │
│  ● Math Homework (Math 5)    [Study]│
│  ● Science Lab Report (Sci)  [Study]│
│                                     │
│  TASKS                              │
│  ┌──────────────────────────────┐   │
│  │▌☐ Review flashcards    [×]   │   │
│  │▌   medium  → Alex            │   │
│  │▌   ─────────────────────     │   │
│  │▌   Due: Feb 8, 3:00 PM      │   │
│  │▌   Created by: Task Parent   │   │
│  └──────────────────────────────┘   │
│  ┌──────────────────────────────┐   │
│  │▌☑ Buy school supplies  [×]   │   │
│  │▌   low                       │   │
│  └──────────────────────────────┘   │
│                                     │
│  [Add a task...              ] [Add]│
└─────────────────────────────────────┘
```

## Key Files

### Backend
| File | Purpose |
|------|---------|
| `app/models/task.py` | Task SQLAlchemy model with cross-role columns |
| `app/schemas/task.py` | Pydantic request/response schemas |
| `app/api/routes/tasks.py` | CRUD router (all roles, relationship verification) |
| `app/api/deps.py` | `get_current_user()` dependency used for auth |
| `main.py` | Mount tasks router under `/api`, lightweight migration |

### Frontend
| File | Purpose |
|------|---------|
| `frontend/src/api/client.ts` | `tasksApi` methods + `TaskItem` interface |
| `frontend/src/pages/TasksPage.tsx` | Dedicated tasks page with full CRUD |
| `frontend/src/pages/ParentDashboard.tsx` | Day Detail Modal, calendar task merging |
| `frontend/src/components/calendar/types.ts` | Extended CalendarAssignment type |
| `frontend/src/components/calendar/CalendarEntry.tsx` | Task visual treatment (dashed border) |
| `frontend/src/components/calendar/CalendarView.tsx` | Accept tasks alongside assignments |
| `frontend/src/components/DashboardLayout.tsx` | Tasks nav item in hamburger menu |
| `frontend/src/App.tsx` | `/tasks` route registration |

## Implementation Order
1. **Backend**: Generalize Task model (created_by_user_id, assigned_to_user_id, priority, category)
2. **Backend**: Update schemas + CRUD router for all roles
3. **Backend**: Lightweight migration in main.py
4. **Frontend**: Update `tasksApi` + `TaskItem` in client.ts
5. **Frontend**: Create TasksPage + register route + add nav
6. **Frontend**: Calendar integration (types, CalendarEntry, ParentDashboard)
7. **Frontend**: Update Day Detail Modal with new fields

## Related Issues
- #104: Cross-role task assignment — backend model & API
- #105: Dedicated Tasks page
- #106: Tasks displayed in calendar
- #107: Task archival (soft-delete, restore, permanent delete, auto-archive on completion)
- #108: Calendar sticky note cards (priority-colored, expandable details)
- #100: Task system backend (original, superseded by #104)
- #101: Day Detail Modal + calendar integration
- #44: Original Task/Todo CRUD issue
