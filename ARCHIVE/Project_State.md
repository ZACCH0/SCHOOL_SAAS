# PROJECT STATE

Update this file at the end of every phase.

## Current phase
Foundation: project setup and custom user. Next: School (tenant) and Membership.

## Done
- Django project `config` created in project root with split settings (`config/settings/base.py`, `development.py`)
- Secrets in `.env` (python-decouple); `.env.example` and `.gitignore` in place
- PostgreSQL configured as the database
- pytest and pytest-django configured (`pytest.ini`)
- App `apps/accounts` with custom `User` (extends `AbstractUser`, adds optional `phone`), registered in admin
- `AUTH_USER_MODEL = "accounts.User"`

## To verify (tick when confirmed)
- [ ] `python manage.py check` has no issues
- [ ] `python manage.py migrate` ran with no errors
- [ ] Superuser created and admin login works
- [ ] `pytest` shows 3 passed
- [ ] Changes committed to Git

## Decisions made
- Login identifier: username, with optional email and phone (parents may not have email)
- Tenancy: one shared database, `school` foreign key on every school-owned record
- Users link to schools through a Membership (user, school, role), not a single field on the user *(proposed, to build next)*
- Academic sessions and periods are data, so schools can use terms or semesters
- Apps live in `apps/`, app names like `apps.accounts`
- Django 5.2 LTS, PostgreSQL from day one

## Assumptions
- Pilot school uses Primary 1-6 now; JSS/SS added later through configuration
- Details such as grading and fees are configurable and confirmed with the school later

## Known issues
- None recorded yet

## Run locally (Windows PowerShell)
```
.venv\Scripts\activate
python manage.py runserver
pytest
```

## Next phase
1. `schools` app: `School` model
2. `Membership` model with roles
3. School-scoped manager and tenant isolation tests
4. Then: academic sessions and periods