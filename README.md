# Photo Classification Platform

Cloud-deployable platform where users register, upload a photo with metadata,
get a classification result, and admins search/filter every submission. Two
FastAPI microservices behind a React SPA, fully containerised, with upload
safety rules and admin-only access.

* **auth-service** — accounts, login, JWT issuance.
* **submission-service** — photo + metadata submissions, storage, classification, admin search.

Architecture: [`docs/architecture_diagram.png`](./docs/architecture_diagram.png)
(editable source [`docs/architecture.drawio`](./docs/architecture.drawio)) ·
scaling notes: [`docs/SCALING.md`](./docs/SCALING.md)

## Tech stack

| Layer | Choice |
| --- | --- |
| Backend | Python · FastAPI · Pydantic · SQLAlchemy · Alembic |
| Auth | JWT (HS256, shared secret) · bcrypt · slowapi rate limiting |
| Data | PostgreSQL (one DB per service) · MinIO / S3 (photos) |
| Imaging | Pillow |
| Frontend | React · TypeScript · Vite · TailwindCSS · React Router |
| Infra | Docker / Docker Compose · Kubernetes · GitHub Actions CI/CD |

## Classification logic

A deterministic, dependency-free **colour-palette** heuristic
([`classifier.py`](services/submission-service/app/services/classifier.py)) runs
on each upload. It averages the image's RGB and labels the dominant tone:

- `warm` — red is the strongest channel
- `cool` — blue strongest
- `natural` — green strongest
- `grayscale` — saturation below a threshold

It returns the `label`, a `0–100` confidence `score` (derived from saturation),
and a `meta` blob (`dominant_channel`, `saturation`, dimensions, model id
`color-palette-v1`). The logic sits behind a single `classify_photo` seam, so it
can be swapped for a real model (ONNX / Triton / remote inference) without
touching routes, storage, or schema.

## Endpoints

Each service exposes Swagger UI at `/docs` and a `/health` probe.

**auth-service** — `http://localhost:8001`

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/auth/register` | Create a user (email + password ≥ 8 chars) |
| POST | `/auth/login` | Returns a JWT `access_token` (60 min) |
| GET | `/auth/me` | Current account from the bearer token |
| POST | `/auth/introspect` | Validate a token (used by peer services) |

**submission-service** — `http://localhost:8002`

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/submissions` | Multipart `photo` + metadata; returns the row + presigned `photo_url` |
| GET | `/submissions/me` | The caller's own submissions |
| GET | `/admin/submissions` | **Admin only.** Filters: `min_age/max_age`, `gender`, `country_of_origin`, `residence`, `name`, `classification_label`, `created_after/before`, `page`, `page_size` |
| GET | `/admin/submissions/{id}` | **Admin only.** One record with presigned URL |

## Run locally

Requires Docker.

```bash
cp .env.example .env        # set JWT_SECRET, ADMIN_PASSWORD, …
docker compose up --build
```

| Surface | URL |
| --- | --- |
| Frontend | http://localhost:5173 |
| auth-service Swagger | http://localhost:8001/docs |
| submission-service Swagger | http://localhost:8002/docs |
| MinIO console | http://localhost:9001 (`minioadmin` / `minioadmin`) |

Default admin: `admin@example.com` / `admin12345`.

Frontend hot-reload (backends in Docker):

```bash
docker compose up auth-service submission-service auth-db submission-db minio
cd frontend && npm install && npm run dev
```

## Tests, lint & CI/CD

Backend — ruff + pytest (auth: 3 tests, submission: 9):

```bash
pip install ruff pytest \
  -r services/auth-service/requirements.txt \
  -r services/submission-service/requirements.txt
ruff check services
(cd services/auth-service && pytest)
(cd services/submission-service && pytest)
```

Frontend — Vitest + React Testing Library (14 tests):

```bash
cd frontend
npm install
npm run typecheck && npm test && npm run build
```

CI/CD — [`.github/workflows/ci.yml`](.github/workflows/ci.yml):

1. **lint-test** — ruff + pytest per service (matrix).
2. **frontend** — `npm ci` → typecheck → vitest → build.
3. **build-and-push** (on `main`) — build & push `auth-service`,
   `submission-service`, and `frontend` images to GHCR, tagged
   `sha-<commit>` + `latest`.
4. **deploy** (gated by the `production` GitHub environment) — `kubectl apply`
   the `k8s/` manifests, pinned to the immutable sha tag.
