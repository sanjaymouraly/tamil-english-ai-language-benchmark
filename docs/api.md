# HTTP API (FastAPI)

Start the server:

```bash
teb serve          # uvicorn, default http://localhost:8000
```

Interactive docs: `http://localhost:8000/docs`.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Liveness probe |
| GET | `/diagnostics` | Environment + provider readiness |
| GET | `/datasets` | List loaded dataset versions |
| GET | `/examples` | List / filter examples (`?limit=&offset=&category=`) |
| GET | `/examples/{example_id}` | Single example (404 if missing) |
| POST | `/jobs` | Create + run an evaluation job (synchronous) |
| GET | `/jobs` | List jobs |
| GET | `/jobs/{job_id}` | Job detail |
| GET | `/jobs/{job_id}/results` | Results for a job |
| GET | `/compare` | Compare jobs (`?job_ids=1,2&dimension=overall_score`) |
| POST | `/jobs/{job_id}/report` | Generate a report (`{"format": "markdown|html|json|csv"}`) |
| GET | `/providers` | Provider registry status |
| POST | `/providers/test` | Smoke-test a provider |
| POST | `/responses/import` | Import model responses for offline scoring |
| GET | `/annotations/status` | Human-review coverage summary |
| POST | `/annotations/review` | Submit a human review (per-dimension scores) |
| POST | `/annotations/adjudicate` | Record a final adjudication decision |
| GET | `/annotations/{example_id}` | Combined review + adjudication state |

## Example: run a job

```bash
curl -s -X POST http://localhost:8000/jobs \
  -H 'Content-Type: application/json' \
  -d '{"name":"api-demo","provider":"mock","model_id":"teb-mock-v1"}'
```

Returns a `JobRunResponse` with the job id, counts, and mean scores.

## Example: submit a human review

```bash
curl -s -X POST http://localhost:8000/annotations/review \
  -H 'Content-Type: application/json' \
  -d '{
    "example_id": "TEB-T2E-0001",
    "reviewer": "alice",
    "semantic_score": 0.9,
    "terminology_score": 0.8,
    "agrees_with_machine": true,
    "status": "approved"
  }'
```

## Example: adjudicate a dispute

```bash
curl -s -X POST http://localhost:8000/annotations/adjudicate \
  -H 'Content-Type: application/json' \
  -d '{"example_id": "TEB-T2E-0001", "adjudicator": "bob", "decision": "uphold"}'
```

Valid adjudication decisions: `uphold`, `override`, `revise`.

## Error model

- `400` — bad request (unknown provider, malformed ids, cost limit exceeded)
- `404` — job / example not found
- `422` — schema validation failure

All provider credential and cost errors are returned as clean `400`s, never as
stack traces.
