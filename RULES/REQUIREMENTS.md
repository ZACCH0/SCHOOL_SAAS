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
- [ ] Parent/Guardian (one account, multiple children, own children only)
- [ ] Student (own records only)

## 3. Foundation (current phase)

- [x] Project structure, split settings, `.env` secrets, PostgreSQL, pytest config
- [x] Custom User (username login, optional email and phone)
- [x] School (tenant) model
- [x] Membership (user, school, role)
- [x] Tenant-scoped queries/managers and tenant isolation tests
- [x] Academic Session and Academic Period (configurable, not hard-coded)
- [x] Active school resolution and backend role check (`role_required`) *(unverified: 33 tests)*
- [ ] Login, logout, school chooser, dashboard landing *(code given; verify 49 tests)*
- [ ] Password reset

## 4. Modules (build in this order, one at a time)

1. [ ] Classes, sections, levels (Primary/JSS/SS), subjects, teacher assignments
2. [ ] Students and parents (parent with many children; history kept across promotions; statuses: active, graduated, withdrawn, suspended, transferred)
3. [ ] Attendance (present, absent, late, excused; statistics; history)
4. [ ] Admissions (application, review, accept/reject, admission number, convert to student)
5. [ ] Assessments and results (configurable components and grade scales; calculated totals/grades/remarks; configurable ranking)
6. [ ] Result workflow: Draft, Submitted, Reviewed, Approved, Published; no silent edits after publish; audit record for changes
7. [ ] Report cards (PDF)
8. [ ] Finance: fee structure, invoice, invoice items, payments, payment allocation, receipt, balance (full and partial payment, manual recording)
9. [ ] Dashboards (admin, teacher, parent) using real data only
10. [ ] Announcements and in-app notifications
11. [ ] Timetable
12. [ ] Documents with controlled access
13. [ ] Analytics (student, academic, finance, attendance)
14. [ ] Audit log
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

## 5b. Agreed after MVP core (build after finance)

- [ ] School public home page (about, programmes, gallery, news, admissions button, contact), own subdomain per school
- [ ] Website gallery manager with parental-permission warning
- [ ] Profile photos for students, teachers and parents
- [ ] UI: real templates on the locked palette, app shell, shared components, error pages, flash messages (phases U0 to U2)

## 6. Future ideas (not MVP)

- FUTURE: Online payments (Paystack), SMS/WhatsApp/email, online admissions, subscriptions and school billing, parent/student mobile apps, boarding, transport, hostel, library, payroll, e-learning, AI analytics, React frontend if justified.

## 7. Open questions to settle through configuration, not blocking

- Exact assessment components and weights at the pilot school
- Grade boundaries and whether ranking is used
- Fee items, class-based differences, discounts, instalments
- Required student fields
