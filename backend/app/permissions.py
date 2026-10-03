from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.security import decode_access_token


security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Validate the JWT token and return the authenticated user payload.
    """

    token = credentials.credentials

    payload = decode_access_token(token)

    return payload


def require_role(*allowed_roles: str):
    """
    Allow access only to users with one of the specified roles.
    """

    def role_checker(
        current_user: dict = Depends(get_current_user)
    ):
        user_role = current_user.get("role")

        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Access denied. Required role: "
                    + ", ".join(allowed_roles)
                )
            )

        return current_user

    return role_checker


def require_farmer(
    current_user: dict = Depends(get_current_user)
):
    """
    Farmer-only permission.
    """

    if current_user.get("role") != "farmer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Farmer access required."
        )

    return current_user


def require_veterinarian(
    current_user: dict = Depends(get_current_user)
):
    """
    Veterinarian-only permission.
    """

    if current_user.get("role") != "veterinarian":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Veterinarian access required."
        )

    return current_user


def require_admin(
    current_user: dict = Depends(get_current_user)
):
    """
    Admin-only permission.
    """

    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required."
        )

    return current_user


def require_vet_or_admin(
    current_user: dict = Depends(get_current_user)
):
    """
    Veterinarian or administrator permission.
    """

    if current_user.get("role") not in [
        "veterinarian",
        "admin"
    ]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Veterinarian or administrator access required."
        )

    return current_user


def require_any_authenticated_user(
    current_user: dict = Depends(get_current_user)
):
    """
    Any authenticated VETRA user.
    """

    return current_user