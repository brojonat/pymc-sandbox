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
    return templates.TemplateResponse(
        "index.html", {"request": request, "page_title": "Dashboard"}
    )


# --- A/B Test Routes ---
@router.get("/ab-test", include_in_schema=False)
async def serve_ab_test(
    request: Request, experiment_name: Optional[str] = Query(default=None)
):
    """Serve the list of A/B test experiments or a detail page."""
    experiment_type = "ab-test"
    page_title_plural = "A/B Tests"

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
        experiment = experiment[0]
        breadcrumbs = [
            {"name": "Dashboard", "url": "/"},
            {"name": page_title_plural, "url": f"/{experiment_type}"},
            {"name": experiment["name"]},
        ]
        return templates.TemplateResponse(
            "ab_test.html",
            {
                "request": request,
                "experiment": experiment,
                "page_title": experiment["name"],
                "breadcrumbs": breadcrumbs,
            },
        )
    else:
        con = get_db_connection_from_env()
        metadata = con.table("_vibes_experiments_metadata")
        ab_tests = metadata.filter(metadata.type == "ab-test").execute()
        breadcrumbs = [{"name": "Dashboard", "url": "/"}, {"name": page_title_plural}]

        return templates.TemplateResponse(
            "experiments_list.html",
            {
                "request": request,
                "page_title": page_title_plural,
                "table_headers": ["Name", "Status", "Created"],
                "experiments": ab_tests.to_dict("records"),
                "experiment_type": "ab-test",
                "breadcrumbs": breadcrumbs,
            },
        )


# --- Bernoulli Routes ---
@router.get("/bernoulli", include_in_schema=False)
async def serve_bernoulli(
    request: Request, experiment_name: Optional[str] = Query(default=None)
):
    """Serve the list of Bernoulli experiments or a detail page."""
    experiment_type = "bernoulli"
    page_title_plural = "Bernoulli Trials"

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
        experiment = experiment[0]
        breadcrumbs = [
            {"name": "Dashboard", "url": "/"},
            {"name": page_title_plural, "url": f"/{experiment_type}"},
            {"name": experiment["name"]},
        ]
        return templates.TemplateResponse(
            "bernoulli.html",
            {
                "request": request,
                "experiment": experiment,
                "page_title": experiment["name"],
                "breadcrumbs": breadcrumbs,
            },
        )
    else:
        con = get_db_connection_from_env()
        metadata = con.table("_vibes_experiments_metadata")
        bernoulli_tests = metadata.filter(metadata.type == "bernoulli").execute()
        breadcrumbs = [{"name": "Dashboard", "url": "/"}, {"name": page_title_plural}]
        return templates.TemplateResponse(
            "experiments_list.html",
            {
                "request": request,
                "page_title": page_title_plural,
                "table_headers": ["Name", "Status", "Created"],
                "experiments": bernoulli_tests.to_dict("records"),
                "experiment_type": "bernoulli",
                "breadcrumbs": breadcrumbs,
            },
        )


# --- Multi-Armed Bandit Routes ---
@router.get("/multi-armed-bandits", include_in_schema=False)
async def serve_multi_armed_bandits(
    request: Request, experiment_name: Optional[str] = Query(default=None)
):
    """Serve the list of Multi-Armed Bandit experiments or a detail page."""
    experiment_type = "multi-armed-bandits"
    page_title_plural = "Multi-Armed Bandits"

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
        experiment = experiment[0]
        breadcrumbs = [
            {"name": "Dashboard", "url": "/"},
            {"name": page_title_plural, "url": f"/{experiment_type}"},
            {"name": experiment["name"]},
        ]
        return templates.TemplateResponse(
            "multi_armed_bandits.html",
            {
                "request": request,
                "experiment": experiment,
                "page_title": experiment["name"],
                "breadcrumbs": breadcrumbs,
            },
        )
    else:
        con = get_db_connection_from_env()
        metadata = con.table("_vibes_experiments_metadata")
        mab_tests = metadata.filter(metadata.type == "multi-armed-bandits").execute()
        breadcrumbs = [{"name": "Dashboard", "url": "/"}, {"name": page_title_plural}]
        return templates.TemplateResponse(
            "experiments_list.html",
            {
                "request": request,
                "page_title": page_title_plural,
                "table_headers": ["Name", "Status", "Created"],
                "experiments": mab_tests.to_dict("records"),
                "experiment_type": "multi-armed-bandits",
                "breadcrumbs": breadcrumbs,
            },
        )


