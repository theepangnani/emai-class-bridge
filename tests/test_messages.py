import pytest

PASSWORD = "Password123!"


def _login(client, email):
    resp = client.post("/api/auth/login", data={"username": email, "password": PASSWORD})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth(client, email):
    return {"Authorization": f"Bearer {_login(client, email)}"}


@pytest.fixture()
def msg_users(db_session):
    from app.core.security import get_password_hash
    from app.models.user import User, UserRole
    from app.models.student import Student, parent_students, RelationshipType
    from app.models.teacher import Teacher
    from app.models.course import Course, student_courses
    from sqlalchemy import insert

    parent = db_session.query(User).filter(User.email == "msg_parent@test.com").first()
    if parent:
        teacher = db_session.query(User).filter(User.email == "msg_teacher@test.com").first()
        student = db_session.query(User).filter(User.email == "msg_student@test.com").first()
        return {"parent": parent, "teacher": teacher, "student": student}

    hashed = get_password_hash(PASSWORD)
    parent = User(email="msg_parent@test.com", full_name="Msg Parent", role=UserRole.PARENT, hashed_password=hashed)
    teacher = User(email="msg_teacher@test.com", full_name="Msg Teacher", role=UserRole.TEACHER, hashed_password=hashed)
    student = User(email="msg_student@test.com", full_name="Msg Student", role=UserRole.STUDENT, hashed_password=hashed)
    db_session.add_all([parent, teacher, student])
    db_session.flush()

    student_rec = Student(user_id=student.id)
    teacher_rec = Teacher(user_id=teacher.id)
    db_session.add_all([student_rec, teacher_rec])
    db_session.flush()

    db_session.execute(insert(parent_students).values(
        parent_id=parent.id, student_id=student_rec.id,
        relationship_type=RelationshipType.GUARDIAN,
    ))

    course = Course(name="Msg Test Course", teacher_id=teacher_rec.id,
                    created_by_user_id=teacher.id, is_private=False)
    db_session.add(course)
    db_session.flush()
    db_session.execute(student_courses.insert().values(
        student_id=student_rec.id, course_id=course.id,
    ))
    db_session.commit()
    for u in [parent, teacher, student]:
        db_session.refresh(u)
    return {"parent": parent, "teacher": teacher, "student": student}


# ── Existing tests ──────────────────────────────────────────

def test_unread_count_and_mark_read(client, db_session):
    from app.core.security import get_password_hash
    from app.models.message import Conversation, Message
    from app.models.user import User, UserRole

    user_a = db_session.query(User).filter(User.email == "usera@example.com").first()
    if not user_a:
        user_a = User(email="usera@example.com", full_name="User A", role=UserRole.PARENT,
                      hashed_password=get_password_hash(PASSWORD))
        user_b = User(email="userb@example.com", full_name="User B", role=UserRole.TEACHER,
                      hashed_password=get_password_hash(PASSWORD))
        db_session.add_all([user_a, user_b])
        db_session.commit()
    else:
        user_b = db_session.query(User).filter(User.email == "userb@example.com").first()

    conv = Conversation(participant_1_id=user_a.id, participant_2_id=user_b.id, subject="Test conversation")
    db_session.add(conv)
    db_session.commit()

    msg = Message(conversation_id=conv.id, sender_id=user_b.id, content="Hello from B", is_read=False)
    db_session.add(msg)
    db_session.commit()

    headers = _auth(client, user_a.email)
    unread = client.get("/api/messages/unread-count", headers=headers)
    assert unread.status_code == 200
    assert unread.json()["total_unread"] >= 1

    mark = client.patch(f"/api/messages/conversations/{conv.id}/read", headers=headers)
    assert mark.status_code == 200


# ── Recipients ──────────────────────────────────────────────

class TestRecipients:
    def test_parent_gets_recipients(self, client, msg_users):
        headers = _auth(client, msg_users["parent"].email)
        resp = client.get("/api/messages/recipients", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_teacher_gets_recipients(self, client, msg_users):
        headers = _auth(client, msg_users["teacher"].email)
        resp = client.get("/api/messages/recipients", headers=headers)
        assert resp.status_code == 200

    def test_unauthenticated_returns_401(self, client):
        resp = client.get("/api/messages/recipients")
        assert resp.status_code == 401


# ── Conversations CRUD ──────────────────────────────────────

class TestConversations:
    def test_create_conversation(self, client, msg_users):
        headers = _auth(client, msg_users["parent"].email)
        resp = client.post("/api/messages/conversations", json={
            "recipient_id": msg_users["teacher"].id,
            "subject": "Hello Teacher",
            "initial_message": "Question about my child",
        }, headers=headers)
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert "id" in data
        assert data["subject"] == "Hello Teacher"

    def test_list_conversations(self, client, msg_users):
        headers = _auth(client, msg_users["parent"].email)
        resp = client.get("/api/messages/conversations", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_conversation_detail(self, client, msg_users, db_session):
        from app.models.message import Conversation, Message

        conv = Conversation(
            participant_1_id=msg_users["parent"].id,
            participant_2_id=msg_users["teacher"].id,
            subject="Detail Test",
        )
        db_session.add(conv)
        db_session.commit()
        db_session.refresh(conv)

        msg = Message(conversation_id=conv.id, sender_id=msg_users["parent"].id,
                      content="Test detail message", is_read=False)
        db_session.add(msg)
        db_session.commit()

        headers = _auth(client, msg_users["parent"].email)
        resp = client.get(f"/api/messages/conversations/{conv.id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["subject"] == "Detail Test"
        assert len(data["messages"]) >= 1

    def test_send_message(self, client, msg_users, db_session):
        from app.models.message import Conversation

        conv = Conversation(
            participant_1_id=msg_users["parent"].id,
            participant_2_id=msg_users["teacher"].id,
            subject="Send Test",
        )
        db_session.add(conv)
        db_session.commit()
        db_session.refresh(conv)

        headers = _auth(client, msg_users["parent"].email)
        resp = client.post(f"/api/messages/conversations/{conv.id}/messages", json={
            "content": "New message in conversation",
        }, headers=headers)
        assert resp.status_code in (200, 201)
        assert resp.json()["content"] == "New message in conversation"

    def test_nonparticipant_cant_view(self, client, msg_users, db_session):
        from app.models.message import Conversation

        conv = Conversation(
            participant_1_id=msg_users["parent"].id,
            participant_2_id=msg_users["teacher"].id,
            subject="Private Conv",
        )
        db_session.add(conv)
        db_session.commit()
        db_session.refresh(conv)

        headers = _auth(client, msg_users["student"].email)
        resp = client.get(f"/api/messages/conversations/{conv.id}", headers=headers)
        assert resp.status_code in (403, 404)
