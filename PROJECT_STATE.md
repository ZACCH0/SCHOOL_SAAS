# PROJECT STATE

Single source of truth for where the project stands. Rules for updating it are in `AGENTS.md` section 9.

**Last updated:** 2026-11-04 (T14c dashboards built, 486 passed — owner to verify in browser)
**Current phase:** Modules 1-4 hard complete. T14 code complete (T14c unverified). Nav shell rebuilt to canvas (T19b). 486 tests passing.
**Current task:** T14c dashboards DONE (unverified) — owner to walk all four role dashboards in the browser.
**Next task:** After owner verifies T14c: T14 closes; then T15 documents/analytics/audit log (pick with owner).

## Task boardStatuses: `TODO`, `IN PROGRESS`, `DONE (unverified)`, `DONE (verified)`.

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
| T8 | Classes, sections, levels (Primary/JSS/SS activatable), subjects, class subjects, teacher assignments per session, class teacher | DONE (unverified by owner in browser) | T8a DONE (verified, 118 passed). T8b-1 services DONE (verified, 141 passed). T8b-2 views, forms, templates DONE (verified, 162 passed on 2026-10-26). Owner chose sections as a separate table (option A) |
| T9 | Students and parents (parent with many children, history across promotions) | DONE (verified by owner) | T9a data model, T9b services, T9c pages. 199 tests passed; owner consulted on admission numbers: manual entry stays, no auto-numbering for now |
| T10 | Attendance | DONE (unverified by owner in browser) | T10a model, T10b services, T10c pages. 227 tests passed on 2026-10-26; tenant isolation, role matrix, audit and read-only history covered |
| T11 | Admissions | DONE (verified by owner 2026-11-01) | T11a model `fe70a0d`, T11b services `7eb0eba`, T11c pages `170ca17`; owner walked the full pipeline live; 26 admissions tests, 415 suite passed |
| T7d | Admin resets a user's password (temporary password, forced change) for users without email | DONE (unverified in browser) | Commit `52a3727`; 8 tests in apps/accounts/test_password_admin.py; 389 passed |
| T12 | Assessments, results, grading, workflow, report cards (PDF) | DONE (verified) | T12a verified 2026-10-28; T12b/c workflow + notifications verified in browser; T12d PDF verified; T12e ranking/totals/attendance + HTML restyle approved by owner 2026-10-30. 381 tests passed |
| T13 | Finance: fee structures, invoices, payments, receipts, balances | DONE (unverified by owner in browser) | T13a model, T13b services, T13c pages. 257 tests passed on 2026-10-26; idempotent payments, no overpay, audit, tenant isolation |
| T14 | Dashboards, announcements, notifications, timetable | IN PROGRESS | T14a verified 2026-11-03 (`4800bdc`); T14b verified 2026-11-04 (36 timetable tests); T14c dashboards DONE (unverified) — 486 suite |
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
| T19b | Nav shell rebuilt to canvas: desktop sidebar (no top bar), tablet Menu drawer, phone bottom tab bar for ALL roles | DONE (unverified in browser) | +4 tests in app shell, 440 passed |
| T20 | Profile photos for students, teachers, parents (needs Pillow and file storage) | TODO | |
| T21 | School public home page with gallery, news, admissions; own subdomain per school | TODO | Build after T9 to T13 |
| P1 | Parent portal step 1: My children page (parents only, own-school links) | DONE (verified by owner 2026-10-29) | apps/portal; 8+ tests; 353 passed |
| P1b | Office creates parent accounts (Parents list + Add parent, audited) | DONE (verified by owner 2026-10-29) | apps/students:parent_list/create; owner registered parent1 flow |
| P2 | Parent portal step 2: child page (published results + fee balances, read-only) | DONE (verified by owner 2026-10-29) | 16 portal tests; 372 passed |
| P3 | Parent portal step 3: report card HTML + PDF for linked parents | DONE (verified) | Owner opened/downloaded the PDF from the portal; label size fixed on their feedback. 20 portal tests; 376 passed |

## Task log (newest first)

### T14c Role dashboards (2026-11-04, 486 passed) — DONE (unverified, owner to check in browser)
- `/dashboard/` left as the single URL; view stays thin and dispatches on role via new `apps/core/selectors.py` (read-only, active school + current/last period only; empty school = zeros + amber "No term is marked current" note)
- Role blocks (real data only, no charts): **Owner/Admin** active students, teachers, admissions waiting (applied/reviewed), fees expected/collected/outstanding/rate (reuses `fees_overview`), latest notices; **Bursar** same money stats + 5 newest payments this term (`fees:payment_list` link) + notices; **Teacher** periods today (coverage rule), draft sheets only I can still fill, teaching count cards, notices; **Parent** children cards via `children_for` with term fee owed (subquery totals mirroring the fees module) + published-results counts + notices. Student role gets the plain welcome card
- Notice audience on the dashboard follows the notice board rule (managers all; roles everyone+own audience); archived never shown
- One shared rule extraction: `apps/subjects/selectors.py` `assignments_for` + `assignment_covers` (class-wide covers every section, exact-section only its own, subject must match) — now used by score-entry eligibility, timetable, and the dashboard; `apps/timetable/selectors.py` `covering_slots(school, session, membership, day)` and `timetable:my_timetable` refactored onto it, behaviour unchanged (all timetable tests green)
- Templates `templates/core/dashboard_sections/{manager,bursar,teacher,parent}.html` reuse fees-home stat markup + shared components; money via `{% load humanize %}` `₦…|intcomma`
- Tests `apps/core/test_dashboard.py` (10): manager real counts (graduated/admitted excluded, rate 40), manager no-session empty-state, Beta-school numbers never leak (counts + name), bursar money + this-term payments only, teacher today's periods (other day + break excluded) + draft sheets only mine + published/foreign-subject hidden, school B teacher sees nothing from school A but own sheet, parent children with owed 15000 (parents audience only, staff hidden), unlinked child never listed
- Test conventions learned: pytest classes MUST be named `Test*` (`XxxDashboardTests` collected nothing); ValidatedSchoolModel runs `clean()` on save so every child row needs `school=`; PUBLISHED result sheets need `submitted_by`; announcements require an owner/admin publisher
- CSS rebuilt; `check` + `makemigrations --check` clean. Owner should next walk each role's dashboard in the browser (welcome line includes the term)
- Commit: `feat: role dashboards - manager bursar teacher parent with real data only, 10 tests`

### T14b verified in browser (2026-11-04, docs only)
- Owner walked the timetable pages (class grids + teacher "My timetable") and confirmed they work. T14b marked DONE (verified).
- No code changes. Suite stands at 476 passed.
- Next task: T14c announcements/notifications.

