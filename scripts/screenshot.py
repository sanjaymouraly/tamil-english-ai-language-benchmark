"""Capture real screenshots of the running TEB app.

Navigates the Streamlit dashboard page-by-page by clicking the sidebar
radio labels via JS (reliable for Streamlit widgets), verifies each page
rendered by reading its heading, and captures the FastAPI docs.
"""

import time
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path("docs/screenshots")
OUT.mkdir(parents=True, exist_ok=True)

PAGES = [
    "Overview",
    "Dataset Explorer",
    "Evaluation",
    "Results Explorer",
    "Model Comparison",
    "Error Analysis",
    "Annotation Workspace",
    "Providers",
    "Reports",
]

CLICK_JS = """(name) => {
  const labels = document.querySelectorAll('div[data-testid="stRadio"] label');
  for (const l of labels) {
    if (l.innerText.trim() === name) { l.scrollIntoView(); l.click(); return true; }
  }
  return false;
}"""


def heading(page):
    try:
        return page.locator("h1").first.inner_text(timeout=2000).strip()
    except Exception:
        return ""


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1400, "height": 900})
    page = ctx.new_page()

    page.goto("http://localhost:8501", wait_until="networkidle")
    time.sleep(5)

    for pg in PAGES:
        ok = page.evaluate(CLICK_JS, pg)
        time.sleep(3.0)  # streamlit re-render
        fname = f"streamlit_{pg.lower().replace(' ', '_')}.png"
        page.screenshot(path=str(OUT / fname), full_page=True)
        h = heading(page)
        body = len(page.inner_text("body"))
        print(f"clicked={ok} {fname}: heading='{h[:45]}' body={body} chars")

    # FastAPI interactive docs
    page.goto("http://localhost:8000/docs", wait_until="networkidle")
    time.sleep(2)
    page.screenshot(path=str(OUT / "fastapi_docs.png"), full_page=True)
    print("fastapi_docs heading:", heading(page))

    browser.close()

print("done ->", OUT.resolve())
