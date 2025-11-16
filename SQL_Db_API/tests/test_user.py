"""
Unit tests for User model and UserRegister endpoint.
"""
import sys
import os
import sqlite3
import tempfile
import pytest

# Add code directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../code'))

from user import User, UserRegister
from passlib.hash import pbkdf2_sha256


class TestUserModel:
    """Test User model database operations."""

    def setup_method(self, monkeypatch=None):
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

    def test_find_by_username_existing_user(self):
        """Test finding a user that exists in database."""
        # Insert a test user
        hashed_pw = pbkdf2_sha256.hash("testpass")
        self.cursor.execute(
            "INSERT INTO users VALUES (1, 'testuser', ?)", (hashed_pw,)
        )
        self.connection.commit()

        # Find the user
        user = User.find_by_username('testuser')

        assert user is not None
        assert user.id == 1
        assert user.username == 'testuser'
        assert user.password == hashed_pw

    def test_find_by_username_nonexistent_user(self):
        """Test finding a user that doesn't exist."""
        user = User.find_by_username('nonexistent')
        assert user is None

    def test_find_by_id_existing_user(self):
        """Test finding a user by ID that exists."""
        hashed_pw = pbkdf2_sha256.hash("testpass")
        self.cursor.execute(
            "INSERT INTO users VALUES (42, 'testuser', ?)", (hashed_pw,)
        )
        self.connection.commit()

        user = User.find_by_id(42)

        assert user is not None
        assert user.id == 42
        assert user.username == 'testuser'

    def test_find_by_id_nonexistent_user(self):
        """Test finding a user by ID that doesn't exist."""
        user = User.find_by_id(999)
        assert user is None

    def test_user_initialization(self):
        """Test User object initialization."""
        user = User(1, 'testuser', 'hashed_password')

        assert user.id == 1
        assert user.username == 'testuser'
        assert user.password == 'hashed_password'


class TestUserRegister:
    """Test UserRegister resource endpoint."""

    def test_post_new_user_success(self, client):
        """Test successful user registration."""
        response = client.post('/register', json={
            'username': 'newuser',
            'password': 'securepass123'
        })

        assert response.status_code == 201
        assert response.json['message'] == 'User created successfully.'

        # Verify user was created with hashed password
        user = User.find_by_username('newuser')
        assert user is not None
        assert user.username == 'newuser'
        # Password should be hashed, not plain text
        assert user.password != 'securepass123'
        assert pbkdf2_sha256.verify('securepass123', user.password)

    def test_post_duplicate_username(self, client):
        """Test registering with an existing username."""
        # Register first user
        client.post('/register', json={
            'username': 'duplicate',
            'password': 'pass1'
        })

        # Try to register with same username
        response = client.post('/register', json={
            'username': 'duplicate',
            'password': 'pass2'
        })

        assert response.status_code == 400
        assert 'already exists' in response.json['message']

    def test_post_missing_username(self, client):
        """Test registration without username."""
        response = client.post('/register', json={
            'password': 'testpass'
        })

        assert response.status_code == 400
        assert 'username' in str(response.json).lower()

    def test_post_missing_password(self, client):
        """Test registration without password."""
        response = client.post('/register', json={
            'username': 'testuser'
        })

        assert response.status_code == 400
        assert 'password' in str(response.json).lower()

    def test_post_empty_username(self, client):
        """Test registration with empty username."""
        response = client.post('/register', json={
            'username': '',
            'password': 'testpass'
        })

        # Should either reject or accept - document current behavior
        # Most likely will be accepted by reqparse, might want to add validation
        assert response.status_code in [201, 400]

    def test_password_is_hashed(self, client):
        """Test that passwords are properly hashed before storage."""
        plain_password = 'mySecretPassword123'

        client.post('/register', json={
            'username': 'hashtest',
            'password': plain_password
        })

        user = User.find_by_username('hashtest')

        # Password should not be stored in plain text
        assert user.password != plain_password

        # Password should be verifiable with passlib
        assert pbkdf2_sha256.verify(plain_password, user.password)

        # Hash should be different each time (salt is random)
        hashed_pw1 = user.password
        hashed_pw2 = pbkdf2_sha256.hash(plain_password)
        assert hashed_pw1 != hashed_pw2  # Different salts
