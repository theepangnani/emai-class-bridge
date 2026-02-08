"""Tests for cross-role task system (CRUD, assignment, permissions)."""

import pytest

PASSWORD = "password123!"


def _login(client, email):
    resp = client.post("/api/auth/login", data={"username": email, "password": PASSWORD})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth(client, email):
    return {"Authorization": f"Bearer {_login(client, email)}"}


# ---------------------------------------------------------------------------
# Fixtures — build a family: parent + child (student), a teacher with a course,
# and an unrelated outsider.
# ---------------------------------------------------------------------------

@pytest.fixture()
def users(db_session):
    """Create (or reuse) test users: parent, student (child), teacher, outsider.

    The test DB is session-scoped, so we must not re-insert the same rows.
    """
    from app.core.security import get_password_hash
    from app.models.user import User, UserRole
    from app.models.student import Student, parent_students
    from app.models.teacher import Teacher
    from app.models.course import Course, student_courses

    # Check if users already exist from a previous test
    parent = db_session.query(User).filter(User.email == "taskparent@test.com").first()
    if parent:
        child_user = db_session.query(User).filter(User.email == "taskchild@test.com").first()
        student = db_session.query(Student).filter(Student.user_id == child_user.id).first()
        teacher_user = db_session.query(User).filter(User.email == "taskteacher@test.com").first()
        teacher = db_session.query(Teacher).filter(Teacher.user_id == teacher_user.id).first()
        outsider = db_session.query(User).filter(User.email == "taskoutsider@test.com").first()
        course = db_session.query(Course).filter(Course.name == "Test Math", Course.teacher_id == teacher.id).first()
        return {
            "parent": parent, "child_user": child_user, "student": student,
            "teacher_user": teacher_user, "teacher": teacher, "outsider": outsider, "course": course,
        }

    hashed = get_password_hash(PASSWORD)
    parent = User(email="taskparent@test.com", full_name="Task Parent", role=UserRole.PARENT, hashed_password=hashed)
    child_user = User(email="taskchild@test.com", full_name="Task Child", role=UserRole.STUDENT, hashed_password=hashed)
    teacher_user = User(email="taskteacher@test.com", full_name="Task Teacher", role=UserRole.TEACHER, hashed_password=hashed)
    outsider = User(email="taskoutsider@test.com", full_name="Outsider Parent", role=UserRole.PARENT, hashed_password=hashed)
    db_session.add_all([parent, child_user, teacher_user, outsider])
    db_session.commit()

    student = Student(user_id=child_user.id, grade_level=8)
    db_session.add(student)
    db_session.commit()

    db_session.execute(parent_students.insert().values(parent_id=parent.id, student_id=student.id))
    db_session.commit()

    teacher = Teacher(user_id=teacher_user.id)
    db_session.add(teacher)
    db_session.commit()

    course = Course(name="Test Math", teacher_id=teacher.id)
    db_session.add(course)
    db_session.commit()
    db_session.execute(student_courses.insert().values(student_id=student.id, course_id=course.id))
    db_session.commit()

    return {
        "parent": parent, "child_user": child_user, "student": student,
        "teacher_user": teacher_user, "teacher": teacher, "outsider": outsider, "course": course,
    }


# ===========================================================================
# 1. Basic CRUD — personal tasks (no assignee)
# ===========================================================================

