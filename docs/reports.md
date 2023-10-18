# Reports

## Formats

| Format | Extension | Best for |
| --- | --- | --- |
| Markdown | `.markdown` / `.md` | READMEs, PRs, quick review |
| HTML | `.html` | Shareable self-contained page with interactive Plotly charts |
| JSON | `.json` | Machine consumption / archiving |
| CSV | `.csv` | Spreadsheet analysis, per-example rows |

```bash
teb eval report --job 1 --format html
teb eval report --job 1 --format csv --out reports/run1.csv
```

## Contents

Every report carries, at minimum:

- **Job metadata** — provider, model, timestamps, duration, status
- **Version stamps** — dataset version, dataset content hash, prompt version,
  rubric version, code (git) revision
- **Aggregate scores** — overall, semantic preservation, terminology
  consistency, and every scored dimension, with sample sizes
- **Per-category breakdown**
- **Per-example table** — scores, pass/fail, provenance, errors
- **Cost** — estimated and actual

## Per-dimension CSV columns

The CSV export emits one `dim_<name>` column per scored dimension
(e.g. `dim_semantic_preservation`, `dim_terminology_consistency`,
`dim_transliteration_accuracy`), so downstream analysis can pivot on any axis.

## Charts

The HTML report embeds three **interactive Plotly** charts (hover for
values, zoom, pan):

1. **Per-category performance** — grouped bars for overall / semantic /
   terminology side by side, making the two primary axes easy to compare.
2. **Score distribution** — histogram of overall scores.
3. **Semantic vs terminology scatter** — one point per example, showing
   the two axes are independent (a model can preserve meaning while
   drifting on terminology, or vice-versa).

The Plotly.js runtime is **inlined** into the HTML, so the report renders
fully offline with no external requests. The Streamlit dashboard uses the
same Plotly figures via `st.plotly_chart`.

## Reproducibility

Because reports record the dataset content hash, prompt version, rubric version,
and code revision, two reports can be diffed to attribute a score change to a
dataset edit, a rubric change, or a code change.
