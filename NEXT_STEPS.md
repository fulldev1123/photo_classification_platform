# Next steps / production hardening

This project is intentionally runnable end-to-end on a laptop while leaving a
clear path to production. The notes below outline what to change before a real
deployment.

## Architecture diagram

[`docs/architecture.drawio`](./docs/architecture.drawio) is an editable
diagram. Open it directly at <https://app.diagrams.net> (File → Open) or with
the **Draw.io Integration** VS Code extension, then export to PNG/SVG via
*File → Export as*.

## Secrets

- Local/dev secrets live in `.env` (compose) and
  `k8s/overlays/docker-desktop/secrets.yaml`. **Never** commit real secrets.
- In production replace the plaintext `Secret` in `k8s/secrets.example.yaml`
  with one of: Sealed Secrets, External Secrets Operator (backed by AWS/GCP
  Secret Manager), or HashiCorp Vault.
- Rotate `JWT_SECRET` regularly. Because both services validate the same HS256
  secret, rotation needs a brief dual-secret window or a move to asymmetric
  (RS256) keys so the `submission-service` only needs the public key.

## Database

- Swap the demo Postgres `StatefulSet`s for a managed offering (RDS, Cloud SQL,
  Azure DB) or an operator (CloudNativePG, Zalando) for backups, HA, and PITR.
- Migrations run automatically on container start
  (`alembic upgrade head && uvicorn ...`). For zero-downtime deploys, run
  migrations as a separate `Job`/init step and keep them backwards-compatible
  with the previous app version.

## Storage

- Point the services at real S3 (or GCS/Azure Blob) by setting
  `S3_ENDPOINT_URL=` and `S3_PUBLIC_ENDPOINT_URL=` empty and providing IAM
  credentials / a workload identity — no code changes required.
- Enable bucket encryption, versioning, and lifecycle rules; keep the bucket
  private and rely on the short-lived presigned URLs the API already issues.

## Scaling

- Both services are stateless and already ship `HorizontalPodAutoscaler`s
  (CPU-based) plus `PodDisruptionBudget`s.
- The `submission-service` is the heavier path (image decode + classify). If the
  classifier is replaced by a real model, move inference to a dedicated
  deployment / GPU node pool or an external inference service and keep the API
  thin.

## Observability

- **Logs**: structured JSON to stdout, shipped by the cluster log agent
  (Fluent Bit → Loki/CloudWatch/Stackdriver).
- **Metrics**: add `prometheus-fastapi-instrumentator` to expose `/metrics`;
  scrape with Prometheus; dashboard in Grafana (latency, error rate, RPS,
  upload sizes, classifier duration).
- **Tracing**: OpenTelemetry SDK with auto-instrumentation for FastAPI +
  SQLAlchemy + boto3, exported to an OTLP collector (Tempo/Jaeger).
- **Alerts**: SLO-based alerts on the readiness/liveness probes already defined
  per deployment.

## Security follow-ups

- Tighten `CORS_ORIGINS` to the real frontend origin (currently `*` for dev).
- Add request-size limits at the ingress (already set:
  `proxy-body-size: 8m`) and per-IP rate limits (set: `limit-rps`).
- Consider moving from a shared symmetric JWT secret to RS256 so only the
  auth service holds the signing key.
- Add a token revocation / denylist if you need to invalidate sessions before
  expiry (the `/auth/introspect` endpoint is the natural hook).
