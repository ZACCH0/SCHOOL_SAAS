# T7e SPEC — Login by phone or email, one-time codes for activation and password reset

Status: **DRAFT — waiting for owner approval**
Agreed plan (PROJECT_STATE task board): login by phone or email with password; one-time codes (email free, SMS paid) only for activation and password reset; per-school SMS credit and rate limits.

---

## 1. What exists today

- `accounts.User` — username login; `email` optional, `phone` a plain `CharField(max_length=20, blank=True)`. Neither is unique.
- Login is stock `LoginView` (username + password) at `accounts:login`.
- Password reset is the built-in **email link** flow (T7c).
- django-axes lockout: 5 failures on (username + IP) → 15 minutes.

## 2. Decisions (and why)

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | **One identifier field** on login (username OR email OR phone) + password | One box is simpler for parents/teachers; usernames stay valid forever |
| D2 | Email/phone resolve to a user **only when unique** | If 2 accounts share an email we cannot pick one safely — refuse with "sign in with your username" |
| D3 | **Codes are 6 digits, stored hashed, 10-minute expiry, single use, max 5 wrong tries then void** | Codes travel over SMS/email; short life + hashed storage + attempt cap is the standard safe pattern |
| D4 | Codes used for **password reset and account activation only** — never as a login method | Agreed scope; keeps login simple and lockout strong |
| D5 | **No new packages.** Codes, rate limits and SMS log live in the DB | Our no-Celery/Redis rule; volumes are tiny |
| D6 | SMS sender is an **interface with a console/log implementation now**; the real Nigerian provider (pricing agreed then) is wired at T18 | No provider account or budget exists yet; nothing paid is triggered from dev |
| D7 | SMS usage is **recorded per school** (the user's single active membership), school NULL = platform-paid | Wrinkle you approved: `User` is global, so "per-school credit" is only meaningful when membership is unambiguous. Billing itself stays T18 |
| D8 | Login lockout keeps working: we resolve the identifier to a user **first**, then authenticate with the resolved username so axes locks (username + IP) exactly as today | Lockout tests stay valid; no axes behaviour change |
| D9 | **No account-existence leaks.** Every forgot-password response shows the same generic message | Someone probing emails/phones must learn nothing |
| D10 | Activation flow exists but stays quiet: office-created users keep getting passwords the current way (T7d); activation is for users created with an **unusable password** | Pilot workflow doesn't change |

## 3. Data changes (migration `accounts.0003`)

**`User`** (no new fields, only constraints):
- `UniqueConstraint(Lower("email"), condition=~Q(email=""))` — case-insensitive, unique only when set.
- `UniqueConstraint("phone", condition=~Q(phone=""))` — phones are stored **normalized** so uniqueness is consistent.
- ⚠ Pre-migration check on the dev DB for duplicate emails/phones (constraint fails loudly if any — that is intended; we clean data first).

**`OneTimeCode`** (new model, `apps.accounts`):
- `user` FK (CASCADE — codes are disposable), `purpose` (`password_reset` / `activation`), `code_hash` (SHA-256 of the 6-digit code), `expires_at`, `used_at` (null until spent), `attempts` (int, default 0), `created_at`.
- Index `(user, purpose, created_at)` for the rate-limit count.

**`SmsLog`** (new model, `apps.accounts`):
- `user` FK, `school` FK (null allowed = platform-paid), `purpose`, `created_at`, index `(school, created_at)`.
- Written by the SMS sender service inside the same transaction as code creation.

## 4. Logic

**Phone normalization** (`accounts/normalization.py`, pure functions, unit-tested):
- Strip spaces, dashes, parentheses. `0803…` → `+234803…` (Nigeria). `+234…` kept. Anything else saved as typed (stripped).
- Login resolution normalizes the typed identifier with the same function.

**Identifier resolution** (`accounts/identification.py`):
1. Exact username match → user.
2. Case-insensitive email match → user **only if exactly one**.
3. Normalized phone match → same rule.
4. No match or ambiguous → `None` (view shows the generic axes-safe failure).

**Code service** (`accounts/services.py` additions):
- `issue_code(request, user, purpose)` — refuses when the user has no reachable channel (no email and no phone → error), enforces max **5 codes per user+purpose per hour**, hashes the code, sends via email (free) or SMS when there is no email, writes `SmsLog` if SMS. Audited **without the code** (`accounts.code_issued` — details contain purpose and channel only).
- `verify_code(user, purpose, code)` — checks hash, expiry, single use, attempts (< 5); wrong/expired/used code increments `attempts` and refuses with one friendly message; 5th wrong try voids the code. Success marks `used_at`.
- `reset_password_with_code(request, user, code, new_password)` — verify, then set the password (validators run), invalidate the user's sessions is NOT needed (password change already keeps sessions in Django's default), audit `accounts.password_changed`.

**Views** (`accounts/`, namespace `accounts`):
- `login/` — identifier + password form (template `accounts/login.html` updated). Axes flow untouched.
- `password-reset/` — becomes **identifier-based**: enter username/email/phone → if the user has an email, keep the existing emailed-link flow (unchanged, free); if the user has **only a phone**, issue an SMS code. Always the same "If that account exists, we've sent reset instructions" page.
- `password-reset/code/` — 6-digit code entry; on success a `SetPasswordForm` step; POST-only, CSRF, rate-limited.
- `activate/<uidb64>/` — same code-entry + set-password pattern for users with unusable passwords (D10). Hidden until we create such users.

## 5. Rate limits (DB-enforced)

| Limit | Value | Where |
|---|---|---|
| Codes issued per user+purpose | 5 per rolling hour | `issue_code` count query |
| Wrong code entries | 5, then the code is void | `verify_code` |
| Login failures | unchanged (axes 5 → 15 min) | axes |

## 6. Tests (~24, new files `test_identification.py`, `test_codes.py`, `test_code_views.py`; updates to `test_login.py`)

1. Login works by username, by email (case-insensitive), by phone (local and +234 formats).
2. Wrong password on every identifier form still counts into axes (lockout after 5).
3. Duplicate email → login refuses with the "use your username" message; duplicate phone same.
4. Constraints: second user with a different-case duplicate email blocked; many blank emails/phones fine.
5. Normalization unit tests: `0803 123 4567`, `+2348031234567`, dashes/spaces, non-Nigerian passthrough.
6. `issue_code`: hashed storage (raw code never in DB), 10-minute expiry, audit without code, no-channel user refused, rate limit refuses the 6th code in an hour.
7. `verify_code`: correct code passes once, second use refused, wrong code ×5 voids, expired refused, code for a different purpose refused.
8. Full reset flow: identifier → code → new password → old password dead → audited.
9. Email-user reset goes through the existing link flow (unchanged) — regression.
10. Views: anonymous walls, generic message for unknown identifiers, GET on code page after 5 bad tries shows voided state, CSRF on all POSTs.
11. `SmsLog` written with the user's single school; multi-membership user → school NULL; no real HTTP call happens in tests (console sender).

## 7. Out of scope (later tasks)

Real SMS provider + pricing + per-school credit balances (T18), email verification on signup, 2FA, REST API endpoints (T17).

## 8. Build order (only after approval)

1. Migration: constraints + 2 models (duplicate check on dev DB first)
2. Normalization + identification + code services + tests
3. Views/templates (login form, reset-by-identifier, code entry) + tests
4. `check`, `makemigrations --check`, full `pytest`, CSS rebuild (login template changed)
5. Update `PROJECT_STATE.md`, commit `feat: login by username email or phone + one-time codes (T7e)`
