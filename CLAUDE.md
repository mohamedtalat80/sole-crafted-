# Shoe Ecommerce — Backend Architecture & Refactoring Guide

This file is the contract for **how every app under `apps/` is built**. When
refactoring an existing app or scaffolding a new one, follow these rules. The
canonical reference implementation is **`apps/privacy_policy/`** — copy its
*structure*, but apply the corrections listed in "Known issues to NOT copy".

---

## 1. Layered architecture

Each app is a vertical slice with strict, one-directional layering. A layer may
only call the layer directly below it. Never skip a layer (e.g. a View must
never touch the ORM, a Service must never build an HTTP `Response`).

```
HTTP request
    │
    ▼
View (apps/<app>/views.py)              ← HTTP only: parse, validate (serializer), call service, return envelope
    │   uses Serializers (validation + representation)
    ▼
Service (apps/<app>/services/*.py)      ← business rules, orchestration, raises domain exceptions
    │   depends on the Interface, not the concrete repo
    ▼
Repository Interface (apps/<app>/interfaces/*.py)   ← ABC: the contract
    ▲
Repository impl (apps/<app>/repositories/*.py)      ← ORM ONLY: queries, select/prefetch_related, integrity handling
    │
    ▼
Models (apps/<app>/models.py)           ← schema only: fields, Meta, __str__, light validation in clean()
```

Shared building blocks live in **`apps/core/`** and must be reused, never
re-implemented per app:

| Need                     | Use from `apps/core`                                             |
|--------------------------|-----------------------------------------------------------------|
| Success/error responses  | `core.responses.success_response` / `error_response`            |
| Domain exceptions        | `core.exceptions.ApplicationError` + subclasses (`NotFoundError`, `ConflictError`, `UnauthorizedError`, `ForbiddenError`, `TooManyRequestsError`) |
| Global error formatting  | `core.exceptions.custom_exception_handler` (registered in DRF settings) |
| Reject unknown fields    | `core.serializers.StrictSerializer` / `StrictModelSerializer`   |
| Pagination               | `core.pagination.PaginationMixin` + `StandardResultsPagination` + `PAGINATION_PARAMS` |
| Permissions              | `core.permissions.IsAdminAccount` / `IsCustomer`                |
| Auto-translation         | `core.utils.translation_utils.TranslationService` + `TRANSLATION_LANGUAGES` |

---

## 2. Standard app file layout

Every app must follow this exact structure. Use plural-snake_case app names
(`privacy_policy`, `contact_us`). Do **not** invent new top-level files.

```
apps/<app>/
├── __init__.py
├── apps.py                 # AppConfig: name = "apps.<app>", label = "<app>"
├── models.py               # models + their *Translation tables
├── admin.py                # @admin.register for each model
├── serializers.py          # Write + Read (+ AdminRead) serializers
├── urls.py                 # public_<app>_urlpatterns + admin_<app>_urlpatterns
├── views.py                # APIView classes, thin
├── interfaces/
│   └── <app>_repository_interface.py   # I<App>Repository(ABC)
├── repositories/
│   └── <app>_repository.py             # <App>Repository(I<App>Repository)
├── services/
│   └── <app>_service.py                # <App>Service
├── migrations/
└── tests/
    └── test_<app>.py
```

---

## 3. Layer rules (the contract)

### Models (`models.py`)
- Fields, `Meta`, `__str__` only. Keep DB-level invariants here
  (`unique_together`, `UniqueConstraint`, `db_index=True` on ordering fields).
- Translatable content uses the **base + translation table** pattern:
  - `<Model>Translation` with FK `related_name="translations"`, a `language`
    field, the translated columns, and `unique_together = ("<parent>", "language")`.
- Light, self-contained validation may live in `clean()` (e.g. singleton guard).
  Anything needing other tables or external services belongs in the Service.

