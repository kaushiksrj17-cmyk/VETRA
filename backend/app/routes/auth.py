from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from app.database import get_database
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    UserResponse,
    TokenResponse
)
from app.security import (
    hash_password,
    verify_password,
    create_access_token
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
def register_user(user: UserRegister):
    """
    Register a new VETRA farmer account.
    Public registration always creates a farmer account.
    """

    db = get_database()

    existing_user = db.users.find_one({
        "email": user.email.lower()
    })

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists."
        )

    now = datetime.now(timezone.utc)

    new_user = {
        "full_name": user.full_name.strip(),
        "email": user.email.lower(),
        "password_hash": hash_password(user.password),
        "role": "farmer",
        "is_active": True,
        "created_at": now,
        "updated_at": now
    }

    result = db.users.insert_one(new_user)

    return UserResponse(
        id=str(result.inserted_id),
        full_name=new_user["full_name"],
        email=new_user["email"],
        role=new_user["role"],
        is_active=True
    )


@router.post(
    "/login",
    response_model=TokenResponse
)
def login_user(user: UserLogin):
    """
    Authenticate a VETRA user and return a JWT token.
    """

    db = get_database()

    existing_user = db.users.find_one({
        "email": user.email.lower()
    })

    if not existing_user:
        db.audit_logs.insert_one({
            "action": "USER_LOGIN_FAILED",
            "email": user.email.lower(),
            "reason": "invalid_credentials",
            "timestamp": datetime.now(timezone.utc)
        })
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={
                "WWW-Authenticate": "Bearer"
            }
        )

    if not existing_user.get("is_active", False):
        db.audit_logs.insert_one({
            "action": "USER_LOGIN_FAILED",
            "user_id": str(existing_user["_id"]),
            "email": existing_user["email"],
            "reason": "account_inactive",
            "timestamp": datetime.now(timezone.utc)
        })
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This user account is inactive."
        )

    if not verify_password(
        user.password,
        existing_user["password_hash"]
    ):
        db.audit_logs.insert_one({
            "action": "USER_LOGIN_FAILED",
            "user_id": str(existing_user["_id"]),
            "email": existing_user["email"],
            "reason": "invalid_credentials",
            "timestamp": datetime.now(timezone.utc)
        })
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={
                "WWW-Authenticate": "Bearer"
            }
        )

    token_data = {
        "sub": str(existing_user["_id"]),
        "email": existing_user["email"],
        "role": existing_user["role"]
    }

    access_token = create_access_token(
        token_data
    )

    db.audit_logs.insert_one({
        "action": "USER_LOGIN",
        "user_id": str(existing_user["_id"]),
        "email": existing_user["email"],
        "role": existing_user["role"],
        "timestamp": datetime.now(timezone.utc)
    })

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=str(existing_user["_id"]),
            full_name=existing_user["full_name"],
            email=existing_user["email"],
            role=existing_user["role"],
            is_active=existing_user["is_active"]
        )
    )