"""Router for serving the web UI."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from pymc_vibes.server.database import get_db_connection

router = APIRouter()

# Path to the templates directory
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@router.get("/", include_in_schema=False)
async def serve_index(request: Request):
    """Serve the main index.html file for the web UI."""
    return templates.TemplateResponse("index.html", {"request": request})


# --- A/B Test Routes ---
@router.get("/ab-test", include_in_schema=False)
async def serve_ab_test_list(request: Request):
    """Serve the list of A/B test experiments."""
    con = get_db_connection()
    metadata = con.table("_vibes_experiments_metadata")
    ab_tests = metadata.filter(metadata.type == "ab-test").execute()

    return templates.TemplateResponse(
        "experiments_list.html",
        {
            "request": request,
            "page_title": "A/B Tests",
            "table_headers": ["Name", "Status", "Created"],
            "experiments": ab_tests.to_dict("records"),
            "experiment_type": "ab-test",
        },
    )


@router.get("/ab-test/{experiment_id}", include_in_schema=False)
async def serve_ab_test_detail(request: Request, experiment_id: str):
    """Serve the detail page for a specific A/B test experiment."""
    return templates.TemplateResponse(
        "ab_test.html", {"request": request, "experiment_id": experiment_id}
    )


# --- Bernoulli Routes ---
@router.get("/bernoulli", include_in_schema=False)
async def serve_bernoulli_list(request: Request):
    """Serve the list of Bernoulli experiments."""
    con = get_db_connection()
    metadata = con.table("_vibes_experiments_metadata")
    bernoulli_tests = metadata.filter(metadata.type == "bernoulli").execute()
    return templates.TemplateResponse(
        "experiments_list.html",
        {
            "request": request,
            "page_title": "Bernoulli Trials",
            "table_headers": ["Name", "Status", "Created"],
            "experiments": bernoulli_tests.to_dict("records"),
            "experiment_type": "bernoulli",
        },
    )


@router.get("/bernoulli/{experiment_id}", include_in_schema=False)
async def serve_bernoulli_detail(request: Request, experiment_id: str):
    """Serve the detail page for a specific Bernoulli experiment."""
    return templates.TemplateResponse(
        "bernoulli.html", {"request": request, "experiment_id": experiment_id}
    )


# --- Multi-Armed Bandit Routes ---
@router.get("/multi-armed-bandits", include_in_schema=False)
async def serve_multi_armed_bandits_list(request: Request):
    """Serve the list of Multi-Armed Bandit experiments."""
    con = get_db_connection()
    metadata = con.table("_vibes_experiments_metadata")
    mab_tests = metadata.filter(metadata.type == "multi-armed-bandits").execute()
    return templates.TemplateResponse(
        "experiments_list.html",
        {
            "request": request,
            "page_title": "Multi-Armed Bandits",
            "table_headers": ["Name", "Status", "Created"],
            "experiments": mab_tests.to_dict("records"),
            "experiment_type": "multi-armed-bandits",
        },
    )


@router.get("/multi-armed-bandits/{experiment_id}", include_in_schema=False)
async def serve_multi_armed_bandits_detail(request: Request, experiment_id: str):
    """Serve the detail page for a specific Multi-Armed Bandit experiment."""
    return templates.TemplateResponse(
        "multi_armed_bandits.html",
        {"request": request, "experiment_id": experiment_id},
    )


# --- Poisson Cohorts Routes ---
@router.get("/poisson-cohorts", include_in_schema=False)
async def serve_poisson_cohorts_list(request: Request):
    """Serve the list of Poisson Cohort experiments."""
    con = get_db_connection()
    metadata = con.table("_vibes_experiments_metadata")
    poisson_tests = metadata.filter(metadata.type == "poisson-cohorts").execute()
    return templates.TemplateResponse(
        "experiments_list.html",
        {
            "request": request,
            "page_title": "Poisson Cohorts",
            "table_headers": ["Name", "Status", "Created"],
            "experiments": poisson_tests.to_dict("records"),
            "experiment_type": "poisson-cohorts",
        },
    )


@router.get("/poisson-cohorts/{experiment_id}", include_in_schema=False)
async def serve_poisson_cohorts_detail(request: Request, experiment_id: str):
    """Serve the detail page for a specific Poisson Cohort experiment."""
    return templates.TemplateResponse(
        "poisson_cohorts.html",
        {"request": request, "experiment_id": experiment_id},
    )