### Repositories (`repositories/`)
- **ORM only.** No HTTP, no business decisions, no translation calls.
- Implement the matching ABC from `interfaces/`. The method signatures in the
  ABC and the impl **must match exactly** (see Known issues #2).
- Use `select_related`/`prefetch_related` for every read that the serializer
  will traverse (translations, FKs) to avoid N+1.
- Translate DB failures into domain exceptions:
  `DoesNotExist → NotFoundError`, `IntegrityError → ConflictError`.
- `update_or_create` returns `(obj, created)` — unpack it; never return the
  tuple where the interface promises a single object (see Known issues #3).

### Services (`services/`)
- All business rules: cross-row uniqueness checks, orchestration, fan-out to
  translation, permission-independent invariants.
- Raise `ApplicationError` subclasses on failure. **Never** build a `Response`.
- **Constructor dependency injection only.** Take the repo (typed as the
  interface) and any collaborators (e.g. `TranslationService`) as constructor
  args. Do *not* default-construct collaborators inside methods.
- Auto-translation pattern (`_auto_translate_all`): loop `TRANSLATION_LANGUAGES`,
  call `translate_batch`, upsert each translation, and **swallow + log** per-language
  failures so one failed language never breaks the write.

### Serializers (`serializers.py`)
- Inherit from `StrictSerializer` / `StrictModelSerializer` (reject unknown keys).
- Separate by direction and audience:
  - `<App>WriteSerializer` — input validation for POST/PATCH.
  - `<App>ReadSerializer` — public output; resolves translated fields via
    `Accept-Language` (read `request.LANGUAGE_CODE`, fall back to `en`).
  - `<App>AdminReadSerializer` — admin output (raw source fields + audit fields
    like `updated_by`, timestamps).

### Views (`views.py`)
- Thin `APIView` subclasses. The body of each method is: validate with the
  serializer → call the service → translate `ApplicationError` to `error_response`
  → return `success_response` / `paginate_and_respond`.
- Build the service through **one module-level factory** (e.g.
  `_get_<app>_service()`), used consistently by *every* view in the file (not
  `__init__` in some and inline in others).
- Document with `@extend_schema` (drf-spectacular): `operation_id`, `summary`,
  request/response serializers, and at least one `OpenApiExample`. Reuse the
  shared `Accept-Language` parameter for translated endpoints.
- Public endpoints (`AllowAny`) and admin endpoints (`IsAdminAccount`) are
  separate view classes.

### URLs (`urls.py`)
- Export two lists: `public_<app>_urlpatterns` and `admin_<app>_urlpatterns`.
- Use **kebab-case** paths consistently (`privacy-policy/`,
  `privacy-policy/<int:pk>/`, `privacy-policy/<int:pk>/toggle-active/`).
- Wire both lists into the project URLconf (`config/urls.py`) under `/api/` and
  `/api/admin/` respectively. **Note:** `config/urls.py` currently still points
  at the *old* apps (`users`, `Prouducts`, `orders`, …) and does **not** include
  the new `apps/*` packages — wiring them in is part of the refactor.

### Tests (`tests/`)
- Patch the view's service factory (`_PATCH_TARGET = "apps.<app>.views._get_<app>_service"`)
  to inject a service backed by a **mocked TranslationService** (so tests never
  hit the network). Reuse the `_assert_success` / `_assert_error` envelope
  helpers from the reference app.
- Cover: create (201), validation (400 incl. missing required + unknown field),
  list (200), retrieve (200 / 404), update (200), toggle-active, and
  authz (non-admin 403, unauthenticated 401/403).

---

## 4. Response & error contract (must hold for every endpoint)

Success:
```json
{ "status": true, "message": "...", "data": { ... } | null }
```
Error:
```json
{ "status": false, "message": "...", "errors": { "field": ["msg"] } }
```
Paginated `data`:
```json
{ "count": 0, "next": null, "previous": null, "next_pages": null, "results": [] }
```
Never hand-roll these dicts — always go through `core.responses` /
`PaginationMixin` / `custom_exception_handler`.

---

## 5. Checklist — refactoring an existing app

1. Create the folder layout in §2 (move ORM out of views/services into a repo).
2. Write the `I<App>Repository` ABC; make the repo implement it; **verify
   signatures match**.
3. Move every business rule from views into the service; inject repo + translation
   via the constructor.
4. Convert serializers to `Strict*`; split Write / Read / AdminRead.
5. Make views thin; introduce the single `_get_<app>_service()` factory.
6. Normalize URL names to kebab-case; export the two urlpattern lists; include
   them in `config/urls.py`.
7. Replace ad-hoc dicts/`Response` with `core.responses` + domain exceptions.
8. Fix the naming/docstring issues in §6.
9. Add/port the test suite using the mocked-translation pattern; run it.

## Checklist — building a new app

1. `python manage.py startapp <app> apps/<app>` (then set `AppConfig.name`/`label`).
2. Add it to `INSTALLED_APPS` as `apps.<app>`.
3. Scaffold the layout in §2 by copying `privacy_policy` and renaming.
4. Model → Interface → Repository → Service → Serializers → Views → URLs → Tests,
   in that order.
5. Wire `public_*`/`admin_*` urlpatterns into `config/urls.py`.
6. `makemigrations` + `migrate`; write tests; run the suite.

---

## 6. Known issues to NOT copy (fix these during refactor)

The current `apps/` were scaffolded by copy-paste, so they carry mistakes. When
you touch an app, fix these rather than propagate them:

1. **Leftover/wrong docstrings & names** — files say "FAQ model", "boats app",
   "onboarding screen", "Omarina envelope". Rewrite docstrings to match the app.
2. **Interface ⇄ impl signature drift** — e.g. `IPrivacyPolicyRepository.update`
   declares `(self, PrivacyPolicy, data)` while the impl is
   `(self, PrivacyPolicy_id, data, updated_by)`. Keep them identical.
3. **`update_or_create` tuple** — `upsert_translation` returns `(obj, created)`
   but the ABC promises a single object. Unpack and return the object.
4. **Model class shadowed by variable name** — services/repos use `PrivacyPolicy`
   as a local variable, colliding with the model. Use `instance` / `policy_id`.
5. **Inconsistent DI** — `privacy_policy` injects `TranslationService` via the
   constructor (correct); `contact_us` default-constructs it inside the service.
   Standardize on constructor injection.
6. **Imports inside methods** — `contact_us` re-imports `logging` inside a method
   though a module logger exists. Keep imports at module top.
7. **Inconsistent service construction in views** — some views build the service
   in `__init__`, the public one builds it inline. Use the one factory everywhere.
8. **URL casing** — mix of `/api/admin/PrivacyPolicy/` (PascalCase) and
   `/api/privacy-policy/` (kebab). Standardize on kebab-case.

---

## 7. Conventions

- Python: type hints on public methods, `from __future__ import annotations`,
  module-level `logging.getLogger(__name__)`.
- App label = bare app name; `AppConfig.name = "apps.<app>"`.
- Translatable text always flows: source columns on the base model →
  `*Translation` rows auto-filled by the service → resolved on read by
  `Accept-Language`. Supported languages come from
  `core.utils.translation_utils.TRANSLATION_LANGUAGES`.
- Run tests with `python manage.py test apps.<app>` before considering a
  refactor done.
