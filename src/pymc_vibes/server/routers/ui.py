"""Router for serving the web UI."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

# Path to the templates directory
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_index():
    """Serve the main index.html file for the web UI."""
    index_path = TEMPLATES_DIR / "index.html"
    if not index_path.exists():
        return HTMLResponse(
            "<html><body><h1>Index file not found</h1></body></html>", status_code=404
        )
    with open(index_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@router.get("/poisson-cohorts", response_class=HTMLResponse, include_in_schema=False)
async def serve_poisson_cohorts():
    """Serve the poisson_cohorts.html file for the web UI."""
    page_path = TEMPLATES_DIR / "poisson_cohorts.html"
    if not page_path.exists():
        return HTMLResponse(
            "<html><body><h1>Poisson Cohorts file not found</h1></body></html>",
            status_code=404,
        )
    with open(page_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())
