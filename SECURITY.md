# Security Policy

## Reporting a vulnerability

Please **do not** open a public issue for security problems. Report them
privately to the maintainers (open a draft security advisory on GitHub, or
contact the maintainers listed in the repository). Include:

- a description of the issue and its impact;
- steps to reproduce;
- affected version / commit;
- any suggested fix.

We aim to acknowledge reports within a few days.

## Supported versions

This is a research/benchmark project under active development. Security fixes
are applied to the `main` branch.

## Handling of secrets

- API keys are read from environment variables or a local `.env` file only.
- `.env` is git-ignored; `.env.example` contains **placeholders only**.
- Secrets are never written to the database, logs, reports, or the UI. Settings
  expose a `redacted_view()` used for display; API keys render as `***`.
- Provider error messages redact the API key before surfacing HTTP error bodies.
- The "easy connect" UI writes credentials only to the local `.env` file and
  never echoes them back.

If you find a path where a secret can be logged, persisted, or returned by the
API, treat it as a security bug and report it.

## Deployment guidance

The application is designed for **trusted, local use** by default:

- The FastAPI service binds to `127.0.0.1` and has permissive CORS suitable for
  local development only.
- There is no authentication layer. If you deploy beyond a trusted local
  environment, put it behind an authenticating reverse proxy, restrict CORS,
  and enforce network access controls.

## Cost and resource controls

- `TEB_MAX_COST_USD` caps estimated spend per job; paid runs require explicit
  confirmation (`--confirm-cost` / the API's `confirm_cost`).
- `TEB_MAX_REQUESTS_PER_JOB` and `TEB_MAX_CONCURRENCY` bound request volume and
  parallelism.
- Uploads/datasets are validated; filenames are sanitized.

## Data and privacy

- The shipped dataset is synthetic; no personal conversations are included.
- Do not add real customer conversations or personal data to the dataset.
- Prefer public-domain, licensed, or synthetic material; record provenance and
  licence for every record.
