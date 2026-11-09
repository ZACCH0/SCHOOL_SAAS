# REQUIREMENTS

Living checklist for the School Management SaaS. Tick items only when built **and tested**.
Types: **REQ** = product requirement, **TECH** = implementation rule, **FUTURE** = later idea (not MVP).

## 1. Product

- REQ: Multi-school SaaS for Nigerian primary and secondary schools.
- REQ: Pilot school (Saki, Oyo State) currently runs Primary 1-6. System must also support JSS 1-3 and SS 1-3, activatable later without rebuilding.
- REQ: Student population can grow continuously (hundreds to thousands).
- REQ: Everything school-specific is configurable by the school (classes, sections, subjects, sessions, periods, fee items, grade scales, assessment components, student/teacher fields). Nothing hard-coded.
- REQ: Ovidi is a benchmark only. Never copy its code, branding, UI, text or database.

## 2. Roles (server-side enforced)

- [ ] Platform Super Admin (not the same as a school admin)
- [ ] School Owner
- [ ] School Admin
- [ ] Teacher (only authorized classes/subjects)
- [ ] Bursar/Accountant (finance access only)
- [x] Parent/Guardian (one account, multiple children, own children only) — DONE (verified) 2026-10-30: office creates parent accounts; "My children" + child page (published results + fee balances, read-only); report card HTML + PDF via GuardianLink; role-guarded, own-school only
- [ ] Student (own records only)

## 3. Foundation (current phase)

- [x] Project structure, split settings, `.env` secrets, PostgreSQL, pytest config
- [ ] Custom User (username login, optional email and phone) *(built; confirm tests pass)*
- [ ] School (tenant) model
- [ ] Membership (user, school, role)
- [ ] Tenant-scoped queries/managers and tenant isolation tests
- [ ] Academic Session and Academic Period (configurable, not hard-coded)
- [ ] Roles and permission checks on the backend

## 4. Modules (build in this order, one at a time)

1. [x] Classes, sections, levels (Primary/JSS/SS), subjects, teacher assignments — DONE (verified) T8: sections as own table, teacher assignments per session, owner-verified in browser 2026-10-26
2. [x] Students and parents (parent with many children; history kept across promotions; statuses: active, graduated, withdrawn, suspended, transferred) — DONE (verified) T9 + office parent accounts, owner-verified 2026-10-29
3. [x] Attendance (present, absent, late, excused; statistics; history) — DONE (unverified in browser) T10 2026-10-26; form-teacher-only marking
4. [x] Admissions (application, review, accept/reject, admission number, convert to student) — DONE (verified in browser) 2026-11-01: internal pipeline (public online form stays FUTURE with T21); auto APP-xxxx references per school; 5 states applied → reviewed → admitted/declined → converted; enrolment keeps the school's manual admission-number rule and builds the class history row; owner/admin only, tenant isolated, audited, 26 tests
5. [x] Assessments and results (configurable components and grade scales; calculated totals/grades/remarks; configurable ranking) — built and owner-verified 2026-10-29; ranking built 2026-10-30 behind `School.show_ranking` (per-school toggle, HTML restyle owner-approved 2026-10-30)
6. [x] Result workflow: Draft, Submitted, Reviewed, Approved, Published; no silent edits after publish; audit record for changes — DONE (verified) 2026-10-29, with workflow notifications
7. [x] Report cards (PDF) — DONE (verified) 2026-10-29 (WeasyPrint A4 terminal report); redesigned + matching HTML page 2026-10-30
8. [x] Finance: fee structure, invoice, invoice items, payments, payment allocation, receipt, balance (full and partial payment, manual recording) — DONE (unverified in browser) 2026-10-26
9. [x] Dashboards (admin, teacher, parent) using real data only — built 2026-11-04 (DONE, unverified in browser): one /dashboard/ URL, role sections for owner/admin, bursar, teacher, parent; current-term scoped, tenant isolated, 10 tests; no charts (stat cards only)
10. [ ] Announcements and in-app notifications — announcements DONE (verified in browser) 2026-11-03 (built 2026-11-02): audience notices (everyone/staff/teachers/parents), bell fan-out via notifications app, archive takedown; in-app notifications to individuals existed since the results workflow
 11. [x] Timetable — built 2026-11-03, verified in browser by owner 2026-11-04: per-class grids for the current session; slot = class (optional section override), subject or labelled break/assembly, day + start/end; overlaps refused (class-wide vs section rules); teachers derived from TeacherAssignment (section-exact preferred); archive/restore, never delete; copy to next session (service); managers build, teachers read only their classes + personal "My timetable" page; 36 tests
12. [x] Documents with controlled access — built 2026-11-04, owner-verified in browser (DONE, verified): owner/admin upload + archive, audiences managers/all staff/everyone, server-checked downloads (no direct media URLs), extension+size guards, tenant isolated, audited, 21 tests (local storage; Cloudinary/R2 planned for T18)
13. [ ] Analytics (student, academic, finance, attendance)
14. [x] Audit log — read-only page built 2026-11-04, owner-verified in browser (DONE, verified): owner/admin only, newest first, search + date range, paginated 25/page, tenant isolated; the recording itself existed since H3
15. [ ] REST API (only where it adds value)
16. [ ] Production deployment (Render), backups, HTTPS

## 5. Technical rules

- TECH: Every school-owned record has a school link (direct or through a safe relationship); queries are school-scoped; URL/API lookups verify the school and the user's permission.
- TECH: Archive, do not delete, configuration that is in use (classes, fee items, grade scales).
- TECH: Results store a snapshot of the grade scale and weights used.
- TECH: Money uses `DecimalField`, database transactions, payment allocations, and idempotent payment references. Never overwrite financial history.
- TECH: Pagination, `select_related`/`prefetch_related`, and indexes for list pages.
- TECH: Tests for tenant isolation, permissions, parent-child access, result and fee calculations.
- TECH: Secrets only in environment variables. Separate development and production settings.
- TECH: No fake dashboard data in the finished product.
- TECH: Stack: Python, Django 5.2, DRF, PostgreSQL, Django Templates, Tailwind, Alpine.js, Chart.js, pytest. Add Paystack, WeasyPrint, Celery/Redis, Cloudinary, drf-spectacular only when needed.

## 6. Future ideas (not MVP)

- FUTURE: Online payments (Paystack), SMS/WhatsApp/email, online admissions, subscriptions and school billing, parent/student mobile apps, boarding, transport, hostel, library, payroll, e-learning, AI analytics, React frontend if justified.

## 7. Open questions to settle through configuration, not blocking

- Exact assessment components and weights at the pilot school
- Grade boundaries and whether ranking is used
- Fee items, class-based differences, discounts, instalments
- Required student fields