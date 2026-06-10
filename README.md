# Photo Classification Platform

Cloud-deployable, microservices-based platform where users register, upload a
photo with metadata, get a classification result, and admins can search and
filter every submission.

The platform is split into two services, each owning its own data:

* **auth-service** — accounts, registration, login, JWT issuance.
* **submission-service** — submissions (photo + metadata), photo storage,
  classification, and admin search/filter.

## Architecture

```
                             +---------------------+
                             |  Ingress / API GW   |
                             +----------+----------+
                                        |
           +----------------------------+----------------------------+
           |                            |                            |
 +---------v----------+      +----------v-----------+      +----------v---------+
 |    auth-service    |      |  submission-service  |      |      frontend      |
 |    (FastAPI/Py)    |      |     (FastAPI/Py)     |      |    (nginx + SPA)   |
 |  /auth/register    |      |  /submissions        |      +--------------------+
 |  /auth/login       |      |  /submissions/me     |
 |  /auth/me          |      |  /admin/submissions  |
 |  /auth/introspect  |      |  /admin/submissions/ |
 +---------+----------+      +-----+----------+-----+
           |                       |          |
 +---------v----------+      +-----v-----+  +-v--------+
 |   auth-db (PG)     |      |submission-|  |  MinIO   |
 |   users            |      |  db (PG)  |  |  photos/ |
 +--------------------+      |submissions|  +----------+
                             +-----------+
```

