def test_backend_import_exposes_fastapi_app():
    import backend.main

    assert type(backend.main.app).__name__ == "FastAPI"
