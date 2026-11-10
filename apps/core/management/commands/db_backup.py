"""Database backup. T16 security hardening.

Writes a portable JSON dump of the whole database with Django's dumpdata
(re-creatable with loaddata), rotates old files, and refuses to run when
DEBUG is on unless forced — backups belong on a real deployment machine.
The real schedule (nightly) is set at deployment (T18); this command is
what the schedule will call.
"""

import logging
from datetime import datetime
from io import StringIO

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger("platform")

BACKUP_PREFIX = "school-saas-backup-"


class Command(BaseCommand):
    help = "Dump the database to a JSON file and rotate old backups."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dir",
            default=getattr(settings, "BACKUP_DIR", None) or str(settings.BASE_DIR / "backups"),
            help="Target folder (default: BACKUP_DIR from env, else ./backups).",
        )
        parser.add_argument(
            "--keep",
            type=int,
            default=7,
            help="How many backup files to keep (default: 7).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Allow running even while DEBUG is on (dev convenience).",
        )

    def handle(self, *args, **options):
        if settings.DEBUG and not options["force"]:
            raise CommandError(
                "Refusing to back up while DEBUG is on. Use --force in development."
            )
        keep = options["keep"]
        if keep < 1:
            raise CommandError("--keep must be at least 1.")

        from pathlib import Path

        target_dir = Path(options["dir"])
        target_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{BACKUP_PREFIX}{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        target = target_dir / filename

        buffer = StringIO()
        call_command(
            "dumpdata",
            stdout=buffer,
            natural_foreign=True,
            natural_primary=True,
            exclude=["contenttypes", "auth.permission"],
        )
        buffer.seek(0)
        target.write_text(buffer.read(), encoding="utf-8", newline="\n")

        backups = sorted(target_dir.glob(f"{BACKUP_PREFIX}*.json"))
        for stale in backups[: max(0, len(backups) - keep)]:
            stale.unlink()
            logger.info("Deleted old backup %s", stale.name)

        logger.info("Wrote backup %s (%.1f KB)", target, target.stat().st_size / 1024)
        self.stdout.write(self.style.SUCCESS(f"Backup written: {target}"))
