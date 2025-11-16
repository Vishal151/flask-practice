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

# Mock flask_jwt if not available
try:
    import flask_jwt
except ImportError:
    # Create a mock flask_jwt module
    flask_jwt = Mock()
    flask_jwt.JWT = Mock(return_value=Mock())
    flask_jwt.jwt_required = lambda: lambda f: f  # Mock decorator
    flask_jwt.current_identity = Mock()
    sys.modules['flask_jwt'] = flask_jwt

from app import app as flask_app


@pytest.fixture(scope='function')
def app():
    """Create and configure a new app instance for each test."""
    # Use in-memory database for testing
    flask_app.config.update({
        'TESTING': True,
        'SECRET_KEY': 'test-secret-key',
    })

    yield flask_app


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