### Teacher "My timetable" (2026-11-03, 476 passed) — follow-up to T14b, owner request
- Owner asked whether every teacher gets their own timetable. Answer: the office still builds the single class timetable (one source of truth, no clashes); the teacher's personal view is DERIVED. Built `/timetable/my/` (namespace `timetable:my`)
- `my_timetable` view: a lesson slot belongs to the signed-in teacher when one of their TeacherAssignments for the current session covers it — exact-section assignment covers that section only, class-wide covers every section and the whole-class slots. Breaks are lessons-never (no subject → never "mine"); assigned slots with foreign sessions/subjects can never match
- Page: day groups (Monday first, only days with own lessons), each row `Subject · section · Class · time range`; empty state tells the teacher their schedule appears once the office places periods on a class they teach. Home page shows a "My timetable" button for teachers (not managers)
- Owner/admin can open the route but it is empty by design (no TEACHER assignments); bursar/parent 403
- Tests `apps/timetable/test_views.py` +3: covered-lessons only (colleague's subject and the break absent), exact-section rule shows A but not B, another school's same-subject lesson never appears
- Lesson kept: Subject is school-owned — school B cannot reuse school A's Subject instance in a slot; tests must create a per-school subject
- CSS rebuilt, `check` + `makemigrations --check` clean. User action: as a teacher check Timetable → My timetable
- Commit: `feat: teacher My timetable - own lessons derived from assignments, 3 tests`

### T14b Timetable complete (2026-11-03, 473 passed) — DONE (unverified, owner to check in browser)
- Fixed the 2 paused service tests: overlap regex is `match="already runs"` (service wording was always correct); the archive/restore audit helper now orders by `id` (audit ties within the same second). 22/22 model+service tests pass
- Pages (`a5c343e`): `/timetable/` home — class cards with section + period counts for the CURRENT session (owners/admins see all classes; teachers only classes they have a TeacherAssignment for this session); `/timetable/classes/<pk>/` grid — day sections (Mon-Sun, only days that have slots) with rows `title · time range · section · teacher`, add-period form in a collapsible card, "Take off" per slot; `timetable:add` is a GET/POST form page; archive/restore are POST-only
- Teacher derivation: `_teacher_names(slot)` reads TeacherAssignment for (session, class, subject) — exact section assignment preferred, class-wide fallback; never stored on the slot. Lessons with no assignment show "no teacher assigned"; breaks never show a teacher
- Forms `SlotForm` (school/class/session fixed by view): subject choices = subjects the class takes (ClassSubject), optional section, label (cleared for lessons; required for breaks via form AND model), day, start/end times. The class's subjects come pre-filtered so an untaught subject cannot even by posted in cleanly — invalid-choice errors keep the slot count at 0
- Nav "Timetable" for owner/admin/teacher only (bursar/parent do not see it). URLs included at `timetable/` (namespace `timetable`). All lookups via `get_for_school_or_404` / `for_school`
- Tests: `apps/timetable/test_views.py` (11): anonymous login wall, bursar/parent 403, owner home counts, teacher sees only taught classes (grid 403 otherwise), teacher read-only (no Take off, archive POST 403), tenant isolation 404 on foreign grid + foreign slot archive/restore, owner posts lesson AND break (2 audits) but a lesson with a label / break without one are refused, untaught subject never lands, overlap friendly message, archive → empty grid → restore with audited history
- Test-agile notes (for future module copies): TeacherAssignment requires a TEACHER-role membership (owners cannot be assigned); login signals create an audit row, so filter audit assertions by action prefix; the add-slot helper needs its own `ends_at` when `starts_at` varies
- CSS rebuilt, `check` + `makemigrations --check` clean. Owner should next walk: sidebar Timetable → class grid → add a period → take it off
- Commit: `feat: timetable - class grids with slot rules + pages, 11 view tests`

### T14b Timetable PAUSED — resumed and finished the same day (2026-11-03)

Owner approved the design: slot per class (optional section override), subject=None = break/assembly (label required), teacher always derived from TeacherAssignment (never stored on the slot), 7 weekdays, overlap refused.

**DONE — apps/timetable model (11/11 model tests passing):**
- New app `apps.timetable` registered in `config/settings/base.py` after `apps.announcements`
- Model `TimetableSlot` (ValidatedSchoolModel): session (per-session config like fees/results), school_class, section (null = whole class), subject (null = break/assembly), label (required when subject is null, forbidden when a subject is set), day (WeekDay IntegerChoices 1-7), starts_at/ends_at TimeFields, is_active archive flag, created/updated
- Rules: `clean()` runs ensure_same_school(session/class/section/subject), section-belongs-to-class, end-after-start, break-label rule, and `_refuse_overlap()` — same school+session+class+day, times overlap, is_active=True; a whole-class slot overlaps every section slot, a section slot overlaps the class-wide slot and its own section only (two sections may differ)
- DB: unique (school, session, class, day, starts_at) + same for section, BOTH conditioned on is_active (archived slots free their exact start time but false duplicates among archived rows are possible — accepted, clean() guards all normal saves); CheckConstraint end>start; index `tt_lookup_idx`
- Migration `timetable.0001_initial` created AND applied
- Admin registered. Files: `models.py`, `admin.py`, `apps.py`, `tests.py` (11 tests: lesson saves, break needs label / lesson must not have one, end-after-start, occupied time refused, same times fine in other school/day, archived frees time, tenant isolation by id, foreign refs refused field by field, section-belongs-to-class, sections may differ but respect class-wide grid). Helpers `make_class`/`make_subject`/`slot` live in `apps/timetable/tests.py` and are reused by the services tests

**WRITTEN, 2 TESTS STILL FAILING — apps/timetable/services.py:**
- `create_slot(request, *, session, school_class, section=None, subject=None, label="", day, starts_at, ends_at)` — owner/admin only (MANAGE_STRUCTURE_ROLES), school always from request, friendly refusals for foreign class/section/subject, break-label rule, wraps save so overlap/duplicate surface as ValidationError; audits `timetable.slot_created` with class/day/period/subject details
- `set_slot_active(request, slot, active)` — archive/restore, never delete; audits `timetable.slot_archived` / `timetable.slot_restored`; no-op if state already matches
- `copy_slot_to_session(request, source_slot, *, session)` — copies a period onto another session's timetable by re-calling create_slot; ensure_owned on both source and target session
- Test file `apps/timetable/test_services.py` (11 tests written): owner places + audit, teacher/bursar/parent refused, overlap friendly message, sections differ + stray section refused, break label through service, foreign class refused, foreign slot cannot be archived, archive→restore keeps row + 3 audit entries, archived slot frees time, copy to next session, copy refuses foreign session

**THE 2 FAILURES + HOW TO FIX (verified output seen):**
1. `test_overlap_gives_a_friendly_message` — test regex is wrong, the SERVICE IS CORRECT. Actual message: "Something already runs for this class on Monday at 09:00-09:40 (Mathematics)." → change the test to `match="already runs"`
2. `test_archiving_then_restoring_keeps_history` — `actions()` reads `AuditLog.objects.values_list(...)` and the model orders NEWEST-FIRST (like `.latest()`), so the list comes back reversed. → change the helper in `apps/timetable/test_services.py` to `AuditLog.objects.order_by("id").values_list("action", flat=True)` (same trap as the 2026-10-28 results note: audit timestamps/ordering)
- After fixing those two: run `pytest apps/timetable` (expect 22 passed), then the FULL suite

**REMAINING FOR T14b (do in this order):**
- Views `apps/timetable/views.py` + `forms.py` + `urls.py` (namespace `timetable`): `/timetable/` class listing (owner/admin see all; teacher sees classes they teach per the results `_my_classes` assignment rule), `/timetable/classes/<pk>/` grid page — grid by day x time with slots in order, add-slot form for owner/admin (class-scoped subject choices, optional section, optional label for breaks, day + start + end), POST new-slot, POST remove (archive) a slot; every lookup via `get_for_school_or_404`
- Teacher display rule (agreed): the slot's teacher = TeacherAssignment for (session, class, subject) with exact section match preferred, class-wide fallback — same precedence idea as `ensure_can_edit_scores`, never a stored field
- Nav entry "Timetable" in `apps/core/navigation.py` — recommend visible to owner/admin/teacher (ALL = None would show to bursar/parent too; decide: owner/admin/teacher only)
- Templates `templates/timetable/home.html` + `grid.html` reusing shared components; mobile-first (bottom bar already exists)
- Add `config/urls.py` include, CSS rebuild (`.\tailwindcss.exe -i static/src/input.css -o static/css/output.css --minify`), `python manage.py check`, `makemigrations --check --dry-run` (no new migrations expected), full `pytest`
- Update REQUIREMENTS.md module 11 tick, PROJECT_STATE task board, commit `feat: timetable - class grids with slot rules`, push
- THEN T14c dashboards

### T19b Nav shell rebuilt to the design canvas (2026-11-03, 440 passed)
- Owner said the nav did not match the canvas on mobile/desktop; rebuilt `templates/base.html` from `Tablet layout.png`, `Admin dashboard.png` and `Parent app (phone).png`
- Desktop (md+): fixed left sidebar w-60 with brand, nav links (reuse `partials/nav_items.html` so `navigation.py` rules untouched), school/period + bell + POST logout at the bottom; NO top bar
- Phone/tablet (<md): teal top bar with Menu button (turned white-outline over teal), platform name, bell; Menu/More opens a slide-in drawer (backdrop + Esc + close button) containing the full nav, school/period, bell and POST logout
- Phone/tablet bottom tab bar for ALL roles: 3 role favourites + "More" (4 slots total, like the parent app canvas). Favourites per role in `apps/core/navigation.py` `FAVOURITES` + `bottom_bar_for()` (owner/admin: Dashboard/Attendance/Students; teacher: Dashboard/Attendance/Results/Announcements-order; bursar: Dashboard/Fees/Notifications; parent: My children/Notices/Alerts); fallback fills from `NAV_ITEMS` order. Context processor passes `nav_favourites` + `nav_more`
- Drawer toggles with a 30-line inline vanilla script (no new packages); single `{% block content %}` kept (first attempt had two — caught immediately by the suite); content gains `pb-28` + `md:pl-60` so the bar/sidebar never cover content; safe-area padding for iOS
- Non-member pages (login, school chooser) keep a plain header; logout stays POST-only everywhere
- 4 new shell tests (bottom bar + More for a 5-item member, none for anonymous, favourites respect roles when NAV_ITEMS is monkeypatched). Live shell check: owner bottom bar = Dashboard · Attendance · Students · Notifications · More
- CSS rebuilt. `check` + `makemigrations --check` clean. Owner should check the three layouts in the browser next
- Commit: `feat: nav shell to canvas — desktop sidebar, tablet drawer, phone bottom bar`

### T14a verified by owner (2026-11-03)
- Owner confirmed the announcements board works in the browser (notice board, add notice, take down) — T14a is DONE (verified)
- Docs only; no code changes. Next task: T14b timetable

### T14a Announcements (2026-11-02, 437 passed)
- New app `apps/announcements` (in INSTALLED_APPS after apps.notifications). Model `Announcement` (ValidatedSchoolModel): title, body, audience choice (everyone/staff/teachers/parents), `published_by` Membership FK (clean() refuses non owner/admin members), is_active archive flag, created/updated. Index on school+audience+is_active. Migration `announcements.0001` applied
- Services `create_announcement` (owner/admin; creates the notice, fans notifications out to the audience's	active memberships via `notify_memberships` — publisher skipped automatically, foreign-school/inactive members receive nothing, audits `announcements.announcement_created`) and `archive_announcement` (sets is_active False, never deletes, audits `announcements.announcement_archived`)
- Pages: `/announcements/` notice board visible to every role but FILTERED by audience (managers see all; teacher sees everyone+teachers; bursar everyone+staff; parent everyone+parents; archived never shown), pagination 25/page, audience chips, "Take down" POST button for managers; `/announcements/new/` form page (owner/admin); `/announcements/<pk>/archive/` POST-only. Nav "Announcements" for all roles
- Tests `apps/announcements/tests.py` (5: default audience, teacher/bursar cannot publish, foreign membership rejected both directions, tenant isolation by id, admin can publish to teachers) + `test_services.py` (8: audited creation, non-manager 403 with no row saved, everyone fan-out skips publisher, audience filter, inactive/foreign members get nothing, invalid audience saves nothing, archive deactivates without deleting, foreign archive refused) + `test_views.py` (9: login wall, owner sees all, teacher/parent/bursar audience filtering, archived disappears but row kept, teacher 403 on create+archive, create posts and audits, foreign archive 404)
- CSS rebuilt (new template compiled). `check` + `makemigrations --check` clean
- Owner should next check the notice board in the browser (announcement board, add a notice, take it down)
- Commit `4800bdc`

### T11 verified by owner + day-2 close (2026-11-01)
- Owner walked the admissions pipeline live: add → review → admit/decline → enrol with admission number — "everything works well"
- Module 4 ticked in Requirements.md with status notes; T11 marked DONE (verified)
- Commits this session: `52a3727` T7d password reset · `fe70a0d` T11a model · `7eb0eba` T11b services · `170ca17` T11c pages · docs commits. Pushed to GitHub
- NEXT: T14 dashboards/announcements/timetable per the build order (owner may swap in T7e or T20)

### T11c Admissions pages (2026-11-01, 415 passed)
- New `apps/admissions/forms.py`: ApplicantForm (school-scoped class choices), ReviewForm/DecideForm (optional note; decision as hidden value from the admit/decline buttons), ConvertForm (admission number + section list limited to the target class)
- Views (all `role_required(owner, admin)`, school from request, `get_for_school_or_404`): list with search (name/reference/guardian) + status filter + pagination (25/page), create page reusing `form_page.html`, detail page whose action cards follow the status (review → decide → enrol → enrolled link to the Student / declined note), POST review, POST decide, GET+POST convert (thin over the T11b service; duplicate admission number keeps the applicant ADMITTED and rejects cleanly)
- URLs `admissions/...` (list/create/detail/review/decide/convert), nav "Admissions" for owner+admin only
- Tests `apps/admissions/test_views.py` (9): anonymous → login, teacher/bursar/parent 403, tenant isolation (foreign applicant list-hidden and detail 404), create assigns APP-0001 + audit, validation error stays on form, status-driven detail actions, admit → convert → student created + applicant converted, decline hides enrol, foreign manager gets 404 on review/decide with no audit
- Bugs caught along the way: view read `cleaned_data` before `is_valid()` (AttributeError on empty submit) — fixed by relying on Django's required-field error; test helpers default to TEACHER role (403s) — explicit `role="owner"` now
- CSS rebuilt (new templates compiled). `check` + `makemigrations --check` clean
- Commit `170ca17`

### T11b Admissions services (2026-10-30, 406 passed)
- `apps/admissions/services.py`: `create_applicant` (owner/admin; APP reference auto like invoices with a count fallback for non-numeric tails), `review_applicant` (applied → reviewed, optional notes), `decide_applicant` (reviewed → admitted/declined, audited with the decision), `convert_applicant` (admitted → converted; refuses missing target class or date of birth with friendly messages; creates the Student through the existing `students.create_student` service so the admission-number rule, class etc. stay one rule; class history row handled there; sets `converted_student` and audits `admissions.applicant_converted`)
- Shared `_advance` guard for review/decide refuses wrong states ("An applicant who is applied cannot move to admitted..."); ensure_owned on every service; audit inside the same transaction
- Tests `apps/admissions/test_services.py` (10): creation + auto-numbering + audit, non-numeric-tail fallback, teacher/bursar refused, foreign applicant refused, full pipeline (review → admit → convert produces a real student with class history), workflow order enforced, declined never converts, class/DOB guards, duplicate admission number leaves the applicant ADMITTED and unlinked (nothing half-built), notes saved
- Commit `7eb0eba`; `check`, `makemigrations --check` clean

### T11a Admissions Applicant model (2026-10-30, 396 passed)
- Owner agreed the T11 shape before build: internal applicant pipeline only (public online applications stay FUTURE with T21), auto references `APP-0001`-style per school, 5 workflow states
- New app `apps/admissions` in INSTALLED_APPS. Model `Applicant` (ValidatedSchoolModel): reference, names, sex, optional date_of_birth and target_class (nullable at intake, needed before conversion), guardian name/phone/email, address, notes, status (applied/reviewed/admitted/declined/converted), converted_student FK (PROTECT), created/updated
- DB rules: reference unique per school ignoring case (`Lower("reference")`), `converted_applicant_has_student` CheckConstraint (CONVERTED requires a linked student, constraint style `condition=` to dodge the deprecated `check=`); clean() rejects foreign-school target_class/converted_student; PROTECT everywhere
- Admin registered (school/status filters, reference+names search); `SchoolClassAdmin` gained `search_fields` so `autocomplete_fields` passes admin.E040
- Side lesson recorded (stale model instances): T7d failures fixed this session came from tests holding a user instance while a service re-fetched + saved it — remember to refresh before re-login in tests
- Tests `apps/admissions/tests.py` (7): default status, case-insensitive reference uniqueness per school, tenant isolation by id, foreign target_class/converted_student rejected, converted-without-student IntegrityError, link kept
- Migrations `admissions.0001_initial` applied. Commit `fe70a0d`; `check`, `makemigrations --check` clean

### Report card 2.0 HTML restyle approved by owner (2026-10-30)
- Owner browser-verified the rebuilt HTML report card (masthead, details card, subjects table, totals/position/average strip, write-ins, signature placeholders, grading footer) and approved it — report card 2.0 is now fully DONE (verified)
- `report-card-sample-esther.pdf` deleted from the project root after approval
- No code changes; docs only
- Commit: `docs: owner approved report card 2.0 HTML restyle`

### T7d adopted from an earlier session: admin password reset + forced change (2026-10-30, 389 passed)
- Uncommitted T7d work was already in the working tree from an earlier session; owner chose "test then commit" before T11 started
- Scope landed: `User.must_change_password` (indexed BooleanField, migration `accounts.0002`); `apps/accounts/services.py` `reset_password(request, membership)` — owner/admin only, generates a readable 12-char temporary password (no 0/O/1/l/I so it survives being typed from paper), sets the flag, audits `accounts.password_reset` WITHOUT the password; view `member_password_reset` on the Parents list (POST-only, audit, safe `next` redirect); POST-only force-change page `accounts:force-change/` with `SetPasswordForm`, clears the flag after a strong password, audited `accounts.password_changed`; `ForcePasswordChangeMiddleware` after AuthenticationMiddleware keeps flagged users on the change page (logout + static exempt)
- Two failing tests fixed: they force-logged-in a STALE user instance carrying the pre-reset password attribute while the service had re-fetched and saved the user (`refresh_from_db` before `force_login`); the app logic was never wrong — a password reset SHOULD invalidate existing sessions. Debug prints removed from the middleware
- Tests `apps/accounts/test_password_admin.py` (8): temp password works + old one dead, audit without the password, admin may reset / teacher + bursar 403, foreign membership 404, flagged user kept on the change page, full flow (weak refused / strong accepted / flag cleared), mismatch changes nothing, anonymous → login
- Commit `52a3727`; suite 389 passed at the time, `check`/`makemigrations --check` clean

### Report card 2.0: ranking, totals, attendance + matching HTML design (2026-10-30, 381 passed)
- Owner reported the "Open full report card" HTML page looked different from the downloaded PDF — only the PDF had been redesigned. This task closes that gap
- **New School fields** (migration `schools.0003`, applied): `motto` (shown on report cards) and `show_ranking` (per-school toggle, the deferred ranking decision; default False, admin field label "show positions on report cards")
- **PDF redesigned** (`templates/results/report_card_pdf.html`) to the updated design canvas: Public Sans vendored to `static/fonts/` (regular/semibold/bold, `@font-face`; WeasyPrint gets `base_url=static/` so relative font paths resolve), teal top band, logo box + school block (with motto) + photo box masthead, "TERMINAL REPORT SHEET" title band, pupil details card (name, class, session, term, admission no., attendance, next-term start date), subjects table with per-component `/max` headers, summary strip (total score / average / position in class / promoted-to blank line), write-in rows (conduct/attitude/interest, teacher/head/parent remarks), signature boxes (placeholders — owner chose hand-signing for now; upload deferred to T20), grading-scale footer with ranges
- **View additions** (`_report_card_context`, shared by HTML + PDF so they cannot drift):
  - `_rank` + `_ordinal`: standard competition ranking (ties share a position: 90/75/75/61 → 1st, 2nd, 2nd, 4th), drive-by peer percentages from published SubjectResults
  - subject `total_max` from the `weights_snapshot` maxes; grand `total_score`/`total_max` across published subjects
  - attendance = present days of the pupil for the period from AttendanceSession/AttendanceRecord (own class, section registers only; other classes never count)
  - `next_term` = the session's next period by start date; grade chips mapped from the school's own scale (top grade green, then teal, then amber, else neutral — colour follows the scale, never a hard-coded letter)
- **HTML report card page** (`templates/results/report_card.html`) rebuilt to mirror the PDF: same masthead/details/table/strip/write-ins/signatures/footer structure in Tailwind (mobile-first, 2-col details, horizontal scroll on the table, `print:hidden` toolbar kept)
- Tests `apps/results/test_views.py` +5: ranking with tied pairs (1st/2nd/2nd/4th, class position "x of 4"), ranking hidden when toggle off, totals 160/200 average 80.0, attendance counts only the pupil's own registers, next-term date prefill. `_manager_member` now makes unique usernames
- Sample render exists as `report-card-sample-esther.pdf` (root, uncommitted) for the owner to view; delete after checking
- Commit `de606ef`; `check`, `makemigrations --check`, CSS rebuild clean

### Session close (2026-10-30) — parent portal closed, everything pushed
- Owner tested the whole portal live: parent1 dashboard → My children → child page (results with grades, fees balances) → Open full report card → Download PDF
- Owner feedback fixed two bugs on the spot:
  - child page grade column was blank (template used `grade_label`, field is `grade`) — regression test added (`aa76966`)
  - PDF signature labels too small — now 11.5pt bold with signature space (`a9ca2f3`)
- Dev data: all 11 Primary 1 A result sheets published through the real workflow via a seed script (per-subject teacher assignments had to be reused/created; primary-3 sheets left in draft on purpose). parent1 also linked to Esther FSS/2026/001 (has results). Seed data stays "active" (non-generic teachers existed); per-subject TeacherAssignment assign reuse; other classes untouched
- Commits this session: `58ebb6a` P1 My children · `fca9ab4` office parent accounts · `5f897d0` P2 child page · `3bc3ca4` P3 report card access · `4b71daa` docs · `aa76966` grade fix · `a9ca2f3` PDF labels — all pushed to GitHub (`c244484..a9ca2f3`)
- Test suite: 376 passed; `check` and `makemigrations --check` clean
- NEXT: pick T14 / T7e / T7d / T11 / T20 (details in "Next task" above)

### Parent portal P1-P3 + office parent accounts (2026-10-29, 376 passed)
- Owner chose the parent portal first, built in steps with owner browser-testing after each step ("after each i will test it")
- **P1 `apps/portal`** (commit "feat: parent portal step 1"): `/portal/` children page, `role_required(PARENT)`; children come from GuardianLink of the ACTIVE membership only (`children_for` selector); nav "My children" for parents only. Owner verified live. Demo parent seeded for testing: username `parent1` / password `Parent@1`, linked to Aishat Adekunle FSS/2026/003
- **P1b office parent accounts** (owner verified): Parents list (`students:parent_list`, search + child count) and Add parent account (`students:parent_create` → `create_parent` service: role-guarded, username uniqueness case-insensitive, password validated, audit `parent.account_created`, creates Membership with Parent role); children are then linked via the existing student detail "Add guardian". Owner registered a parent + link by themselves
- **P2 child page** (owner verified): `/portal/children/<pk>/` — read-only: class card, average of published subject percentages, fees owed card (amber when > 0), published-results table (per subject total/%/grade from PUBLISHED sheets via new `published_subject_results(school, pupil, period)` selector in `apps/results/services.py` — reused read source for report card and portal), fees table reusing the fees module's exact subquery totals (item_total/paid_total/balance_due → same numbers as bursar sees); no payment recording for parents
- **P3 report card for parents** (NOT yet verified): `student_report_card(_pdf)` now `@report_access` = SCORE_ROLES + PARENT; `_report_card_context` allows PARENT only with a GuardianLink for that pupil in the active school (else 403); teachers keep the assignment rule, managers pass, bursar 403. Child page gains "Open full report card" + "Download PDF" buttons (current period)
- Tests: apps/portal (20), 11 new in apps/students/test_parent_management.py. Tenant isolation: another parent's child 403, foreign-school child 404, two-schools-one-user leak test, parents-only report card rule
- Known leftover: all existing results tests still pass (the old report-card "parent 403" test parent has no GuardianLink, so it remains 403)

### T12d: PDF report cards with WeasyPrint (2026-10-29, 345 passed)
- Owner asked the PDF to "print the result area only, look like a real standard result". Setup: `weasyprint==70.0` pinned in `requirements/base.txt`; the Windows GTK runtime (needed by pango) was installed once and its bin folder appended to the user PATH — app code stays portable (CI/Render just install libpango via the updated `.github/workflows/tests.yml`)
- Data refactor: `apps/results/views.py` now has `_report_card_context` (pupil/period fetch, teacher-assignment rule, published sheets, scores by component name, component `columns` from the `weights_snapshot` union, average, scale legend) used by BOTH the HTML card and the PDF, so they can never drift
- New view `student_report_card_pdf` → `/results/students/<pk>/report-card/<pk>/pdf/` (name `results:report_card_pdf`): renders `templates/results/report_card_pdf.html` (standalone A4 document, serif fonts, school header with address/phone, TERMINAL REPORT title band, pupil details box, bordered subject table S/N | Subject | component columns | Total | % | Grade | Remark, average row, grading-scale line, Class Teacher + Head/Principal signature lines and a validity stamp) and streams `application/pdf` with `attachment` filename like `report-card-FSS-2026-006-first-term.pdf`
- Rules kept: only PUBLISHED sheets appear (status filter in the query), tenant scoping via `get_for_school_or_404`, teacher needs an assignment for the pupil's class, parent/bursar 403 — all covered by 3 new tests (`apps/results/test_views.py`: real `%PDF-` magic + disposition, unpublished → still a valid PDF with the no-results note, parent 403 + foreign school 404)
- `report_card.html` gained a "Download PDF" button; a separate "PDF" button on published sheet rows was removed at the owner's request (commit `80a01cc`) — the office opens the Report card first, the PDF download lives inside it; WeasyPrint/fontTools loggers set to WARNING in `config/settings/base.py` (the font-subset spam was drowning the console); CSS rebuilt (now minified, hence the big output.css diff)
- WeasyPrint prints a one-time deprecation warning about HarfBuzz-Subset — harmless; will be handled at deployment
- Live check: generated `report-card-sample.pdf` from the pilot school's two published sheets via the dev DB test client

### Workflow notifications at every result step (2026-10-29, 342 passed)
- Owner verified the send-back note live and asked for notifications across the whole workflow. New rule (owner approved): each action tells the OTHER side — who acts next or who is waiting
  - `submit_sheet` (teacher) → all active owner/admin memberships: "Mathematics result submitted for review" + link (new `office_memberships(school)` helper in `apps/notifications/services.py`)
  - `review_sheet` admin → the sheet's submitter: "reviewed, awaiting approval"
  - `approve_sheet` admin → the submitter: "approved, can be published"
  - `publish_sheet` admin → the submitter + assigned teacher(s) (dedup combined): "published, report cards ready"
  - The acting admin never gets their own note; when an admin submits a sheet themselves they are skipped too
- `_advance` grew `note_verb`/`recipients`/`note_body` params so the three step-services share one notify block; classes label in titles moved to `_class_label(sheet)` (reused by send-back)
- No model/migration changes; no template changes
- Tests `apps/results/test_services.py` +3 (submit pings the office not the teacher; a full walk yields 5 notes with the right recipients per kind; a school B admin gets nothing and the school A office gets the submit note). Updated 1 old test (send-back scenario now also shows the submit note)

### Session close (2026-10-29) — where to resume
- Commits this session: `3061ee7` (T12c results pages), `12bf745` (submit_sheet FK fix), `9e8ff8c` (send-back notification + notifications app). 339 tests passing, checks clean, CSS rebuilt
- Owner verified live during the session: they hit the submit bug in the browser (fixed + regression test); the rest of T12c/T12b is STILL DONE (unverified)
- Resume point: owner browser verification of T12c + notifications, then T12d PDF report cards (WeasyPrint) — details in "Next task" above

### Send-back notification + notifications foundation (2026-10-29, 339 passed)
- New app `apps/notifications`: `Notification` (ValidatedSchoolModel: recipient Membership, kind `<area>.<verb>` like audit, title, body, optional url, is_read, index on school+recipient+is_read); migration `notifications.0001` applied
- `services.py`: `notify_memberships(request, recipients, kind, title, body, url)` — deduplicates, skips the actor, refuses memberships of another school; `unread_count(request)` for the bell
- Hooked into `apps/results/services.py` `send_back`: on the same transaction the assigned subject teacher(s) (via the new shared `teaching_assignments_for_sheet(sheet)` helper) plus the sheet's previous submitter are notified — "Mathematics result sent back (Primary 3 A)" with body + link to the sheet. The actor (admin) never receives their own back-action
- `ensure_can_edit_scores` refactored onto the same helper so score-entry scope, results-home teacher listing and send-back recipients use ONE rule (no more triple-duplicated Q logic)
- Views: `/notifications/` list (own notes only, 50 latest, mark one read / mark all read), added `membership_required` decorator in `apps/schools/permissions.py` (any role); context processor `unread_notifications` for the top bar
- Templates: bell button with red unread badge next to Log out in `base.html`; `templates/notifications/list.html` (New/Read chips, Open link to the sheet, print-safe reuse of shared components); nav item "Notifications" for every role
- Tests: apps/notifications/test_services.py (4: actor skipped, dedup, cross-school skipped, count per membership), test_views.py (6: login, own-only, badge clears, cannot mark another member's, mark all, foreign id no crash); results test_services.py +2 (send_back notifies the assigned teacher with title/url/not the admin; a non-teacher submitter also receives one)
- No results-model changes; the email/push/SMS channel stays FUTURE (today it is the in-app bell only)

### Fix: submit_sheet crashed on the live flow (2026-10-29, 327 passed)
- Owner found the bug in the browser: `ValueError: Cannot assign "5": "SubjectResult.student" must be a "Student" instance`. `submit_sheet` looped `values_list("student", flat=True)` and fed the raw integer into `_recompute_student`, which assigns it to the `SubjectResult.student` FK
- Fix: fetch `Student.objects.for_school(sheet.school).filter(pk__in=student_ids)` and recompute per instance (`apps/results/services.py`); caught late because all service tests happened to pre-create results through `save_score` — new test `test_submit_grades_pupils_whose_scores_were_created_directly` reproduces the bare `Score.objects.create` path (percentage 75.0, grade A)

### T12c Results pages (2026-10-29, 326 passed)
- New `apps/results/urls.py` (namespace `results`), `apps/results/views.py`, `templates/results/home.html`, `sheet.html`, `report_card.html`; nav entry "Results" (owner/admin/teacher) in `apps/core/navigation.py`; `config/urls.py` adds `results/`
- Home: term picker reuses new `apps/academics/selectors.py` helpers `session_periods` + `current_or_last_period` (previously duplicated inside fees views — fees can switch to them later); teacher listing uses the same assignment rule as `ensure_can_edit_scores` (class-wide assignment also shows section sheets)
- Sheet page: score-entry form is one form per pupil row (values post as `score_<component_pk>`); post-submit states show the `weights_snapshot` captured at submission with live-score lookup by component name, so later config changes cannot distort what was graded; score inputs only on DRAFT; published sheets get a per-pupil "Report card" link
- Workflow buttons: submit visible to the assignee on draft; review/approve/publish/send-back manager-only (403 via decorator, service re-checks); every POST action goes through `role_required` + the service's own `require_role`
- Report card: published sheets only (status filter in the query, never a display filter); shows per-subject breakdown (component), total, %, grade, remark, the grading-scale legend from `scale_snapshot`, and the mean of subject percentages; printable (print button + `print:hidden`), like the fee receipt
- Access decisions: teacher must have a TeacherAssignment for the pupil's class (section matching) to open a report card; parent/bursar get 403 for now — parent portal comes later; report-card teacher check is view-level only
- Tests `apps/results/test_views.py` (21): login/parent/bursar 403, admin home lists sheets, teacher sees only assigned subjects, class-wide covers section sheets, teacher 403 on foreign sheet, draft shows inputs / submitted does not, admin saves a row (Score + SubjectResult + audit), over-max friendly message, foreign pupil refused, teacher fills + submits, edit after submit refused, teacher cannot review/approve/publish, admin walks to PUBLISHED, approved sheet cannot be sent back, published sheet links report cards, report card shows 75.0 + scale legend, ignores unpublished sheets, cross-school 404, parent 403
- No migrations; `check` and `makemigrations --check` clean; CSS rebuilt

### Session close (2026-10-28)
- T12a verified by owner; pilot results config seeded; T12b services built (305 passed); T12c prepared (`components_for_sheet` made public, 48 results tests pass). Pushing to GitHub; T12c pages continue next session.

### T12b Results services (2026-10-28, 305 passed)
- `apps/results/services.py`: `save_score`, `submit_sheet`, `review_sheet`, `approve_sheet`, `publish_sheet`, `send_back`; helpers `ensure_can_edit_scores` (teacher needs a TeacherAssignment for the sheet's session/class/subject; class-wide assignment covers section sheets), `_applicable_components` (school-wide + class level), `_active_scale` (first active scale of the session), `_recompute_student` (weighted percentage, total, grade, `scale_snapshot`)
- Rules: edits only on DRAFT (send back first after submission); submit requires every scored pupil to have every applicable component (stops inflated partial percentages); grade lookup = highest boundary ≤ percentage; workflow advance owner/admin only, strict order; send_back from submitted/reviewed only
- Audit actions: `results.score_saved` (with previous value), `results.sheet_submitted`, `results.sheet_reviewed`, `results.sheet_approved`, `results.sheet_published`, `results.sheet_sent_back`
- Tests `apps/results/test_services.py` (24): role matrix (assigned/unassigned/wrong-subject teacher, parent/bursar, owner/admin), section vs class-wide assignment, cross-school refused, max-score and level-scope refusals, recompute on resave (66.7 B → 96.7 A), submit completeness, snapshot contents, workflow order enforcement, teacher cannot review/publish, send-back rules, boundary math (86.0 → A)
- Bugs caught by tests: aliasing bug — `score = previous` then `score.value = new` mutated `previous` before the audit line, so `previous` logged the NEW value (fixed by capturing `previous_value` first); audit timestamps within the same second make `.latest()` unstable in tests (order by `-id`)
- No migrations. Note: `sheet.reviewed_by` is a Membership, so tests use `.role` on it

### Pilot results config seed (2026-10-28, T12a verified by owner)
- Owner verified T12a (browser + tests: 284 passed). Filled the pilot school's results config by script so the owner can feel it without manual entry:
  - Grade scale "Primary Grading Scale" (2026/2027): A 70 Excellent, B 60 Very Good, C 50 Good, D 45 Fair, F 0 Needs improvement
  - Assessment components (school-wide, all levels): First Test 20/20, Second Test 20/20, Examination 60/60 (classic 40% CA + 60% exam; editable in admin)
  - 11 draft ResultSheets (First Term 2026/2027) — one per subject for Primary 1 A
  - 33 Scores on the Mathematics sheet for its 11 pupils (seed 42, no pupil below 40% of a component); totals/grades left empty on purpose — computing them is T12b
- Note: a pre-existing "WAEC" scale (owner's admin experiment) contains a boundary labelled "70" from 50% — harmless, owner may delete it in admin
- Seed script (throwaway, in temp): no audit entries, like the earlier pupil seed; NOT real school data — replace before live use

### T12a Results models (2026-10-28, 281 passed)
- New app `apps/results` registered in settings. Models (all `ValidatedSchoolModel`):
  - `GradeScale` per session (is_active archive flag) + `GradeBoundary` (grade label, min_percent 0-100, remark, optional points; unique label + unique boundary start per scale)
  - `AssessmentComponent` per session, school-wide by default or scoped to one Level; name, max_score, weight (positive)
  - `ResultSheet` per (period, class/section, subject) with 5-state workflow (draft/submitted/reviewed/approved/published), actor FKs (submitted/reviewed/approved/published_by) and `weights_snapshot` JSON captured at submission time
  - `Score` (sheet, student, component, value) — one per pupil/component, session must match the sheet's term, pupil must be in the sheet's class/section
  - `SubjectResult` (sheet, student) — computed total, percentage, grade label + remark + `scale_snapshot` JSON (TECH: snapshot of grading used)
- Migration `results.0001_initial` created and applied
- Tests `apps/results/test_models.py`: 24 tests — config uniqueness/percent ranges, tenant isolation (session/class/subject from another school rejected), sheet uniqueness incl. two sections, score rules, snapshots
- Side fix: `apps/fees/test_services.py::test_payment_date_cannot_be_in_the_future` was pinned to `TODAY = 2026-10-26`; once the real calendar passed the 26th it stopped testing the rule. Now computes the future date from `timezone.localdate() + timedelta(days=2)`
- Decisions (owner approved 2026-10-28): config per session (like fees); keep all 5 workflow states; ranking = per-school toggle; report card HTML first, PDF (WeasyPrint) in T12d
- Known issue: fees `CheckConstraint(check=...)` deprecation warnings still present (existing debt; new app uses `condition=`)
- Owner re-audit (2026-10-28) caught two bugs before they reached T12b: the `submitted_needs_submitter` check constraint was inverted (allowed submitted-without-submitter, blocked draft-with-submitter) — replaced with `submitted_or_later_needs_submitter` in migration `results.0002`; and nothing stopped a score from exceeding its component's max score — `Score.clean()` now rejects it. Added `admin.py` for manual verification and 3 more tests (27 in the app)

### T13 Finance complete (2026-10-26, 257 passed)
- T13a `apps/fees/models.py`: FeeItem (per session, charged per term / per session / optional), FeeItemPrice (amount per class), Invoice (number INV-xxxx per school, status unpaid/part_paid/paid, issue/due dates), InvoiceItem (description+amount snapshot so later fee changes never alter issued invoices), Payment (amount, method cash/transfer/POS/cheque, reference unique per school case-insensitive, received_by, paid_on). DB constraints: unique numbers/references, positive amounts, due >= issue
- T13b services: `create_fee_item`, `set_price` (owner/admin), `generate_invoices` (per term; skips pupils already billed, optional items never auto-billed, per-session items only in the term that starts the session; only active pupils; only classes with a price), `record_payment` (finance roles; atomic with select_for_update; idempotent on reference — same reference returns the same payment; refuses overpay, future dates, missing reference; updates status; audits `fees.payment_recorded`)
- T13c pages styled from the fees PNGs: Fees overview (Expected/Collected/Outstanding/Collection rate stat cards + per-class table, term picker), Fee structure (add item, set per-class prices, price tags), Invoices (search + class + status filters incl. Overdue, Generate invoices, totals via subquery annotations `item_total/paid_total/balance_due`), Invoice detail (items, balance, record payment form, payments with receipt links), Payments list, printable Receipt (school header, receipt no., previous/remaining balance, print button). Nav "Fees" for owner/admin/bursar
- Decisions: fee structure defined per session (schools can copy it for a new session later); receipts use reference as receipt number; Paystack/online payments stay FUTURE
- Bugs caught by tests on the way: annotation named `balance` collided with the property (renamed `balance_due`), double-counting Sum over items x payments (replaced with subqueries), forms.py missing SchoolClass import, previous-balance math
- Dev DB now has 73 First Term invoices (all active pupils) + one part payment FSS-RCPT-001 for owner demo; `django.contrib.humanize` enabled for ₦ thousands separators
- Known debt: `CheckConstraint(check=...)` deprecation warnings (Django 6) in fees models — switch to `condition=` later


### Attendance styled to the canvas (2026-10-26, 228 passed)
- Design canvas added to repo (62 screens + design system); workflow decision: style each module as we build it, tokens/components change in one place
- `static/src/input.css`: new tokens muted #475569, ok #15803D, bad #B91C1C, warn #B45309, info #1D4ED8; `status_chip.html` now uses them (with optional dot)
- Attendance home matches "Attendance overview.png": stat cards (Present %, Registers taken x of y, Absent), desktop table (Class, Teacher, Register chip Taken/Not taken, Present "n of m", Open/Mark actions), phone cards below md; day stats and per-register present counts computed from real data in the view
- Register page matches "Attendance register (phone).png": teal header band, Present/Absent/Late/Excused count chips, pupil cards with one 44px P/A/L/E square per status (filled green/red/amber/slate when active), remark input; instant save per tap kept (deliberate difference from canvas batch save), read-only shows chips
- Decision: statuses keep full words in read-only chips (design rule: never colour alone); canvas "Not marked" wording became "Not taken"
- Test wording updated ("Not marked" -> "Not taken"); live-checked with owner and teacher data


### Attendance permission: form teacher only (2026-10-26, 228 passed)
- Owner decision matches real school operation: the daily register is marked by the form teacher; subject teachers will get their own "my classes + subjects" score views in T12
- `ensure_can_mark` keeps only the ClassTeacher check; `_my_classes` in views returns only form classes (TeacherAssignment filter removed); service refusal message now `"Only the form teacher of this class or section can mark its register."`
- New test: a subject teacher who is not the form teacher is refused (and no register/audit is created)
- Live check: mrs_ogunleye (2 form classes, 7 subject assignments) now sees only Primary 1 A and Primary 6 A on the Attendance home


### T10c Attendance pages (2026-10-26, 227 passed)
- URLs `/attendance/` home, `/attendance/open/` POST, `/attendance/registers/<pk>/` page, `/attendance/registers/<pk>/mark/` POST
- Home: grid of classes/sections for a chosen day (owners/admins see all classes; teachers see only their form classes and the classes whose subjects they teach), day picker, Marked/Not-marked chips, Open register buttons; future days cannot be opened
- Register page: pupils with surname first, one-tap status buttons (four small POST forms), remark column text, daily summary chips; outside the current session the page is read-only
- Nav entry "Attendance" (owner, admin, teacher); `templates/attendance/home.html` and `register.html` reuse shared components; `static/css/output.css` rebuilt
- Tests 9 view tests (login, 403 parent, admin opens, teacher class filtering, mark absent with remark, cross-school pupil refused, future day refused, read-only view). Live shell check: admin home shows 9 marked registers for today (seed data), teacher home shows own classes only
- Owner should next look in the browser; a day with no register (e.g. change the picker) shows Not-marked chips to try opening one

### T10b Attendance marking services (2026-10-26, 218 passed)
- `apps/attendance/services.py`: `open_register` (owner/admin any class; a teacher only their own class or section; creates the register once per day and fills every pupil with Present; re-opening returns the existing register), `mark_student` (create or change one pupil's line, audit shows previous and new status; refuses pupils of other classes/sections; old-session registers are read-only)
- Permission rule newly agreed: a teacher may mark if they are the CLASS TEACHER (form teacher, with section match) OR a SUBJECT TEACHER of that class in the current session; owner/admin always can
- `conftest.py`: `make_request` now accepts an existing membership (backward compatible)
- Tests `apps/attendance/test_services.py` (10): role matrix (teacher assigned/unassigned, parent/bursar refused, admin allowed, cross-school refused), idempotent open, audit entries, cross-class pupil refused, old-session lock
- No migrations; all checks clean

### T10a Attendance data model (2026-10-26, 208 passed)
- New app `apps/attendance`: `AttendanceSession` (the daily register: class plus optional section, date, session, optional term, the member who opened it; unique per class/section/day per session; dates must fall inside the session and the chosen term) and `AttendanceRecord` (one line per pupil: present/absent/late/excused plus remark, unique per pupil per register)
- Rules in `clean()`: related records same school, section belongs to its class, register date inside session/term; foreign-school pupils refused; indexes on school+date etc.
- Tests `apps/attendance/tests.py` (9): one register per day, per-section split allowed, per-school independence, one line per pupil, tenant isolation, date bounds, all four statuses
- Deferred on purpose: percentages/statistics (T10c), teacher-permission checks (T10b services), auto-remaining-absent policy (school decision)

### T9c Student pages and a history bug fix (2026-10-26, 199 passed)
- `apps/students/forms.py`: StudentForm (create with admission number), StudentDetailForm (edit; admission number locked), GuardianForm (only that school's parents, excludes already-linked)
- `apps/students/views.py`: list with q/status/class filters and pagination (25/page), create, edit, detail, status (POST only), move, guardian add/remove. All owner/admin only, thin views over services
- URLs `/students/...`; nav entry "Students" for owner and admin; templates `students/student_list.html`, `students/student_detail.html` reuse the shared components
- Bug fixed in service: creating or moving a student in a school with no current session no longer crashes (history row is skipped until a current session exists)
- 13 view tests; `static/css/output.css` rebuilt; live check: list 200 with pagination, detail/edit/create 200, teacher 403, foreign school 404
- Next: UI agent may restyle the students screen set with the design canvas

### T9b Student services (2026-10-26, 186 passed)
- `apps/students/services.py`: `create_student` (admission number friendly message, auto class-history row for the current session), `update_student` (audit shows old and new values), `set_student_status`, `move_student` (updates history row in the same transaction), `add_guardian` (Parent role enforced, only one primary guardian per student), `remove_guardian`
- All services: owner/admin only via `require_role`, school from the request, other-school records refused via `ensure_owned`, audit entry in the same transaction
- Tests: `apps/students/test_services.py` (10). Suite: 186 passed; `check` and `makemigrations --check` clean

### Pilot school student seed (2026-10-26)
- 72 placeholder pupils filled for Five Star Model School (12 per class, Primary 1-6, admission numbers FSS/2026/001-072, Yoruba names, Saki addresses, session-appropriate birth dates, sections assigned, StudentClassHistory rows for 2026/2027)
- Fixed period typo "Firsr Term" to "First Term" and made First Term the current period (was wrongly Second Term in October)
- IMPORTANT: these are realistic placeholders, not the real school register; must be replaced with the school's actual pupil list before live use
- Shell seeding writes no audit entries (no request context); acceptable for seed data

### T9a Students data model (2026-10-26, 176 passed)
- New app `apps/students` (in INSTALLED_APPS): `Student` (names, sex, date of birth, address, admission number unique per school ignoring case, status: active/graduated/withdrawn/suspended/transferred, current class and optional section), `GuardianLink` (student + parent Membership, relationship mother/father/guardian, is_primary flag, unique per student, guardian must have Parent role in that school), `StudentClassHistory` (student + session + class + optional section, one row per session)
- Rules in `clean()`: section belongs to its class, related records must be from the same school; all FKs are PROTECT; indexes on school+status and school+names
- Deferred on purpose: photos (T20), promotion logic, auto-generated admission numbers (stored string for now)
- Admin registered with school/status/class filters; tenant isolation tests added (school A cannot see school B students, foreign class/section/guardian refused)
- Files: `apps/students/main models.py`, `apps/students/admin.py`, `apps/students/tests.py`, migration `students.0001_initial`
- Test result: 176 passed; `makemigrations --check` clean; `manage.py check` clean

### School profile fields and real data (2026-10-26, 165 passed)
- `apps/schools/models.py`: `School.SchoolType` choices (primary, jss, ss, mixed; default primary) and optional `country`, `state`, `lga`, `town` CharFields
- Migration `schools.0002_school_country_school_lga_school_school_type_and_more` applied
- `apps/schools/admin.py`: fieldsets (basic/contact/location/status), `school_type` in list display and filters
- `apps/schools/tests.py`: 3 new tests (default type, JSS type accepted, location fields saved). Suite: 165 passed
- Real data filled via shell for Five Star Model School (address 12 Isale Taba Road, phone, email, town Saki, LGA Saki West, Oyo State, Nigeria); other schools left as they are
- Manual check: admin change page renders with all fields and saved values (status 200)

### T8b-2 Views for classes and subjects (verified: 162 passed on 2026-10-26)
- Owner ran the full suite: 162 passed (13 classes view tests, 8 subjects view tests included)
- Codes and docs reorganized: root now holds `AGENTS.md`, `PROJECT_STATE.md`, `Requirements.md`; older document copies moved to `ARCHIVE/` (NEW CHNAGE copy, RULES copies, root duplicates). Nothing deleted
- T8b-2 code still needs to be committed and pushed (OpenCode session)

### T8b-2 Views for classes and subjects (code as provided)
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
- `apps/fees/views.py` keeps its own `_current_period`; the shared helpers now live in `apps/academics/selectors.py` (`session_periods`, `current_or_last_period`) — fees can switch to them in a later cleanup
- Report-card access for teachers is one rule for now (any assignment for the pupil's class); per-subject scoped report-card access can be tightened if the owner wants it
- Report card shows the mean of subject percentages; class position/ranking is now built behind `School.show_ranking` (default off; owner can enable per school in admin)
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
    portal/     parent portal (My children, child page)
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
