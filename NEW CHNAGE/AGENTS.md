# AGENTS.md

Rules for any AI agent or developer working on this repository. Read this file first, then `PROJECT_STATE.md`, then `REQUIREMENTS.md`.

## 1. What this project is

A multi-tenant School Management SaaS for Nigerian primary and secondary schools (Primary 1-6, JSS 1-3, SS 1-3). The pilot is a real primary school in Saki, Oyo State. It must become usable by other schools.
Everything school-specific (classes, subjects, sessions, periods, fee items, grade scales, assessment components, student fields) is configured by the school and never hard-coded.
Ovidi is a benchmark only. Never copy its code, branding, UI, text or database.

## 2. Read order at the start of every session

1. `AGENTS.md` (this file)
2. `PROJECT_STATE.md` (where we are, what is next, known issues)
3. `REQUIREMENTS.md` (what must be built, with checkboxes)
4. Ask the owner to show any file you are about to change. Never guess a file's contents.

## 3. Working loop for every task

1. State the goal and where it fits (which phase, which module).
2. Explain the design and trade-offs when there is a real choice. Recommend one option.
3. Implement only this task. Do not build ahead.
4. Add tests (see section 7).
5. Run `pytest` and the manual check. Do not call a task done without seeing the output.
6. Commit with a clear message.
7. Update `PROJECT_STATE.md` (see section 9).

## 4. Hard rules

- Build incrementally. Do not start the next phase until the current one is verified.
- Do not invent requirements. Separate: product requirement, technical implementation, future idea.
- Do not rewrite working architecture without a stated reason.
- When debugging: reproduce, find the root cause, make the smallest safe fix, test, check for regressions. Do not rewrite the project.
- Never mark something verified unless the owner has shown the passing output. Mark it "unverified" instead.
- No fake dashboard data, hard-coded demo numbers, or features added only to look big.
- Do not add technology early: no React, Celery/Redis, Docker or extra packages until a task needs them.

## 5. Architecture conventions

- Layout: `config/` (settings, urls), `apps/<name>/` (features), `templates/`, `static/`. App config name is `apps.<name>`.
- Stack: Python 3.11, Django 5.2 LTS, PostgreSQL, Django Templates, Tailwind (standalone CLI), Alpine.js, Chart.js, pytest. DRF, Paystack, WeasyPrint, Cloudinary later.
- Custom user: `accounts.User` (username login, optional email and phone). `AUTH_USER_MODEL` must never change.
- Tenancy: one shared database. Every school-owned model inherits `SchoolOwnedModel` (has `school`, manager with `.for_school(school)`).
- Access: a user acts in a school through a `Membership` (user, school, role). `request.membership` and `request.school` are set by `ActiveSchoolMiddleware`.
- Views that need a role use `@role_required(...)`. Always combine with school-scoped queries.
- Configuration in use is archived (`is_active`), not deleted. Use `on_delete=PROTECT` for school-owned parents.
- New school-owned models inherit `ValidatedSchoolModel` (runs `clean()` on every save) and call `self.ensure_same_school("field", ...)` in `clean()` so related records can never come from another school.
- Database constraints for single-table rules; `clean()` plus tests for cross-table rules. Note that `bulk_create()` and `.update()` skip `clean()`.
- Money: `DecimalField`, database transactions, payment allocations, idempotent payment references. Never overwrite financial history.
- Results: store a snapshot of the grade scale and weights used. Published results are never silently edited; changes need permission and an audit record.
- Performance: paginate lists, use `select_related`/`prefetch_related`, add indexes for common filters.

## 6. Security rules

- Services (functions that change data) take `request`, check the role with `require_role`, take the school from `request.school` (never from user input), refuse objects from another school with `ensure_owned`, and write an audit entry in the same transaction. Views stay thin: fetch with `get_for_school_or_404`, call a service, show the result.

- Record important actions with `apps.audit.services.record(request, "<area>.<verb>", target=obj, **details)`: creating or changing students, scores, results, fees, invoices and payments, approvals, and permission changes. Call it inside the same database transaction as the action. Never log passwords or tokens in the details.

