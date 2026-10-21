# PROJECT STATE

Single source of truth for where the project stands. Rules for updating it are in `AGENTS.md` section 9.

**Last updated:** 2026-10-19
**Current phase:** Phase 3, Authentication (foundation work before classes and subjects)
**Current task:** U0 Apply brand palette to real templates (code provided; awaiting owner's result, 53 tests expected, no logic change).
**Next task:** U1 app shell (sidebar, top bar, page header, flash messages), then U2 components and error pages, then T8 Classes, sections, subjects, teacher assignments. T7d (admin password reset) to be added after U2 if the owner agrees.

## Task board

Statuses: `TODO`, `IN PROGRESS`, `DONE (unverified)`, `DONE (verified)`.

| ID | Task | Status | Evidence |
|---|---|---|---|
| T0 | Master prompt, brief, requirements and agent rules written | DONE (verified) | Files exist |
| T1 | Project skeleton, split settings, `.env`, PostgreSQL, pytest | DONE (verified) | Server runs, pytest runs |
| T2 | Custom user (`apps/accounts`) | DONE (verified) | 3 tests passed |
| T3 | `School` and `Membership` (`apps/schools`) | DONE (verified) | 7 tests passed |
| T4 | Tenant base model and `AcademicSession` (`apps/academics`) | DONE (verified) | Owner confirmed it worked (13 tests expected) |
| T5 | `AcademicPeriod` | DONE (verified) | 21 tests passed, migration academics.0002 applied |
| T6 | Active school middleware and `role_required` | DONE (verified) | Included in 49 passed |
| T7a | Tailwind (standalone CLI), base layout, home page, `core` app | DONE (verified) | Styling confirmed; included in 49 passed |
| T7b | Login, logout, school chooser, dashboard landing, `selectors.py` | DONE (verified) | 49 passed on 2026-10-19 |
| T7c | Password reset (email based) | DONE (verified) | Owner confirmed it worked; test count not shown (53 expected) |
| T7d | Admin resets a user's password (temporary password, forced change) for users without email | TODO (proposed) | Owner has not yet approved |
| T8 | Classes, sections, class levels (Primary/JSS/SS), subjects, teacher assignments | TODO | |
| T9 | Students and parents (parent with many children, history across promotions) | TODO | |
| T10 | Attendance | TODO | |
| T11 | Admissions | TODO | |
| T12 | Assessments, results, grading, workflow, report cards (PDF) | TODO | |
| T13 | Finance: fee structures, invoices, payments, receipts, balances | TODO | |
| T14 | Dashboards, announcements, notifications, timetable | TODO | |
| T15 | Documents, analytics, audit log | TODO | |
| T16 | Security hardening (login attempt limiting, backups, file security, production settings) | TODO | |
| T17 | REST API (only where useful) | TODO | |
| T18 | Production deployment (Render) and school pilot | TODO | |
| T19 | UI: apply brand palette and app shell to real templates (phases U0 to U2) | IN PROGRESS | U0 code provided; U1 and U2 to do |
| T20 | Profile photos for students, teachers, parents (needs Pillow and file storage) | TODO | |
| T21 | School public home page with gallery, news, admissions; own subdomain per school | TODO | Build after T9 to T13 |

## Task log (newest first)

### U0 Brand palette on real templates (in progress)
- `static/src/input.css`: `@theme` tokens (brand-50, brand-600, brand-700, page, ink, line) and a focus-visible outline
- Templates: indigo, slate-50, slate-800 and ring-slate-200 replaced by the tokens; header border colour set explicitly (Tailwind v4 default is currentColor)
- No Python, models or tests changed. Expected tests: 53

### T7c Password reset (verified by owner)
- Django built-in reset views under `accounts/password-reset/` and `accounts/reset/...` with own templates; email via console backend in development
- Users without an email cannot self-reset; a school admin or Django admin resets them (admin screen later)
- `PASSWORD_RESET_TIMEOUT` set to 3 hours
- Tests: `apps/accounts/test_password_reset.py` (4). Expected total: 53
- Note: the design canvas "Forgot password" screen asks for a username; the built version asks for an email. Canvas to be updated.

### T7b Login, logout, school chooser, dashboard landing (verified: 49 passed)
- Added `apps/schools/selectors.py` (`active_memberships`), refactored middleware to use it
- Settings: `LOGIN_URL`, `LOGIN_REDIRECT_URL`, `LOGOUT_REDIRECT_URL`
- URLs: `accounts/login/`, `accounts/logout/` (POST only), `school/choose/`, `dashboard/`
- Views: `core.dashboard`, `schools.choose_school` (only accepts the user's own membership; non-numeric IDs handled)
- Templates: login, choose_school, dashboard, no_access; header with login/logout
- Tests added: `apps/accounts/test_login.py`, `apps/core/tests.py` (replaced), `apps/schools/test_choose_school.py`
- Migrations: none. Expected tests: 49
- Known issue: no login attempt limiting yet (planned T16)

### T7a Tailwind, base layout, home page
- `core` app, `templates/base.html`, `templates/core/home.html`, Tailwind standalone CLI (`tailwindcss.exe`, git-ignored), `static/src/input.css` to `static/css/output.css`
- Rebuild CSS after template changes: `.\tailwindcss.exe -i static/src/input.css -o static/css/output.css`

### T6 Active school and role check
- `ActiveSchoolMiddleware` sets `request.membership` and `request.school`; only the user's own active membership in an active school is accepted
- `role_required(*roles)` decorator in `apps/schools/permissions.py`
- Tests in `apps/schools/test_active_school.py` (12). Expected total: 33

### T5 AcademicPeriod
- Model with constraints (unique name and order per session, one current per school, end after start), `clean()` for same school and dates inside session
- 21 tests passed

### T4 Tenant base model and AcademicSession
- `SchoolQuerySet.for_school()`, abstract `SchoolOwnedModel`, `AcademicSession` with constraints, isolation tests

### T3 School and Membership
- `School` (slug unique, `is_active`), `Membership` (unique user+school+role, `PROTECT` on school)
- 7 tests passed

### T2 Custom user
- `accounts.User` extends `AbstractUser` with optional `phone`; `AUTH_USER_MODEL = "accounts.User"`
- 3 tests passed

### T1 Skeleton
- Django 5.2.17, Python 3.11.8, split settings, `.env`, PostgreSQL, pytest, `.gitignore`

## Design
- Design canvas (about 62 screens, ordered like the real app): https://claude.ai/artifact/6hL8FbNod8j25sAPp91am5
- Locked palette: primary teal #0F766E, deep teal #115E59, light teal #CCFBF1, text #0F172A, background #F4F6F3, white cards, borders #E2E8F0. Status colours only for meaningful states; amber for money owed.
- Font: Public Sans. Mobile-first, 44px touch targets, every status has a word.
- The real Django templates still use indigo/slate and must be moved to the palette (T19).
- Ovidi's theme colour is orange, so teal keeps us visually distinct. Schola, Termwise, SchoolBase are references only.

## Decisions
- Each school gets a public home page on its own subdomain; built after the core modules (owner agreed)
- Photos: Student.photo for students, User.photo for teachers and parents; children's photos never on the public page without parental permission
- Login by username; email and phone optional (parents may have no email)
- Shared database, `school` foreign key on every school-owned record, explicit `for_school()` scoping (not automatic hidden filtering)
- Access through `Membership` (user, school, role); a person can hold several roles or schools
- Academic sessions and periods are data, so schools can use terms or semesters
- Schools and in-use configuration are deactivated or archived, not deleted
- Tailwind via standalone CLI (works offline, no Node.js)
- `apps/` folder for all feature apps; `core` app for pages that belong to no module

## Known issues and technical debt
- No login attempt limiting yet (T16)
- Platform super admin has no dedicated permission helper or screens; uses Django admin
- `bulk_create()` and `.update()` skip `AcademicPeriod.clean()`; use normal saves or forms
- Users without an email cannot self-reset a password until T7d
- No audit log yet (T15)
- Brand name is a placeholder ("School Platform")
- Seed data for testing is planned (CSV files and a management command)

## Current project structure
```
SCHOOL_SAAS/
  manage.py, pytest.ini, .env, .env.example, .gitignore, tailwindcss.exe
  AGENTS.md, PROJECT_STATE.md, REQUIREMENTS.md
  config/ (settings/base.py, settings/development.py, urls.py, asgi.py, wsgi.py)
  apps/
    accounts/   custom User, login urls
    schools/    School, Membership, SchoolOwnedModel, middleware, permissions, selectors, choose-school view
    academics/  AcademicSession, AcademicPeriod
    core/       home, dashboard
  templates/    base.html, accounts/, schools/, core/
  static/       src/input.css, css/output.css
  requirements/ base.txt, dev.txt
```

## Commands (Windows PowerShell, from the project root)
```
.venv\Scripts\activate
python manage.py runserver
pytest
python manage.py makemigrations
python manage.py migrate
.\tailwindcss.exe -i static/src/input.css -o static/css/output.css
```
