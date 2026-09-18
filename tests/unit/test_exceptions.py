import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from backend.main import create_app
from backend.core.exceptions import AgentForgeBaseException, NotFoundException, AuthException, PermissionException, ValidationException
from backend.models.constants import ResponseCode
from sqlalchemy.exc import SQLAlchemyError

app = create_app()

@app.get("/test/agentforge_error")
def trigger_agentforge_error():
    raise AgentForgeBaseException(message="Custom Error", code=ResponseCode.MODEL_ERROR, status_code=400)

@app.get("/test/not_found")
def trigger_not_found():
    raise NotFoundException(message="Resource not found")

@app.get("/test/auth")
def trigger_auth():
    raise AuthException(message="Auth failed")

@app.get("/test/db_error")
def trigger_db_error():
    raise SQLAlchemyError("Some DB issue")

@app.get("/test/unhandled")
def trigger_unhandled():
    raise ValueError("Unexpected")

client = TestClient(app, raise_server_exceptions=False)

def test_agentforge_exception_handler():
    response = client.get("/test/agentforge_error")
    assert response.status_code == 400
    data = response.json()
    assert data["code"] == ResponseCode.MODEL_ERROR.value if hasattr(ResponseCode.MODEL_ERROR, "value") else ResponseCode.MODEL_ERROR
    assert data["message"] == "Custom Error"

def test_not_found_exception_handler():
    response = client.get("/test/not_found")
    assert response.status_code == 404
    data = response.json()
    assert data["code"] == ResponseCode.NOT_FOUND.value if hasattr(ResponseCode.NOT_FOUND, "value") else ResponseCode.NOT_FOUND
    assert data["message"] == "Resource not found"

def test_auth_exception_handler():
    response = client.get("/test/auth")
    assert response.status_code == 401
    data = response.json()
    # AuthException defaults to AUTH_REQUIRED
    assert data["code"] == ResponseCode.AUTH_REQUIRED.value if hasattr(ResponseCode.AUTH_REQUIRED, "value") else ResponseCode.AUTH_REQUIRED
    assert data["message"] == "Auth failed"

def test_db_exception_handler():
    response = client.get("/test/db_error")
    assert response.status_code == 500
    data = response.json()
    assert data["code"] == ResponseCode.DATABASE_ERROR.value if hasattr(ResponseCode.DATABASE_ERROR, "value") else ResponseCode.DATABASE_ERROR
    assert "A database error occurred" in data["message"]

def test_unhandled_exception_handler():
    response = client.get("/test/unhandled")
    assert response.status_code == 500
    data = response.json()
    assert data["code"] == ResponseCode.INTERNAL_ERROR.value if hasattr(ResponseCode.INTERNAL_ERROR, "value") else ResponseCode.INTERNAL_ERROR
    assert data["message"] == "An unexpected error occurred"