# --- Poisson Cohorts Routes ---
@router.get("/poisson-cohorts", include_in_schema=False)
async def serve_poisson_cohorts(
    request: Request, experiment_name: Optional[str] = Query(default=None)
):
    """Serve the list of Poisson Cohort experiments or a detail page."""
    experiment_type = "poisson-cohorts"
    page_title_plural = "Poisson Cohorts"
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
        experiment = experiment[0]
        breadcrumbs = [
            {"name": "Dashboard", "url": "/"},
            {"name": page_title_plural, "url": f"/{experiment_type}"},
            {"name": experiment["name"]},
        ]
        return templates.TemplateResponse(
            "poisson_cohorts.html",
            {
                "request": request,
                "experiment": experiment,
                "page_title": experiment["name"],
                "breadcrumbs": breadcrumbs,
            },
        )
    else:
        con = get_db_connection_from_env()
        metadata = con.table("_vibes_experiments_metadata")
        poisson_tests = metadata.filter(metadata.type == "poisson-cohorts").execute()
        breadcrumbs = [{"name": "Dashboard", "url": "/"}, {"name": page_title_plural}]
        return templates.TemplateResponse(
            "experiments_list.html",
            {
                "request": request,
                "page_title": page_title_plural,
                "table_headers": ["Name", "Status", "Created"],
                "experiments": poisson_tests.to_dict("records"),
                "experiment_type": "poisson-cohorts",
                "breadcrumbs": breadcrumbs,
            },
        )


# --- Weibull Routes ---
@router.get("/weibull", include_in_schema=False)
async def serve_weibull(
    request: Request, experiment_name: Optional[str] = Query(default=None)
):
    """Serve the list of Weibull experiments or a detail page."""
    experiment_type = "weibull"
    page_title_plural = "Weibull Experiments"

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
        experiment = experiment[0]
        breadcrumbs = [
            {"name": "Dashboard", "url": "/"},
            {"name": page_title_plural, "url": f"/{experiment_type}"},
            {"name": experiment["name"]},
        ]
        return templates.TemplateResponse(
            "weibull.html",
            {
                "request": request,
                "experiment": experiment,
                "page_title": experiment["name"],
                "breadcrumbs": breadcrumbs,
            },
        )
    else:
        con = get_db_connection_from_env()
        metadata = con.table("_vibes_experiments_metadata")
        weibull_tests = metadata.filter(metadata.type == "weibull").execute()
        breadcrumbs = [{"name": "Dashboard", "url": "/"}, {"name": page_title_plural}]
        return templates.TemplateResponse(
            "experiments_list.html",
            {
                "request": request,
                "page_title": page_title_plural,
                "table_headers": ["Name", "Status", "Created"],
                "experiments": weibull_tests.to_dict("records"),
                "experiment_type": "weibull",
                "breadcrumbs": breadcrumbs,
            },
        )


# --- Hazard Rate Routes ---
@router.get("/hazard-rate", include_in_schema=False)
async def serve_hazard_rate(
    request: Request, experiment_name: Optional[str] = Query(default=None)
):
    """Serve the list of Hazard Rate experiments or a detail page."""
    experiment_type = "hazard-rate"
    page_title_plural = "Hazard Rate Experiments"

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
        experiment = experiment[0]
        breadcrumbs = [
            {"name": "Dashboard", "url": "/"},
            {"name": page_title_plural, "url": f"/{experiment_type}"},
            {"name": experiment["name"]},
        ]
        return templates.TemplateResponse(
            "hazard_rate.html",
            {
                "request": request,
                "experiment": experiment,
                "page_title": experiment["name"],
                "breadcrumbs": breadcrumbs,
            },
        )
    else:
        con = get_db_connection_from_env()
        metadata = con.table("_vibes_experiments_metadata")
        hazard_tests = metadata.filter(metadata.type == "hazard-rate").execute()
        breadcrumbs = [{"name": "Dashboard", "url": "/"}, {"name": page_title_plural}]
        return templates.TemplateResponse(
            "experiments_list.html",
            {
                "request": request,
                "page_title": page_title_plural,
                "table_headers": ["Name", "Status", "Created"],
                "experiments": hazard_tests.to_dict("records"),
                "experiment_type": "hazard-rate",
                "breadcrumbs": breadcrumbs,
            },
        )
