import os
import pytest
from fastapi.testclient import TestClient

# Important: Skip external Guardrails to ensure local measurability
os.environ["BYPASS_GUARDRAILS"] = "1"

# from rag.app import app  

@pytest.fixture(scope="session")
def client():
    return TestClient(app)
