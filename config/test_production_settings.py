import importlib

def test_production_settings_are_locked_down(monkeypatch):
    monkeypatch.setenv("ALLOWED_HOSTS", "example.com")
    module = importlib.import_module("config.settings.production")
    assert module.DEBUG is False
    assert module.ALLOWED_HOSTS == ["example.com"]
    assert module.SECURE_SSL_REDIRECT is True
    assert module.SESSION_COOKIE_SECURE is True
    assert module.CSRF_COOKIE_SECURE is True