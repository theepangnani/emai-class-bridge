# Task Management System

## Overview
ClassBridge includes a personal task/todo manager integrated into the calendar. Tasks have optional reminders and appear alongside assignments on the calendar. The parent dashboard is the primary consumer in Phase 1; other roles get task support in Phase 1.5.

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
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(Date, nullable=True)
    reminder_at = Column(DateTime(timezone=True), nullable=True)
    is_completed = Column(Boolean, default=False)
    priority = Column(Enum(TaskPriority), default=TaskPriority.MEDIUM)
    category = Column(String(50), nullable=True)
    linked_child_id = Column(Integer, ForeignKey("students.id"), nullable=True)
    linked_assignment_id = Column(Integer, ForeignKey("assignments.id"), nullable=True)
    google_calendar_event_id = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

### Key Relationships
- `user_id` → Owner of the task (any role)
- `linked_child_id` → Optional link to a specific child (parent tasks only)
- `linked_assignment_id` → Optional link to an assignment (student tasks only)

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/tasks/` | GET | List tasks (filters: date_from, date_to, child_id, is_completed, priority) |
| `/api/tasks/` | POST | Create task (with optional reminder) |
| `/api/tasks/{id}` | GET | Get task details |
| `/api/tasks/{id}` | PUT | Update task |
| `/api/tasks/{id}` | DELETE | Delete task |
| `/api/tasks/{id}/complete` | POST | Toggle task completion |
| `/api/tasks/by-date/{date}` | GET | Get all tasks for a specific date |

## Pydantic Schemas

### TaskCreate
```python
class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    due_date: date | None = None
    reminder_at: datetime | None = None
    priority: str = "medium"  # low, medium, high
    category: str | None = None
    linked_child_id: int | None = None
    linked_assignment_id: int | None = None
```

### TaskUpdate
```python
class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    due_date: date | None = None
    reminder_at: datetime | None = None
    is_completed: bool | None = None
    priority: str | None = None
    category: str | None = None
```

### TaskResponse
```python
class TaskResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: str | None
    due_date: date | None
    reminder_at: datetime | None
    is_completed: bool
    priority: str
    category: str | None
    linked_child_id: int | None
    linked_assignment_id: int | None
    created_at: datetime
    updated_at: datetime

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
# In tasks router or service
from apscheduler.schedulers.background import BackgroundScheduler

def schedule_task_reminder(scheduler: BackgroundScheduler, task: Task):
    job_id = f"task_reminder_{task.id}"
    # Remove existing job if any
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
    # notification.title = f"Reminder: {task.title}"
    # notification.message = f"Task due: {task.due_date}"
    pass
```

## Calendar Integration

### How Tasks Appear on Calendar
Tasks with `due_date` appear on the calendar alongside assignments. They use a distinct visual style:

```typescript
// Frontend: CalendarItem type (extends CalendarAssignment)
interface CalendarItem {
  id: number;
  title: string;
  description: string | null;
  courseId: number | null;      // null for tasks
  courseName: string | null;    // null for tasks
  courseColor: string;           // task priority color or neutral
  dueDate: Date;
  childName: string;
  maxPoints: number | null;
  itemType: 'assignment' | 'task';
  priority?: 'low' | 'medium' | 'high';
  isCompleted?: boolean;
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

## Day Detail Modal

When a date is clicked on the calendar, the Day Detail Modal opens:

```
┌─────────────────────────────────────┐
│  February 8, 2026          [Close]  │
│─────────────────────────────────────│
│  ASSIGNMENTS                        │
│  ● Math Homework (Math 5)    3:00pm │
│  ● Science Lab Report (Sci)  EOD    │
│                                     │
│  TASKS                              │
│  ☐ Review flashcards     [Edit][Del]│
│  ☑ Buy school supplies   [Edit][Del]│
│                                     │
│  [+ Add Task]  [+ Create Study Guide]│
└─────────────────────────────────────┘
```

## Key Files

### Backend
| File | Purpose |
|------|---------|
| `app/models/task.py` | Task SQLAlchemy model |
| `app/schemas/task.py` | Pydantic request/response schemas |
| `app/api/routes/tasks.py` | CRUD router |
| `app/jobs/task_reminders.py` | Reminder scheduling logic |
| `main.py` | Mount tasks router under `/api` |

### Frontend
| File | Purpose |
|------|---------|
| `frontend/src/api/client.ts` | `tasksApi` methods (list, create, update, delete, complete, byDate) |
| `frontend/src/components/calendar/DayDetailModal.tsx` | Day detail modal with CRUD |
| `frontend/src/components/TaskModal.tsx` | Add/edit task modal |
| `frontend/src/components/calendar/types.ts` | Updated CalendarItem type |
| `frontend/src/components/calendar/CalendarView.tsx` | Accept tasks alongside assignments |

## Implementation Order
1. **Backend**: Task model → schemas → CRUD router → mount in main.py
2. **Backend**: Reminder scheduling (APScheduler job)
3. **Frontend**: `tasksApi` in client.ts
4. **Frontend**: TaskModal component (add/edit)
5. **Frontend**: Update CalendarView to accept tasks
6. **Frontend**: DayDetailModal component
7. **Frontend**: Wire into ParentDashboard

## Related Issues
- #100: Task system backend
- #101: Day Detail Modal + calendar integration
- #99: Left nav (Add Task button)
- #44: Original Task/Todo CRUD issue (Phase 1.5, now pulled into Phase 1)
