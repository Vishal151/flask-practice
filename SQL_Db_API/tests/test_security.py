"""
Unit tests for authentication and security functions.
"""
import sys
import os
import sqlite3
import tempfile
import pytest

# Add code directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../code'))

from security import authenticate, identity
from user import User
from passlib.hash import pbkdf2_sha256


class TestAuthenticate:
    """Test authentication function."""

    def setup_method(self):
        """Create a temporary database for each test."""
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.connection = sqlite3.connect(self.db_path)
        self.cursor = self.connection.cursor()

        # Create users table
        self.cursor.execute(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, username text, password text)"
        )
        self.connection.commit()

        # Store original connection function
        self._original_connect = sqlite3.connect

        # Monkey patch sqlite3.connect to use test database
        def mock_connect(db_name, *args, **kwargs):
            return self._original_connect(self.db_path, *args, **kwargs)

        sqlite3.connect = mock_connect

    def teardown_method(self):
        """Clean up temporary database."""
        sqlite3.connect = self._original_connect
        self.connection.close()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_authenticate_valid_credentials(self):
        """Test authentication with correct username and password."""
        # Create a user with hashed password
        hashed_pw = pbkdf2_sha256.hash("correctpass")
        self.cursor.execute(
            "INSERT INTO users VALUES (1, 'validuser', ?)", (hashed_pw,)
        )
        self.connection.commit()

        # Authenticate
        user = authenticate('validuser', 'correctpass')

        assert user is not None
        assert user.username == 'validuser'
        assert user.id == 1

    def test_authenticate_wrong_password(self):
        """Test authentication with correct username but wrong password."""
        hashed_pw = pbkdf2_sha256.hash("correctpass")
        self.cursor.execute(
            "INSERT INTO users VALUES (1, 'validuser', ?)", (hashed_pw,)
        )
        self.connection.commit()

        # Try to authenticate with wrong password
        user = authenticate('validuser', 'wrongpass')

        assert user is None

    def test_authenticate_nonexistent_user(self):
        """Test authentication with non-existent username."""
        user = authenticate('nonexistent', 'anypass')
        assert user is None

    def test_authenticate_empty_password(self):
        """Test authentication with empty password."""
        hashed_pw = pbkdf2_sha256.hash("correctpass")
        self.cursor.execute(
            "INSERT INTO users VALUES (1, 'validuser', ?)", (hashed_pw,)
        )
        self.connection.commit()

        user = authenticate('validuser', '')
        assert user is None

    def test_authenticate_case_sensitive_username(self):
        """Test that username authentication is case-sensitive."""
        hashed_pw = pbkdf2_sha256.hash("testpass")
        self.cursor.execute(
            "INSERT INTO users VALUES (1, 'TestUser', ?)", (hashed_pw,)
        )
        self.connection.commit()

        # Exact match should work
        user = authenticate('TestUser', 'testpass')
        assert user is not None

        # Different case should not work
        user = authenticate('testuser', 'testpass')
        assert user is None


class TestIdentity:
    """Test identity function for JWT payload."""

    def setup_method(self):
        """Create a temporary database for each test."""
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.connection = sqlite3.connect(self.db_path)
        self.cursor = self.connection.cursor()

        # Create users table
        self.cursor.execute(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, username text, password text)"
        )
        self.connection.commit()

        # Store original connection function
        self._original_connect = sqlite3.connect

        # Monkey patch sqlite3.connect to use test database
        def mock_connect(db_name, *args, **kwargs):
            return self._original_connect(self.db_path, *args, **kwargs)

        sqlite3.connect = mock_connect

    def teardown_method(self):
        """Clean up temporary database."""
        sqlite3.connect = self._original_connect
        self.connection.close()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_identity_valid_user_id(self):
        """Test identity function with valid user ID."""
        # Create a user
        hashed_pw = pbkdf2_sha256.hash("testpass")
        self.cursor.execute(
            "INSERT INTO users VALUES (5, 'testuser', ?)", (hashed_pw,)
        )
        self.connection.commit()

        # Get user from payload
        payload = {'identity': 5}
        user = identity(payload)

        assert user is not None
        assert user.id == 5
        assert user.username == 'testuser'

    def test_identity_invalid_user_id(self):
        """Test identity function with non-existent user ID."""
        payload = {'identity': 999}
        user = identity(payload)

        assert user is None

    def test_identity_extracts_correct_field(self):
        """Test that identity function extracts 'identity' field from payload."""
        # Create users with different IDs
        hashed_pw = pbkdf2_sha256.hash("testpass")
        self.cursor.execute(
            "INSERT INTO users VALUES (1, 'user1', ?)", (hashed_pw,)
        )
        self.cursor.execute(
            "INSERT INTO users VALUES (2, 'user2', ?)", (hashed_pw,)
        )
        self.connection.commit()

        # Should get user with ID 2
        payload = {'identity': 2, 'other_field': 1}
        user = identity(payload)

        assert user.id == 2
        assert user.username == 'user2'


class TestAuthenticationIntegration:
    """Test authentication flow end-to-end."""

    def test_auth_endpoint_success(self, client):
        """Test successful authentication through /auth endpoint."""
        # Register a user
        client.post('/register', json={
            'username': 'authuser',
            'password': 'authpass123'
        })

        # Authenticate
        response = client.post('/auth', json={
            'username': 'authuser',
            'password': 'authpass123'
        })

        assert response.status_code == 200
        assert 'access_token' in response.json

    def test_auth_endpoint_wrong_password(self, client):
        """Test authentication with wrong password."""
        # Register a user
        client.post('/register', json={
            'username': 'authuser',
            'password': 'correctpass'
        })

        # Try to authenticate with wrong password
        response = client.post('/auth', json={
            'username': 'authuser',
            'password': 'wrongpass'
        })

        assert response.status_code == 401

    def test_auth_endpoint_nonexistent_user(self, client):
        """Test authentication with non-existent user."""
        response = client.post('/auth', json={
            'username': 'nonexistent',
            'password': 'anypass'
        })

        assert response.status_code == 401

    def test_jwt_token_can_be_used(self, client):
        """Test that JWT token from /auth can be used for protected endpoints."""
        # Register a user
        client.post('/register', json={
            'username': 'tokenuser',
            'password': 'tokenpass'
        })

        # Get token
        auth_response = client.post('/auth', json={
            'username': 'tokenuser',
            'password': 'tokenpass'
        })
        token = auth_response.json['access_token']

        # Create an item first (doesn't require auth)
        client.post('/item/testitem', json={'price': 9.99})

        # Use token to access protected endpoint
        response = client.get('/item/testitem', headers={
            'Authorization': f'JWT {token}'
        })

        assert response.status_code == 200
