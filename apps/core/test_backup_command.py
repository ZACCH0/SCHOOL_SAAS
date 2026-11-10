"""T16: the db_backup management command produces real, rotating backups."""

import json
from datetime import datetime
from pathlib import Path

import pytest
from django.core.management import CommandError, call_command


@pytest.fixture
def backup_dir(tmp_path):
    return tmp_path / "backups"


def _write_stale_backup(folder: Path, name: str) -> Path:
    """Backup files are named school-saas-backup-<YYYYMMDD-HHMMSS>.json, so
    name-sorted order IS age order — plant one directly for the rotation test."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_text("[]", encoding="utf-8")
    return path


@pytest.mark.django_db
def test_backup_command_writes_a_json_file(backup_dir):
    call_command("db_backup", dir=str(backup_dir), force=True)
    backups = list(backup_dir.glob("school-saas-backup-*.json"))
    assert len(backups) == 1
    assert isinstance(json.loads(backups[0].read_text(encoding="utf-8")), list)


@pytest.mark.django_db
def test_backup_contains_the_written_data(backup_dir):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    User.objects.create_user("backup-me", password="S3cure-pass!")

    call_command("db_backup", dir=str(backup_dir), force=True)
    backup_file = next(backup_dir.glob("school-saas-backup-*.json"))
    usernames = [row.get("fields", {}).get("username", "") for row in json.loads(backup_file.read_text(encoding="utf-8"))]
    assert "backup-me" in usernames


@pytest.mark.django_db
def test_backup_filename_carries_a_timestamp(backup_dir):
    call_command("db_backup", dir=str(backup_dir), force=True)
    name = next(backup_dir.iterdir()).name
    stamp = name.removeprefix("school-saas-backup-").removesuffix(".json")
    datetime.strptime(stamp, "%Y%m%d-%H%M%S")  # ValueError would fail the test


@pytest.mark.django_db
def test_rotation_keeps_the_newest_and_deletes_the_oldest(backup_dir):
    _write_stale_backup(backup_dir, "school-saas-backup-20260101-000000.json")
    _write_stale_backup(backup_dir, "school-saas-backup-20260202-000000.json")
    call_command("db_backup", dir=str(backup_dir), keep=2, force=True)
    backups = sorted(p.name for p in backup_dir.glob("school-saas-backup-*.json"))
    assert len(backups) == 2  # 3 files exist, keep=2
    assert "school-saas-backup-20260101-000000.json" not in backups
    assert "school-saas-backup-20260202-000000.json" in backups


@pytest.mark.django_db
def test_rotation_never_touches_unrelated_files(backup_dir):
    stray = backup_dir / "not-a-backup.json"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stray.write_text("{}", encoding="utf-8")
    _write_stale_backup(backup_dir, "school-saas-backup-20260101-000000.json")
    call_command("db_backup", dir=str(backup_dir), keep=1, force=True)
    assert stray.exists()


def test_keep_must_be_positive(backup_dir):
    with pytest.raises(CommandError):
        call_command("db_backup", dir=str(backup_dir), keep=0, force=True)


def test_debug_mode_refuses_without_force():
    from django.conf import settings

    if settings.DEBUG:
        with pytest.raises(CommandError):
            call_command("db_backup")
