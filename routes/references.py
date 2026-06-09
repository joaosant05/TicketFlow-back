from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from services import reference_service


router = APIRouter(prefix="/api", tags=["referencias"])


class UserCreate(BaseModel):
    nome: str
    email: str
    role: Optional[str] = None
    papel: Optional[str] = None
    auth0Id: Optional[str] = None
    departamentoId: Optional[int] = None
    departamento: Optional[str] = None


@router.get("/departamentos")
def list_departments():
    return reference_service.list_departments()


@router.get("/categorias")
def list_categories():
    return reference_service.list_categories()


@router.get("/usuarios")
def list_users(role: Optional[str] = Query(default=None)):
    return reference_service.list_users(role)


@router.get("/users")
def list_users_alias(role: Optional[str] = Query(default=None)):
    return list_users(role)


@router.post("/usuarios", status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate):
    try:
        return reference_service.create_user(payload.dict(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_user_alias(payload: UserCreate):
    return create_user(payload)


@router.get("/admin/usuarios")
def list_admin_users():
    return reference_service.list_users()


@router.get("/admin/users")
def list_admin_users_alias():
    return list_admin_users()


@router.post("/admin/usuarios", status_code=status.HTTP_201_CREATED)
def create_admin_user(payload: UserCreate):
    try:
        return reference_service.create_user(payload.dict(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/admin/users", status_code=status.HTTP_201_CREATED)
def create_admin_user_alias(payload: UserCreate):
    return create_admin_user(payload)


@router.patch("/admin/usuarios/roles")
def update_user_roles(payload: dict):
    return reference_service.update_user_roles(payload)


@router.patch("/admin/users/roles")
def update_user_roles_alias(payload: dict):
    return update_user_roles(payload)
