"""poisson_cohorts.py"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/poisson_cohorts")
async def get_poisson_cohorts():
    return {"message": "Hello, World!"}