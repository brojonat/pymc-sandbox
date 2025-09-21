"""Router for serving the web UI."""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.templating import Jinja2Templates

from pymc_vibes.db import get_db_connection_from_env

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
async def serve_ab_test(
    request: Request, experiment_name: Optional[str] = Query(default=None)
):
    """Serve the list of A/B test experiments or a detail page."""
    if experiment_name:
        con = get_db_connection_from_env()
        metadata = con.table("_vibes_experiments_metadata")
        experiment = (
            metadata.filter(metadata.name == experiment_name)
            .execute()
            .to_dict("records")
        )
        if not experiment:
            raise HTTPException(
                status_code=404, detail=f"Experiment '{experiment_name}' not found."
            )
        return templates.TemplateResponse(
            "ab_test.html", {"request": request, "experiment": experiment[0]}
        )
    else:
        con = get_db_connection_from_env()
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


# --- Bernoulli Routes ---
@router.get("/bernoulli", include_in_schema=False)
async def serve_bernoulli(
    request: Request, experiment_name: Optional[str] = Query(default=None)
):
    """Serve the list of Bernoulli experiments or a detail page."""
    if experiment_name:
        con = get_db_connection_from_env()
        metadata = con.table("_vibes_experiments_metadata")
        experiment = (
            metadata.filter(metadata.name == experiment_name)
            .execute()
            .to_dict("records")
        )
        if not experiment:
            raise HTTPException(
                status_code=404, detail=f"Experiment '{experiment_name}' not found."
            )
        return templates.TemplateResponse(
            "bernoulli.html",
            {"request": request, "experiment": experiment[0]},
        )
    else:
        con = get_db_connection_from_env()
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


# --- Multi-Armed Bandit Routes ---
@router.get("/multi-armed-bandits", include_in_schema=False)
async def serve_multi_armed_bandits(
    request: Request, experiment_name: Optional[str] = Query(default=None)
):
    """Serve the list of Multi-Armed Bandit experiments or a detail page."""
    if experiment_name:
        con = get_db_connection_from_env()
        metadata = con.table("_vibes_experiments_metadata")
        experiment = (
            metadata.filter(metadata.name == experiment_name)
            .execute()
            .to_dict("records")
        )
        if not experiment:
            raise HTTPException(
                status_code=404, detail=f"Experiment '{experiment_name}' not found."
            )
        return templates.TemplateResponse(
            "multi_armed_bandits.html",
            {"request": request, "experiment": experiment[0]},
        )
    else:
        con = get_db_connection_from_env()
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


# --- Poisson Cohorts Routes ---
@router.get("/poisson-cohorts", include_in_schema=False)
async def serve_poisson_cohorts(
    request: Request, experiment_name: Optional[str] = Query(default=None)
):
    """Serve the list of Poisson Cohort experiments or a detail page."""
    if experiment_name:
        con = get_db_connection_from_env()
        metadata = con.table("_vibes_experiments_metadata")
        experiment = (
            metadata.filter(metadata.name == experiment_name)
            .execute()
            .to_dict("records")
        )
        if not experiment:
            raise HTTPException(
                status_code=404, detail=f"Experiment '{experiment_name}' not found."
            )
        return templates.TemplateResponse(
            "poisson_cohorts.html",
            {"request": request, "experiment": experiment[0]},
        )
    else:
        con = get_db_connection_from_env()
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
