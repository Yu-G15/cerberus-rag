import os
import pytest
from fastapi.testclient import TestClient

# 重要：跳过外部 Guardrails，确保本地可测
os.environ["BYPASS_GUARDRAILS"] = "1"

# from rag.app import app  

@pytest.fixture(scope="session")
def client():
    return TestClient(app)
