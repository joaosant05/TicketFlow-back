from typing import Optional

from fastapi import APIRouter, Query

from services import reference_service


router = APIRouter(prefix="/api", tags=["referencias"])


@router.get("/departamentos")
def list_departments():
    return reference_service.list_departments()


@router.get("/categorias")
def list_categories():
    return reference_service.list_categories()


@router.get("/usuarios")
def list_users(role: Optional[str] = Query(default=None)):
    return reference_service.list_users(role)
