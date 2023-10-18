# CLI reference (`teb`)

The Typer CLI groups commands under sub-apps. Run `teb --help` for the full tree.

## Dataset

```bash
teb dataset build [--version 1.0.0]
teb dataset validate <path>
teb dataset stats
teb dataset import <path> [--version 1.0.0]
teb dataset export <out> [--version 1.0.0]
```

## Evaluation

```bash
teb eval run [--provider mock] [--model ID] [--name NAME]
             [--partition train|dev|test] [--categories a,b]
             [--max N] [--max-tokens N] [--temperature F]
             [--config configs/held-out-test.json]
             [--offline-file responses.jsonl] [--confirm-cost]
teb eval compare --jobs 1,2 [--dimension overall_score|semantic_preservation|terminology_consistency]
teb eval report --job <id> [--format markdown|html|json|csv] [--out FILE]
teb eval responses-import <file> [--model-id ID]
```

- `--max N` draws a **seeded random sample** of N examples (`sampling_seed`, default 42),
  so samples are reproducible.
- `--max-tokens` raises the completion budget; needed for "reasoning" models.
- `--config FILE` loads a full `JobConfig` JSON (see `configs/`); CLI flags override it.
- `--confirm-cost` is required when the pre-run cost estimate exceeds the cap.
- The offline provider needs `--offline-file` (JSONL of `example_id`/`response_text`).

## Providers

```bash
teb providers list
teb providers test <name> [--model ID]
teb providers discover <name>        # list models the endpoint actually serves
```

## Annotation

```bash
teb annotation status
teb annotation review <example_id> --reviewer NAME
                   [--semantic F] [--terminology F] [--fluency F]
                   [--adequacy F] [--cultural F]
                   [--agrees/--disagrees] [--status pending|approved|disputed]
                   [--notes "..."]
teb annotation adjudicate <example_id> --adjudicator NAME
                        --decision uphold|override|revise [--notes "..."]
```

## Serving

```bash
teb serve [--host 127.0.0.1] [--port 8000] [--reload]   # FastAPI (uvicorn)
teb ui    [--port 8501] [--headless/--no-headless]      # Streamlit dashboard
```

## Top level

```bash
teb doctor      # environment self-check
teb version     # package + code revision
```

## Exit codes

`0` success · `1` validation failure · `2` dataset load error ·
`3` provider error / unknown provider · `4` cost estimate above the cap ·
`5` cost limit exceeded during the run · `6` unexpected job failure.