class TestTaskCRUD:
    def test_create_personal_task(self, client, users):
        headers = _auth(client, users["parent"].email)
        resp = client.post("/api/tasks/", json={"title": "Buy school supplies"}, headers=headers)
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["title"] == "Buy school supplies"
        assert body["created_by_user_id"] == users["parent"].id
        assert body["assigned_to_user_id"] is None
        assert body["is_completed"] is False
        assert body["priority"] == "medium"
        assert body["creator_name"] == "Task Parent"
        assert body["assignee_name"] is None

    def test_create_task_with_all_fields(self, client, users):
        headers = _auth(client, users["parent"].email)
        resp = client.post("/api/tasks/", json={
            "title": "Homework review",
            "description": "Check math homework",
            "due_date": "2026-03-01T15:00:00",
            "priority": "high",
            "category": "homework",
        }, headers=headers)
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["priority"] == "high"
        assert body["category"] == "homework"
        assert body["description"] == "Check math homework"
        assert "2026-03-01" in body["due_date"]

    def test_list_tasks_returns_own(self, client, users):
        headers = _auth(client, users["parent"].email)
        # Create a task first
        client.post("/api/tasks/", json={"title": "List test task"}, headers=headers)
        resp = client.get("/api/tasks/", headers=headers)
        assert resp.status_code == 200, resp.text
        titles = [t["title"] for t in resp.json()]
        assert "List test task" in titles

    def test_update_own_task(self, client, users):
        headers = _auth(client, users["parent"].email)
        create = client.post("/api/tasks/", json={"title": "Original title"}, headers=headers)
        task_id = create.json()["id"]

        resp = client.patch(f"/api/tasks/{task_id}", json={"title": "Updated title", "priority": "high"}, headers=headers)
        assert resp.status_code == 200, resp.text
        assert resp.json()["title"] == "Updated title"
        assert resp.json()["priority"] == "high"

    def test_toggle_completion(self, client, users):
        headers = _auth(client, users["parent"].email)
        create = client.post("/api/tasks/", json={"title": "Toggle me"}, headers=headers)
        task_id = create.json()["id"]

        resp = client.patch(f"/api/tasks/{task_id}", json={"is_completed": True}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["is_completed"] is True
        assert resp.json()["completed_at"] is not None

        resp2 = client.patch(f"/api/tasks/{task_id}", json={"is_completed": False}, headers=headers)
        assert resp2.json()["is_completed"] is False
        assert resp2.json()["completed_at"] is None

    def test_delete_own_task(self, client, users):
        headers = _auth(client, users["parent"].email)
        create = client.post("/api/tasks/", json={"title": "Delete me"}, headers=headers)
        task_id = create.json()["id"]

        resp = client.delete(f"/api/tasks/{task_id}", headers=headers)
        assert resp.status_code == 204

        # Verify it's gone
        listing = client.get("/api/tasks/", headers=headers)
        ids = [t["id"] for t in listing.json()]
        assert task_id not in ids

    def test_delete_nonexistent_returns_404(self, client, users):
        headers = _auth(client, users["parent"].email)
        resp = client.delete("/api/tasks/999999", headers=headers)
        assert resp.status_code == 404

    def test_unauthenticated_returns_401(self, client):
        resp = client.get("/api/tasks/")
        assert resp.status_code == 401


# ===========================================================================
# 2. Cross-role assignment: Parent → Child
# ===========================================================================

class TestParentAssignsToChild:
    def test_parent_assigns_task_to_child(self, client, users):
        headers = _auth(client, users["parent"].email)
        resp = client.post("/api/tasks/", json={
            "title": "Do your math homework",
            "assigned_to_user_id": users["child_user"].id,
            "priority": "high",
        }, headers=headers)
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["assigned_to_user_id"] == users["child_user"].id
        assert body["assignee_name"] == "Task Child"

    def test_child_sees_assigned_task(self, client, users):
        parent_headers = _auth(client, users["parent"].email)
        client.post("/api/tasks/", json={
            "title": "Child visible task",
            "assigned_to_user_id": users["child_user"].id,
        }, headers=parent_headers)

        child_headers = _auth(client, users["child_user"].email)
        resp = client.get("/api/tasks/", headers=child_headers)
        assert resp.status_code == 200
        titles = [t["title"] for t in resp.json()]
        assert "Child visible task" in titles

    def test_parent_cannot_assign_to_unlinked_student(self, client, users):
        """Outsider parent has no linked children — assignment should fail."""
        headers = _auth(client, users["outsider"].email)
        resp = client.post("/api/tasks/", json={
            "title": "Should fail",
            "assigned_to_user_id": users["child_user"].id,
        }, headers=headers)
        assert resp.status_code == 403


# ===========================================================================
# 3. Cross-role assignment: Teacher → Student
# ===========================================================================

class TestTeacherAssignsToStudent:
    def test_teacher_assigns_task_to_enrolled_student(self, client, users):
        headers = _auth(client, users["teacher_user"].email)
        resp = client.post("/api/tasks/", json={
            "title": "Read chapter 5",
            "assigned_to_user_id": users["child_user"].id,
        }, headers=headers)
        assert resp.status_code == 201, resp.text
        assert resp.json()["assigned_to_user_id"] == users["child_user"].id

    def test_teacher_cannot_assign_to_non_enrolled_student(self, client, users, db_session):
        """Create a new student NOT in the teacher's course."""
        from app.core.security import get_password_hash
        from app.models.user import User, UserRole
        from app.models.student import Student

        other_student_user = db_session.query(User).filter(User.email == "otherstudent@test.com").first()
        if not other_student_user:
            other_student_user = User(
                email="otherstudent@test.com", full_name="Other Student",
                role=UserRole.STUDENT, hashed_password=get_password_hash(PASSWORD),
            )
            db_session.add(other_student_user)
            db_session.commit()
            other_student = Student(user_id=other_student_user.id, grade_level=9)
            db_session.add(other_student)
            db_session.commit()

        headers = _auth(client, users["teacher_user"].email)
        resp = client.post("/api/tasks/", json={
            "title": "Should fail",
            "assigned_to_user_id": other_student_user.id,
        }, headers=headers)
        assert resp.status_code == 403


# ===========================================================================
# 4. Cross-role assignment: Student → Parent
# ===========================================================================

class TestStudentAssignsToParent:
    def test_student_assigns_task_to_linked_parent(self, client, users):
        headers = _auth(client, users["child_user"].email)
        resp = client.post("/api/tasks/", json={
            "title": "Sign permission slip",
            "assigned_to_user_id": users["parent"].id,
        }, headers=headers)
        assert resp.status_code == 201, resp.text
        assert resp.json()["assigned_to_user_id"] == users["parent"].id
        assert resp.json()["assignee_name"] == "Task Parent"

    def test_student_cannot_assign_to_unlinked_user(self, client, users):
        headers = _auth(client, users["child_user"].email)
        resp = client.post("/api/tasks/", json={
            "title": "Should fail",
            "assigned_to_user_id": users["outsider"].id,
        }, headers=headers)
        assert resp.status_code == 403


# ===========================================================================
# 5. Permission enforcement: assignee vs creator
# ===========================================================================

class TestPermissions:
    def test_assignee_can_toggle_completion(self, client, users):
        parent_headers = _auth(client, users["parent"].email)
        create = client.post("/api/tasks/", json={
            "title": "Toggle by child",
            "assigned_to_user_id": users["child_user"].id,
        }, headers=parent_headers)
        task_id = create.json()["id"]

        child_headers = _auth(client, users["child_user"].email)
        resp = client.patch(f"/api/tasks/{task_id}", json={"is_completed": True}, headers=child_headers)
        assert resp.status_code == 200
        assert resp.json()["is_completed"] is True

    def test_assignee_cannot_edit_title(self, client, users):
        parent_headers = _auth(client, users["parent"].email)
        create = client.post("/api/tasks/", json={
            "title": "No edit for child",
            "assigned_to_user_id": users["child_user"].id,
        }, headers=parent_headers)
        task_id = create.json()["id"]

        child_headers = _auth(client, users["child_user"].email)
        resp = client.patch(f"/api/tasks/{task_id}", json={"title": "Hacked title"}, headers=child_headers)
        assert resp.status_code == 403

    def test_outsider_cannot_see_task(self, client, users):
        parent_headers = _auth(client, users["parent"].email)
        create = client.post("/api/tasks/", json={"title": "Private task"}, headers=parent_headers)
        task_id = create.json()["id"]

        outsider_headers = _auth(client, users["outsider"].email)
        resp = client.patch(f"/api/tasks/{task_id}", json={"is_completed": True}, headers=outsider_headers)
        assert resp.status_code == 404

    def test_outsider_cannot_delete_task(self, client, users):
        parent_headers = _auth(client, users["parent"].email)
        create = client.post("/api/tasks/", json={"title": "Cannot delete"}, headers=parent_headers)
        task_id = create.json()["id"]

        outsider_headers = _auth(client, users["outsider"].email)
        resp = client.delete(f"/api/tasks/{task_id}", headers=outsider_headers)
        assert resp.status_code == 404

    def test_assignee_cannot_delete_task(self, client, users):
        parent_headers = _auth(client, users["parent"].email)
        create = client.post("/api/tasks/", json={
            "title": "Child cannot delete",
            "assigned_to_user_id": users["child_user"].id,
        }, headers=parent_headers)
        task_id = create.json()["id"]

        child_headers = _auth(client, users["child_user"].email)
        resp = client.delete(f"/api/tasks/{task_id}", headers=child_headers)
        assert resp.status_code == 404


# ===========================================================================
# 6. Assignable users endpoint
# ===========================================================================

class TestAssignableUsers:
    def test_parent_sees_linked_children(self, client, users):
        headers = _auth(client, users["parent"].email)
        resp = client.get("/api/tasks/assignable-users", headers=headers)
        assert resp.status_code == 200
        user_ids = [u["user_id"] for u in resp.json()]
        assert users["child_user"].id in user_ids

    def test_teacher_sees_enrolled_students(self, client, users):
        headers = _auth(client, users["teacher_user"].email)
        resp = client.get("/api/tasks/assignable-users", headers=headers)
        assert resp.status_code == 200
        user_ids = [u["user_id"] for u in resp.json()]
        assert users["child_user"].id in user_ids

    def test_student_sees_linked_parents(self, client, users):
        headers = _auth(client, users["child_user"].email)
        resp = client.get("/api/tasks/assignable-users", headers=headers)
        assert resp.status_code == 200
        user_ids = [u["user_id"] for u in resp.json()]
        assert users["parent"].id in user_ids

    def test_outsider_parent_sees_no_children(self, client, users):
        headers = _auth(client, users["outsider"].email)
        resp = client.get("/api/tasks/assignable-users", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []


# ===========================================================================
# 7. Filters
# ===========================================================================

class TestFilters:
    def test_filter_by_completion_status(self, client, users):
        headers = _auth(client, users["parent"].email)
        create = client.post("/api/tasks/", json={"title": "Filter completed"}, headers=headers)
        task_id = create.json()["id"]
        client.patch(f"/api/tasks/{task_id}", json={"is_completed": True}, headers=headers)

        client.post("/api/tasks/", json={"title": "Filter pending"}, headers=headers)

        # Only completed
        resp = client.get("/api/tasks/?is_completed=true", headers=headers)
        assert resp.status_code == 200
        for t in resp.json():
            assert t["is_completed"] is True

        # Only pending
        resp2 = client.get("/api/tasks/?is_completed=false", headers=headers)
        assert resp2.status_code == 200
        for t in resp2.json():
            assert t["is_completed"] is False

    def test_filter_by_priority(self, client, users):
        headers = _auth(client, users["parent"].email)
        client.post("/api/tasks/", json={"title": "High pri", "priority": "high"}, headers=headers)
        client.post("/api/tasks/", json={"title": "Low pri", "priority": "low"}, headers=headers)

        resp = client.get("/api/tasks/?priority=high", headers=headers)
        assert resp.status_code == 200
        for t in resp.json():
            assert t["priority"] == "high"


# ===========================================================================
# 8. Edge cases
# ===========================================================================

class TestEdgeCases:
    def test_assign_to_nonexistent_user(self, client, users):
        headers = _auth(client, users["parent"].email)
        resp = client.post("/api/tasks/", json={
            "title": "Ghost user",
            "assigned_to_user_id": 999999,
        }, headers=headers)
        assert resp.status_code == 404

    def test_unassign_via_update(self, client, users):
        headers = _auth(client, users["parent"].email)
        create = client.post("/api/tasks/", json={
            "title": "Unassign test",
            "assigned_to_user_id": users["child_user"].id,
        }, headers=headers)
        task_id = create.json()["id"]

        # Convention: assigned_to_user_id=0 means unassign
        resp = client.patch(f"/api/tasks/{task_id}", json={"assigned_to_user_id": 0}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["assigned_to_user_id"] is None
        assert resp.json()["assignee_name"] is None

    def test_student_personal_task(self, client, users):
        """Student creates a task for themselves (no assignee)."""
        headers = _auth(client, users["child_user"].email)
        resp = client.post("/api/tasks/", json={"title": "Study for quiz"}, headers=headers)
        assert resp.status_code == 201
        assert resp.json()["assigned_to_user_id"] is None
        assert resp.json()["creator_name"] == "Task Child"

    def test_teacher_personal_task(self, client, users):
        """Teacher creates a task for themselves (no assignee)."""
        headers = _auth(client, users["teacher_user"].email)
        resp = client.post("/api/tasks/", json={"title": "Grade papers"}, headers=headers)
        assert resp.status_code == 201
        assert resp.json()["assigned_to_user_id"] is None
        assert resp.json()["creator_name"] == "Task Teacher"


# ===========================================================================
# 9. Task Archival — soft-delete, restore, permanent delete, auto-archive
# ===========================================================================

class TestTaskArchival:
    def test_delete_soft_deletes(self, client, users):
        """DELETE sets archived_at instead of removing the task."""
        headers = _auth(client, users["parent"].email)
        create = client.post("/api/tasks/", json={"title": "Soft delete me"}, headers=headers)
        task_id = create.json()["id"]

        resp = client.delete(f"/api/tasks/{task_id}", headers=headers)
        assert resp.status_code == 204

        # Not visible in default listing
        listing = client.get("/api/tasks/", headers=headers)
        ids = [t["id"] for t in listing.json()]
        assert task_id not in ids

        # Visible when include_archived=true
        listing2 = client.get("/api/tasks/?include_archived=true", headers=headers)
        archived = [t for t in listing2.json() if t["id"] == task_id]
        assert len(archived) == 1
        assert archived[0]["archived_at"] is not None

    def test_restore_archived_task(self, client, users):
        """Restoring an archived task clears archived_at and is_completed."""
        headers = _auth(client, users["parent"].email)
        create = client.post("/api/tasks/", json={"title": "Restore me"}, headers=headers)
        task_id = create.json()["id"]

        # Archive it
        client.delete(f"/api/tasks/{task_id}", headers=headers)

        # Restore it
        resp = client.patch(f"/api/tasks/{task_id}/restore", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["archived_at"] is None
        assert body["is_completed"] is False
        assert body["completed_at"] is None

        # Now visible in default listing again
        listing = client.get("/api/tasks/", headers=headers)
        ids = [t["id"] for t in listing.json()]
        assert task_id in ids

    def test_restore_non_archived_returns_400(self, client, users):
        """Cannot restore a task that is not archived."""
        headers = _auth(client, users["parent"].email)
        create = client.post("/api/tasks/", json={"title": "Not archived"}, headers=headers)
        task_id = create.json()["id"]

        resp = client.patch(f"/api/tasks/{task_id}/restore", headers=headers)
        assert resp.status_code == 400

    def test_permanent_delete_removes_from_db(self, client, users):
        """Permanent delete only works on archived tasks and hard-deletes."""
        headers = _auth(client, users["parent"].email)
        create = client.post("/api/tasks/", json={"title": "Perm delete me"}, headers=headers)
        task_id = create.json()["id"]

        # Archive first
        client.delete(f"/api/tasks/{task_id}", headers=headers)

        # Permanently delete
        resp = client.delete(f"/api/tasks/{task_id}/permanent", headers=headers)
        assert resp.status_code == 204

        # Gone even with include_archived
        listing = client.get("/api/tasks/?include_archived=true", headers=headers)
        ids = [t["id"] for t in listing.json()]
        assert task_id not in ids

    def test_permanent_delete_non_archived_returns_400(self, client, users):
        """Cannot permanently delete a task that is not archived first."""
        headers = _auth(client, users["parent"].email)
        create = client.post("/api/tasks/", json={"title": "Still active"}, headers=headers)
        task_id = create.json()["id"]

        resp = client.delete(f"/api/tasks/{task_id}/permanent", headers=headers)
        assert resp.status_code == 400

    def test_completion_auto_archives(self, client, users):
        """Completing a task auto-sets archived_at."""
        headers = _auth(client, users["parent"].email)
        create = client.post("/api/tasks/", json={"title": "Auto archive on complete"}, headers=headers)
        task_id = create.json()["id"]

        resp = client.patch(f"/api/tasks/{task_id}", json={"is_completed": True}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["is_completed"] is True
        assert resp.json()["archived_at"] is not None

    def test_uncompletion_unarchives(self, client, users):
        """Un-completing a task clears archived_at."""
        headers = _auth(client, users["parent"].email)
        create = client.post("/api/tasks/", json={"title": "Un-archive on uncomplete"}, headers=headers)
        task_id = create.json()["id"]

        # Complete (auto-archives)
        client.patch(f"/api/tasks/{task_id}", json={"is_completed": True}, headers=headers)

        # Un-complete (un-archives)
        resp = client.patch(f"/api/tasks/{task_id}", json={"is_completed": False}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["is_completed"] is False
        assert resp.json()["archived_at"] is None

    def test_outsider_cannot_restore(self, client, users):
        """Only the creator can restore archived tasks."""
        parent_headers = _auth(client, users["parent"].email)
        create = client.post("/api/tasks/", json={"title": "Only creator restores"}, headers=parent_headers)
        task_id = create.json()["id"]
        client.delete(f"/api/tasks/{task_id}", headers=parent_headers)

        outsider_headers = _auth(client, users["outsider"].email)
        resp = client.patch(f"/api/tasks/{task_id}/restore", headers=outsider_headers)
        assert resp.status_code == 404

    def test_outsider_cannot_permanent_delete(self, client, users):
        """Only the creator can permanently delete archived tasks."""
        parent_headers = _auth(client, users["parent"].email)
        create = client.post("/api/tasks/", json={"title": "Only creator perm deletes"}, headers=parent_headers)
        task_id = create.json()["id"]
        client.delete(f"/api/tasks/{task_id}", headers=parent_headers)

        outsider_headers = _auth(client, users["outsider"].email)
        resp = client.delete(f"/api/tasks/{task_id}/permanent", headers=outsider_headers)
        assert resp.status_code == 404
