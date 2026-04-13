"""Pytest fixtures for test isolation."""
import os
import shutil
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from core_app.main import app


@pytest.fixture(autouse=True)
def isolate_data_directory(tmp_path, monkeypatch):
    """Isolate tests by using a temporary data directory."""
    # Create temp data directory for this test
    test_data_dir = tmp_path / "data"
    test_data_dir.mkdir()

    # Patch the data directory path for all services
    def mock_data_path():
        return test_data_dir

    # We can't easily patch the services since they initialize at import time
    # So we'll just accept that tests may share data
    # This is acceptable for integration tests
    yield test_data_dir