- Never trust the frontend. Check school and permission on the server for every view and API call.
- A request must never reach another school's record by changing an ID. Use `for_school()` or the user's membership to fetch objects, and return 404 for records outside the school.
- Parents see only their own children. Teachers see only assigned classes and subjects. Students see only their own records.
- Secrets live only in `.env` (never committed). Keep `.env.example` current.
- Logout is POST only. Forms use CSRF tokens. Validate all input. Handle non-numeric IDs without crashing.
- Planned before deployment: login attempt limiting, audit log, backups, secure file uploads, production settings and HTTPS.

## 7. Testing rules

- Every task adds tests for its business rules.
- Every new school-owned model gets a tenant isolation test (School A cannot read School B's record, including by ID).
- Test permissions and role checks, not only the happy path.
- In tests, log users in with `client.force_login(user)` or by posting to the login view. Do not use `client.login(...)`: django-axes requires a request and will raise an error.
- Test financial and result calculations with realistic values.
- Run from the project root (folder with `manage.py`), with the virtual environment active:
  - `pytest`
  - `python manage.py check`
  - `python manage.py makemigrations --check --dry-run` (should report no changes after a task is finished)

## 8. Code and Git style

- PEP 8, clear names, small functions, thin views, business logic in services or selectors when it grows. No copy-pasted logic.
- Commit messages: `feat:`, `fix:`, `test:`, `docs:`, `chore:`, `refactor:`. Meaningful, never "update" or "final".
- Never delete or edit applied migration files unless the owner agrees and the reason is explained.

## 9. Updating PROJECT_STATE.md after every task

Update these parts, in this order:

1. **Last updated** and **Current task**.
2. **Task board**: set the task status. Use only: `TODO`, `IN PROGRESS`, `DONE (unverified)`, `DONE (verified)`.
3. **Task log**: add a new entry at the top with: date, task, what changed, files, migrations, test result, commit message, known issues.
4. **Next task**: exact next step.
5. **Decisions**, **Known issues** and **Technical debt**: add anything new.
6. Tick matching boxes in `REQUIREMENTS.md`.

## 10. Working with the owner

- The owner is a developer who wants to learn. Explain what, why, where it fits, the relevant database relationships, then the code, how to test, and what could go wrong.
- Environment: Windows, PowerShell, VS Code. Give exact file paths and say whether to replace a whole file or add to it.
- Give code in small steps. Do not paste hundreds of unexplained lines.
- Be honest about risks, shortcuts and anything that could cause bugs, crashes or missing requirements.
- The owner wants no omissions: check each task against `REQUIREMENTS.md` before calling it done.

## 11. Definition of done for a task

- [ ] Code matches the requirement and the conventions above
- [ ] Migrations created and applied
- [ ] New tests written and the full suite passes
- [ ] Manual check done (admin or browser)
- [ ] Tenant isolation and permissions considered and tested where relevant
- [ ] Committed
- [ ] `PROJECT_STATE.md` and `REQUIREMENTS.md` updated

## 12. UI agent boundaries (OpenCode or any UI-only agent)

The owner may use a separate agent to build the UI from the design canvas. That agent must follow these limits.

- Design source: https://claude.ai/artifact/6hL8FbNod8j25sAPp91am5 (62 screens). Palette: teal #0F766E, deep teal #115E59, light teal #CCFBF1, text #0F172A, background #F4F6F3, borders #E2E8F0. Amber only for money owed, green/red only for status. Font: Public Sans. Mobile first, 44px touch targets.
- May edit: `templates/`, `static/src/input.css`, template partials and components, and template-related tests.
- Must not change without asking the owner: models, migrations, view logic, permissions, middleware, settings, `selectors.py`, `navigation.py` rules, or existing non-template tests.
- Keep: `request.school` scoping, `{% csrf_token %}` on every POST form, logout as POST, and one `{% block content %}` in `base.html`.
- Reuse `templates/components/` (page_header, stat_card, status_chip, empty_state, form_field, pagination) and `templates/partials/`. Add new Tailwind tokens only in `input.css` `@theme`.
- Profile and logo photos are edited with a pen icon badge on the picture.
- Do not add packages (including icon or JS libraries) without asking. Icons are inline SVG.
- After every change: rebuild CSS (`.\tailwindcss.exe -i static/src/input.css -o static/css/output.css`), run `pytest` (all tests must still pass), and update `PROJECT_STATE.md`.
- Show real data only. Never ship the design's sample numbers or names.