An editable block diagram is in [`docs/architecture.drawio`](./docs/architecture.drawio)
(open at <https://app.diagrams.net>). See [NEXT_STEPS.md](./NEXT_STEPS.md) for
production-hardening guidance.

The `submission-service` validates JWTs locally with the shared secret (no
per-request hop to the auth service); it can also fall back to
`POST /auth/introspect` if you prefer centrally revocable tokens.

### Why these technologies

| Choice | Reason |
| --- | --- |
| **FastAPI** | Pydantic validation, async, automatic OpenAPI/Swagger at `/docs`. |
| **PostgreSQL** | Relational integrity, rich indexing, JSONB for classifier metadata, mature managed offerings (RDS / Cloud SQL). Two logical DBs keep service ownership clean and allow independent scaling/migrations. |
| **MinIO (S3-compatible)** | Photos are large binary blobs — a row in Postgres would bloat backups and waste IOPS. S3-compatible storage gives presigned URLs, lifecycle rules, and is swappable for AWS S3 / GCS in production. |
| **Alembic** | Versioned, reversible migrations per service. |
| **JWT (HS256)** | Stateless inter-service auth via a shared secret. |
| **slowapi** | Per-route rate limiting in front of the most abusable endpoints. |
| **Pillow** | Image decode + the classifier's heuristic. |
| **TailwindCSS + React** | Utility-first styling for a fast, consistent UI; React Router SPA served by nginx. |

### Project structure

Each Python service follows a layered architecture so responsibilities are easy
to locate and test:

```
services/<service>/app/
  core/          # settings, database engine/session, security (JWT, hashing)
  models/        # SQLAlchemy ORM models
  schemas/       # Pydantic request/response models
  repositories/  # data-access boundary (all DB queries live here)
  services/      # domain logic (classifier, photo storage)   [submission-service]
  api/
    routes/      # FastAPI routers
    serializers.py
  bootstrap.py   # admin seeding                               [auth-service]
  main.py        # app factory + wiring
```

```
frontend/src/
  lib/           # apiClient (typed fetch wrapper)
  context/       # AuthContext (auth state + token handling)
  components/    # NavBar, RequireAuth, Banner
  features/      # auth / submissions / admin pages
```

### Database schema & indexing

* `users(id UUID PK, email UNIQUE, password_hash, is_admin, is_active, created_at)`
  — index on `email`.
* `submissions(id UUID PK, owner_id UUID, full_name, age, residence, gender,
  country_of_origin, description, photo_key, photo_content_type,
  photo_size_bytes, classification_label, classification_score,
  classification_meta JSONB, created_at, updated_at)`
  — single-column indexes on each filterable column plus a composite
  `(gender, country_of_origin, age)` index aligned with the admin filter UI,
  and `created_at` for time-range queries / pagination.

## Required endpoints

### auth-service (`http://localhost:8001`)

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/auth/register` | Create a user (email + password ≥ 8 chars) |
| POST | `/auth/login` | Returns `access_token` (JWT, 60 min) |
| GET  | `/auth/me` | Current account from `Authorization: Bearer …` |
| POST | `/auth/introspect` | Validate a token (server-side check) |
| GET  | `/health` | Liveness/readiness |
| GET  | `/docs` | Swagger UI |

### submission-service (`http://localhost:8002`)

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/submissions` | Multipart: `photo` + metadata fields. Returns row + presigned `photo_url`. |
| GET  | `/submissions/me` | List the caller's own submissions |
| GET  | `/admin/submissions` | **Admin only**. Filters: `min_age/max_age`, `gender`, `country_of_origin`, `residence`, `name`, `classification_label`, `created_after/before`, `page`, `page_size` |
| GET  | `/admin/submissions/{id}` | **Admin only**. Single record with presigned URL |
| GET  | `/health` | Liveness/readiness |
| GET  | `/docs` | Swagger UI |

## Safety rules implemented

Most rules are applied in the `submission-service`
([`app/api/routes/submissions.py::enforce_upload_policy`](services/submission-service/app/api/routes/submissions.py))
because uploads are the largest attack surface:

1. **MIME allow-list** (`image/jpeg`, `image/png`, `image/webp`) — rejects
   anything else with HTTP 415. Mitigates accidental upload of executables /
   archives.
2. **Hard size cap** (`MAX_UPLOAD_BYTES`, default 5 MB, also enforced at the
   ingress level) — protects disk, bandwidth, and the classifier.
3. **Real-image verification** via `PIL.Image.verify()` — defends against
   header spoofing where a non-image is given an image MIME type.
4. **Pixel-dimension bounds** (min `64×64`, max `4096×4096`) — defends against
   *decompression bombs* (tiny files that expand to gigabytes in memory).
5. **Password hashing with bcrypt + per-request rate limiting** on
   `/auth/login` (10/min) and `/auth/register` (5/min) — slows credential
   stuffing.
6. **JWT signature verification** on every protected request, plus an
   `is_admin` claim check for admin endpoints (defense in depth: even if a
   regular user's token leaks, they still can't reach `/admin/*`).
7. **Pydantic input validation** on every endpoint (lengths, ranges, enums) —
   protects against malformed input that could destabilize downstream code.
   Path IDs are typed as `UUID`, so a malformed id returns 422, not a 500.
8. **Private object storage** — photos are written under
   `<owner_id>/<uuid>-<filename>` and only exposed via short-lived presigned
   URLs (`S3_PRESIGNED_EXPIRES`, default 1 hour). The bucket is never public.
9. **Container hardening** in Kubernetes manifests: non-root user (uid 1001),
   read-only root filesystem, all capabilities dropped, seccomp
   `RuntimeDefault`, resource requests/limits.
10. **Network policy** (`k8s/networkpolicy.yaml`): default-deny in the
    namespace; services can only reach their own DB, MinIO, and DNS.

## Running locally with Docker

```bash
cp .env.example .env          # edit JWT_SECRET, ADMIN_PASSWORD, etc.
docker compose up --build
```

Once healthy:

* Frontend (web UI):    http://localhost:5173
* Auth Swagger:     http://localhost:8001/docs
* Submission Swagger:      http://localhost:8002/docs
* MinIO console:        http://localhost:9001  (login: minioadmin / minioadmin)

### Frontend dev mode (hot reload)

The compose file ships a production nginx build of the frontend. For local
development with hot reload, run Vite directly while the backends still run in
Docker:

```bash
docker compose up auth-service submission-service minio auth-db submission-db
cd frontend
npm install        # first time only
npm run dev        # http://localhost:5173
```

The frontend reads backend URLs from `frontend/.env` (`VITE_AUTH_API`,
`VITE_SUBMISSION_API`). Defaults already point at `localhost:8001` /
`localhost:8002`.

### Storage note (no AWS account needed)

Photos are stored in **MinIO**, an S3-compatible server bundled in
`docker-compose.yml`. The `submission-service` uploads via the in-cluster endpoint
`http://minio:9000`, but presigned download URLs returned to the browser use
`S3_PUBLIC_ENDPOINT_URL` (default `http://localhost:9000`) so they resolve from
the host. To switch to real AWS S3 in prod, set `S3_ENDPOINT_URL=` (empty),
`S3_PUBLIC_ENDPOINT_URL=` (empty), `S3_REGION`, and provide IAM credentials —
no code changes.

### Quick API walkthrough

```bash
# 1) Register
curl -X POST http://localhost:8001/auth/register \
  -H 'content-type: application/json' \
  -d '{"email":"alice@example.com","password":"hunter22hunter"}'

# 2) Login -> grab the token
TOKEN=$(curl -s -X POST http://localhost:8001/auth/login \
  -H 'content-type: application/json' \
  -d '{"email":"alice@example.com","password":"hunter22hunter"}' | jq -r .access_token)

# 3) Submit a submission (photo + metadata)
curl -X POST http://localhost:8002/submissions \
  -H "Authorization: Bearer $TOKEN" \
  -F full_name=Alice -F age=29 -F residence=Berlin \
  -F gender=female -F country_of_origin=DE \
  -F 'description=Hi there' \
  -F photo=@./me.jpg

# 4) Admin login + filtered list
ADMIN=$(curl -s -X POST http://localhost:8001/auth/login \
  -H 'content-type: application/json' \
  -d '{"email":"admin@example.com","password":"admin12345"}' | jq -r .access_token)

curl -H "Authorization: Bearer $ADMIN" \
  "http://localhost:8002/admin/submissions?gender=female&min_age=18&max_age=60&page=1&page_size=25"
```

## Tests & lint

Backend (Python) — auth has 3 tests, submission has 8:

```bash
pip install -r services/auth-service/requirements.txt \
            -r services/submission-service/requirements.txt \
            pytest ruff
ruff check services
(cd services/auth-service && pytest)
(cd services/submission-service && pytest)
```

Frontend (Vitest + React Testing Library) — 14 tests:

```bash
cd frontend
npm install            # first time only
npm run typecheck
npm test               # api client, auth context, login page
npm run test:coverage  # with v8 coverage report
```

## CI/CD

[`.github/workflows/ci.yml`](.github/workflows/ci.yml):

1. **lint-test** matrix per Python service: ruff + pytest.
2. **frontend** job: `npm ci` → typecheck → vitest → vite build.
3. **build-and-push** (only on `main`): builds Docker images for
   `auth-service`, `submission-service`, **and `frontend`** in parallel,
   pushes `ghcr.io/<owner>/<image>:sha-<commit>` and `:latest`.
4. **deploy** (gated by the `production` GitHub environment): runs
   `kubectl apply` against the cluster declared in the `KUBECONFIG` secret,
   substitutes the `OWNER` placeholder + `:latest` tag with the real GHCR
   namespace and the immutable sha tag, then waits for all three rollouts.

## Kubernetes

`k8s/` contains namespace, secrets/config example, Postgres + MinIO
StatefulSets, Deployments + Services + HPAs + PDBs for both services, an
Ingress for `api.example.com`, and a default-deny NetworkPolicy.

To run on Docker Desktop's built-in Kubernetes against locally-built images:

```bash
docker compose build
kubectl apply -k k8s/overlays/docker-desktop
```

See [NEXT_STEPS.md](./NEXT_STEPS.md) for production hardening (secrets, scaling,
observability).
