"""
Pytest configuration and fixtures for testing.
"""
import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock
import sqlite3

# Add code directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../code'))

# Check if Flask-JWT is actually available (not mocked)
FLASK_JWT_AVAILABLE = False
try:
    import flask_jwt
    # Verify it's the real module, not a mock
    if hasattr(flask_jwt, '__version__') or hasattr(flask_jwt.JWT, '__call__'):
        FLASK_JWT_AVAILABLE = True
except (ImportError, AttributeError):
    pass

# Mock flask_jwt if not available
if not FLASK_JWT_AVAILABLE:
    flask_jwt = Mock()
    flask_jwt.JWT = Mock(return_value=Mock())
    flask_jwt.jwt_required = lambda: lambda f: f  # Mock decorator
    flask_jwt.current_identity = Mock()
    sys.modules['flask_jwt'] = flask_jwt

from app import app as flask_app


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "requires_auth: mark test as requiring JWT authentication"
    )


def pytest_collection_modifyitems(config, items):
    """Skip tests that require Flask-JWT if it's not available."""
    skip_jwt = pytest.mark.skip(reason="Flask-JWT not available")
    for item in items:
        if "requires_auth" in item.keywords and not FLASK_JWT_AVAILABLE:
            item.add_marker(skip_jwt)


@pytest.fixture(scope='function')
def app(monkeypatch):
    """Create and configure a new app instance for each test."""
    # Create a temporary test database
    db_fd, db_path = tempfile.mkstemp()
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    # Create tables for testing
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username text, password text)"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS items (name text PRIMARY KEY, price real)"
    )
    connection.commit()
    connection.close()

    # Store original connect function
    original_connect = sqlite3.connect

    # Monkeypatch sqlite3.connect to use test database
    def mock_connect(db_name, *args, **kwargs):
        return original_connect(db_path, *args, **kwargs)

    monkeypatch.setattr(sqlite3, 'connect', mock_connect)

    # Configure app for testing
    flask_app.config.update({
        'TESTING': True,
        'SECRET_KEY': 'test-secret-key',
    })

    yield flask_app

    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture(scope='function')
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture(scope='function')
def db_connection():
    """Create a test database connection."""
    # Create temporary database file
    db_fd, db_path = tempfile.mkstemp()
    connection = sqlite3.connect(db_path)

    yield connection

    # Cleanup
    connection.close()
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture(scope='function')
def init_database():
    """Initialize test database with tables."""
    db_fd, db_path = tempfile.mkstemp()
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    # Create tables
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username text, password text)"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS items (name text PRIMARY KEY, price real)"
    )

    connection.commit()

    yield connection, db_path

    # Cleanup
    connection.close()
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def auth_token(client):
    """Get a valid JWT token for testing authenticated endpoints."""
    # First register a user
    client.post('/register', json={
        'username': 'testuser',
        'password': 'testpass'
    })

    # Then authenticate to get token
    response = client.post('/auth', json={
        'username': 'testuser',
        'password': 'testpass'
    })

    token = response.json['access_token']
    return token
