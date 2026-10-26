# PROJECT STATE

Single source of truth for where the project stands. Rules for updating it are in `AGENTS.md` section 9.

**Last updated:** 2026-10-23
**Current phase:** Phase 3, Authentication (foundation work before classes and subjects)
**Current task:** T8b-2 Forms, views, URLs and plain templates for classes and subjects, plus sidebar entries (zip provided; awaiting owner's result, 162 tests expected).
**Next task:** T9 Students and parents (admission numbers, parent with several children, pen-icon photo, class history), then T7d/T7e accounts and login.

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
| T7c | Password reset (email based) | DONE (verified) | 53 passed |
| T7d | Admin resets a user's password (temporary password, forced change) for users without email | TODO (proposed) | Owner has not yet approved |
| T8 | Classes, sections, levels (Primary/JSS/SS activatable), subjects, class subjects, teacher assignments per session, class teacher | IN PROGRESS | T8a DONE (verified, 118 passed). T8b-1 services DONE (verified, 141 passed). T8b-2 views, forms, templates in progress. Owner chose sections as a separate table (option A) |
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
| T7e | Login by phone or email with password; one-time codes (email free, SMS paid) only for activation and password reset; per-school SMS credit and rate limits | TODO (agreed) | Owner agreed the plan |
| H1 | Production settings file and clean `check --deploy` | DONE (verified) | 78 passed; check --deploy has no errors, only W005/W021 (HSTS subdomains and preload) left on purpose until deployment |
| H2 | Login attempt limiting (django-axes, 5 failures per username+IP, 15 minute lock) | DONE (verified) | 82 passed |
| H3 | Audit log foundation (`apps/audit`: append-only AuditLog, `record()` service, login/logout signals, read-only admin) | DONE (verified) | 92 passed |
| H4 | Safe lookup helpers for views (`get_for_school_or_404`, `SchoolScopedMixin`, `RoleRequiredMixin`) | DONE (verified) | 78 passed |
| H5 | Logging to console (platform captures it) with levels from env; error alert emails come at deployment | DONE (verified) | Owner confirmed pytest works; test count not shown (94 expected). Test suite also uses a fast hasher via `config/settings/test.py` |
| H6 | GitHub Actions running tests on every push | IN PROGRESS | Code provided |
| T19 | UI: apply brand palette and app shell to real templates (phases U0 to U2) | DONE (verified) | U0, U1 (58 passed), U2 (68 passed). Real pages are built by the owner with OpenCode from the design canvas |
| T20 | Profile photos for students, teachers, parents (needs Pillow and file storage) | TODO | |
| T21 | School public home page with gallery, news, admissions; own subdomain per school | TODO | Build after T9 to T13 |

## Task log (newest first)

### T8b-2 Views for classes and subjects (in progress)
- Forms scoped to the school (a foreign id is simply not a valid choice), thin function views for owner and admin only, POST-only actions, messages for results
- URLs: `/classes/` (list, new, detail, edit, toggle, sections, class teacher) and `/subjects/` (list, new, edit, toggle, class add and remove, assign and unassign teacher)
- Plain Tailwind templates using the shared components; OpenCode restyles them from the design canvas
- `apps/core/navigation.py` now lists Classes and Subjects for owner and admin; `apps/academics/selectors.py` (`current_session`)
- Tests: `apps/classes/test_views.py` (13), `apps/subjects/test_views.py` (8). Expected total: 162
- Note: `apps/classes/views.py` imports from `apps/subjects` for the combined class detail page (views only, models stay one-directional)

### T8b-1 Services for classes and subjects (verified: 141 passed; the subjects service tests are 11, not 12)
- `apps/schools/service_helpers.py` (`ensure_owned`, `save_or_explain`), `require_role` and `MANAGE_STRUCTURE_ROLES` in `permissions.py`
- `apps/classes/services.py`: create_class, update_class, set_class_active, add_section, assign_class_teacher (plus the seed)
- `apps/subjects/services.py`: create_subject, update_subject, set_subject_active, add_subject_to_class, remove_subject_from_class, assign_teacher, unassign_teacher
- Rules: only owner and admin may change structure; school always comes from the request (never from client input); objects from another school are refused; every change writes an audit entry in the same transaction; nothing is deleted except an unused class-subject link
- Tests: `apps/classes/test_services.py` (12), `apps/subjects/test_services.py` (12), `conftest.py` gets `make_request`. Expected total: 142

### T8a Classes and subjects data model (verified: 118 passed)
- New apps `apps/classes` (Level, SchoolClass, Section, ClassTeacher, `seed_standard_structure`) and `apps/subjects` (Subject, ClassSubject, TeacherAssignment)
- `apps/schools/models.py`: `SchoolOwnedModel.ensure_same_school(...)` and abstract `ValidatedSchoolModel` (runs `clean()` on every save)
- Rules in the database: names unique ignoring case per school, one order number per school, one class teacher and one subject teacher per class/section per session (null-safe constraints)
- Rules in `clean()`: related records must be from the same school, teachers must have the Teacher role, a class can only be assigned subjects it takes
- Root `conftest.py` with shared fixtures. Tests: `apps/classes/tests.py` (14), `apps/subjects/tests.py` (10). Expected total: 118

### H6 GitHub Actions (in progress)
- `.github/workflows/tests.yml`: Python 3.11, PostgreSQL service, installs `requirements/dev.txt`, runs `makemigrations --check` and `pytest`
- Requires `django-axes` pinned in `requirements/base.txt` and the repository pushed to GitHub

### Test speed-up and H5 Logging (verified by owner)
- `config/settings/test.py` (development settings plus MD5 hasher, tests only); `pytest.ini` points to it. The full suite took 4 min 34 s with 92 tests
- `LOGGING` in `base.py` (console handler, `LOG_LEVEL` from env); tests in `apps/audit/test_resilience.py` (2). Expected total: 94

### H3 Audit log foundation (verified: 92 passed)
- New app `apps/audit`: `AuditLog` (school, actor, actor_label, action, target, metadata, ip_address, created_at); entries cannot be updated or deleted (model and queryset block it); `for_school()` for tenant scoping
- `audit.services.record(request, action, target=..., **metadata)`; login and logout recorded by signals (signal failures never block login)
- Admin is read-only. Tests: `apps/audit/tests.py` (10). Expected total: 92
- Convention: action names are `<area>.<verb>`, for example `student.created`, `result.published`, `payment.recorded`; business actions call `record()` inside the same transaction

### H2 Login attempt limiting (verified: 82 passed)
- `django-axes` installed and pinned in `requirements/base.txt`; backend, middleware (last), settings (5 failures, 15 minutes, lock by username plus IP, reset on success); migration applied
- `templates/accounts/locked_out.html`; tests in `apps/accounts/test_lockout.py` (4). Expected total: 82
- Lockout responds with HTTP 429. Tests must use `force_login` or the login view, never `client.login(...)` (axes needs a request)
- To revisit at deployment (T18): proxy IP settings (`AXES_IPWARE_PROXY_COUNT`) for Render, and HSTS subdomains (W005)

### H1 and H4 Backend hardening (verified: 78 passed)
- `config/settings/production.py` (HTTPS redirect, secure cookies, HSTS from env, allowed hosts from env); `.env.example` updated
- `apps/schools/lookups.py` (`get_for_school_or_404`), `SchoolScopedMixin`; `RoleRequiredMixin` added to `permissions.py`
- Tests: `apps/schools/test_lookups.py` (9), `config/test_production_settings.py` (1). Expected total: 78

### U2 Shared components and error pages (verified: 68 passed)
- `static/src/input.css`: `.field` styles for form inputs
- Components in `templates/components/`: page_header, stat_card, status_chip, empty_state, form_field, pagination
- Error pages: `templates/403.html`, `404.html`, `500.html` (500 is standalone so it cannot fail)
- Tests: `apps/core/test_components.py` (10). Expected total: 68
- Modules from T8 on use these components; existing pages unchanged

### U1 App shell (verified: 58 passed)
- `apps/core/navigation.py` (single nav list with role filter), `apps/core/context_processors.py` (`shell`: nav items and current period, school-scoped), registered in settings
- `templates/base.html` rebuilt: skip link, top bar with school and current period, role-aware sidebar (desktop), `<details>` menu (mobile), flash messages partial
- New partials: `templates/partials/nav_items.html`, `templates/partials/messages.html`
- Tests: `apps/core/test_shell.py` (5). Expected total: 58
- Rule: each module adds its own line to `NAV_ITEMS` when its page exists, so there are no dead links

### U0 Brand palette on real templates (verified by owner)
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
- UI will be built by the owner with OpenCode from the design canvas, following `AGENTS.md` section 12; the backend (models, logic, security, tests) stays with the main agent
- Login plan (T7e): password for daily login with phone or email; codes only for activation and reset; each user chooses email or SMS; SMS costs about N6 to N7 each, so limits per number and credits per school
- Student logins are not in the first version; parents see their children's data
- Profile and logo photos are changed by tapping a pen icon badge on the picture (design rule)
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
- Login attempt limiting arrives with H2; proxy IP settings still to be set at deployment
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
