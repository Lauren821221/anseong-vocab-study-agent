import os


def get_api_base_url() -> str:
    return os.getenv(
        "API_BASE_URL",
        "http://localhost:8000/api/v1",
    ).rstrip("/")
