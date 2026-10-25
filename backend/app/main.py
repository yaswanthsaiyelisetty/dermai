import os

import psycopg
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from backend.app.auth import (
    LoginRequest,
    RegistrationRequest,
    get_current_user,
    get_optional_current_user,
    login_user,
    register_user,
)
from backend.app.cases import (
    CaseCreate,
    CaseUpdate,
    attach_image,
    create_case,
    delete_case,
    get_case,
    list_cases,
    update_case,
)
from backend.app.database import get_db_connection
from backend.app.uploads import validate_image_upload

load_dotenv()

app = FastAPI(
    title="DermAI API",
    description="Backend API for the DermAI skin image project",
    version="0.1.0",
)
frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/")
def home():
    return {"message": "Welcome to DermAI API!", "status": "running"}


@app.get("/health")
def health_check():
    return {"status": "healthy", "project": "DermAI"}


@app.post("/auth/register", status_code=201)
def register(request: RegistrationRequest):
    return register_user(request)


@app.post("/auth/login")
def login(request: LoginRequest):
    return login_user(request)


@app.post("/images/upload")
async def upload_image(
    file: UploadFile = File(...),
    case_id: int | None = None,
    current_user: dict | None = Depends(get_optional_current_user),
):
    image_details = await validate_image_upload(file)
    if case_id is not None:
        if current_user is None:
            raise HTTPException(status_code=401, detail="Authentication required for case association")
        attach_image(current_user["id"], case_id, image_details)
    return {"message": "Image uploaded and validated", "image": image_details}


@app.post("/cases", status_code=201)
def create_case_endpoint(
    request: CaseCreate,
    current_user: dict = Depends(get_current_user),
):
    return create_case(current_user["id"], request)


@app.get("/cases")
def list_cases_endpoint(current_user: dict = Depends(get_current_user)):
    return list_cases(current_user["id"])


@app.get("/cases/{case_id}")
def get_case_endpoint(
    case_id: int,
    current_user: dict = Depends(get_current_user),
):
    return get_case(current_user["id"], case_id)


@app.patch("/cases/{case_id}")
def update_case_endpoint(
    case_id: int,
    request: CaseUpdate,
    current_user: dict = Depends(get_current_user),
):
    return update_case(current_user["id"], case_id, request)


@app.delete("/cases/{case_id}", status_code=204)
def delete_case_endpoint(
    case_id: int,
    current_user: dict = Depends(get_current_user),
):
    delete_case(current_user["id"], case_id)


@app.get("/health/database")
def database_health_check():
    db_config = {
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT"),
        "dbname": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
    }

    try:
        with psycopg.connect(**db_config, connect_timeout=5) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()

        return {"status": "connected", "database": "dermai_db"}

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed",
        ) from exc


@app.get("/predictions/history")
def get_prediction_history():
    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, image_filename, predicted_class,
                           confidence, created_at
                    FROM prediction_history
                    ORDER BY created_at DESC
                    LIMIT 50
                    """
                )
                rows = cursor.fetchall()

        return [
            {
                "id": row[0],
                "image_filename": row[1],
                "predicted_class": row[2],
                "confidence": row[3],
                "created_at": row[4].isoformat(),
            }
            for row in rows
        ]

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Could not retrieve prediction history",
        ) from exc
