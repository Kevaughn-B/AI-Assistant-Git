import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app


def csrf(response):
    return re.search(r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True)).group(1)


def test_signup_login_and_contact(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.db"), "UPLOAD_FOLDER": str(tmp_path / "uploads"), "SECRET_KEY": "test-secret"})
    client = app.test_client()

    page = client.get("/signup")
    client.post("/signup", data={"csrf_token": csrf(page), "username": "student", "email": "student@example.com", "password": "password123"})
    page = client.get("/login")
    response = client.post("/login", data={"csrf_token": csrf(page), "username": "student", "password": "password123"}, follow_redirects=True)
    assert b"Your dashboard" in response.data

    page = client.get("/contact")
    response = client.post("/contact", data={"csrf_token": csrf(page), "form_type": "contact", "name": "Test", "email": "test@example.com", "message": "Hello"}, follow_redirects=True)
    assert b"message has been received" in response.data


def test_protected_pages_require_login(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.db"), "UPLOAD_FOLDER": str(tmp_path / "uploads"), "SECRET_KEY": "test-secret"})
    response = app.test_client().get("/manage_pdfs")
    assert response.status_code == 302
