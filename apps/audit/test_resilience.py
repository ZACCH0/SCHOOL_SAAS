import logging
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()

def test_logging_is_configured_for_the_console():
    assert "console" in settings.LOGGING["handlers"]
    assert settings.LOGGING["root"]["handlers"] == ["console"]

@pytest.mark.django_db
def test_login_still_works_when_audit_writing_fails(client, monkeypatch, caplog):
    def broken(*args, **kwargs):
        raise RuntimeError("database hiccup")

    monkeypatch.setattr("apps.audit.signals.record", broken)
    User.objects.create_user("teacher1", password="S3cure-pass!")
    with caplog.at_level(logging.ERROR):
        response = client.post(
            reverse("accounts:login"), {"username": "teacher1", "password": "S3cure-pass!"}
        )
    assert response.status_code == 302
    assert "_auth_user_id" in client.session
    assert "Could not write the login audit entry" in caplog.text