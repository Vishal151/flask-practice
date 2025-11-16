# Flask RESTful API with SQLite

A RESTful API built with Flask, featuring user authentication with JWT and item management.

## Features

- User registration and authentication with JWT tokens
- Password hashing with PBKDF2-SHA256
- CRUD operations for items
- SQLite database storage
- Comprehensive test suite with pytest

## Security Improvements

This codebase includes several security enhancements:

1. **Password Hashing**: Passwords are hashed using PBKDF2-SHA256 before storage
2. **Environment Variables**: Secret keys are loaded from environment variables
3. **Parameterized Queries**: All SQL queries use parameterized statements to prevent SQL injection

## Installation

### Dependencies

**Note**: Flask-JWT has compatibility issues with newer Python versions. You may need to install it manually or use an alternative.

```bash
# Install core dependencies
pip install -r requirements-dev.txt

# If Flask-JWT fails to install, try:
pip install flask-jwt --no-build-isolation

# Or use a more recent alternative (requires code changes):
pip install Flask-JWT-Extended
```

### Environment Configuration

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Update the `.env` file with your configuration:
   ```
   SECRET_KEY=your-secret-key-here
   DATABASE_PATH=data.db
   ```

## Running the Application

```bash
cd code
python app.py
```

The API will be available at `http://localhost:5000`.

## API Endpoints

### Authentication

- `POST /register` - Register a new user
  ```json
  {
    "username": "user",
    "password": "pass"
  }
  ```

- `POST /auth` - Authenticate and get JWT token
  ```json
  {
    "username": "user",
    "password": "pass"
  }
  ```

### Items

- `GET /items` - List all items (no auth required)
- `GET /item/<name>` - Get item details (requires JWT)
- `POST /item/<name>` - Create new item
  ```json
  {
    "price": 19.99
  }
  ```
- `PUT /item/<name>` - Update or create item
- `DELETE /item/<name>` - Delete item

## Running Tests

The project includes comprehensive tests for:
- User model and registration
- Authentication and security
- Item CRUD operations
- API integration scenarios

### Run all tests:

```bash
cd SQL_Db_API
pytest tests/ -v
```

### Run with coverage:

```bash
pytest tests/ --cov=code --cov-report=html --cov-report=term
```

### Run specific test files:

```bash
pytest tests/test_user.py -v
pytest tests/test_security.py -v
pytest tests/test_item.py -v
pytest tests/test_api_integration.py -v
```

## Test Coverage

The test suite includes:

- **Unit Tests**:
  - User model (find_by_username, find_by_id)
  - User registration with duplicate detection
  - Password hashing verification
  - Authentication functions
  - Item model (CRUD operations)

- **Integration Tests**:
  - Complete user workflow (register → login → use token)
  - Item lifecycle (create → read → update → delete)
  - Multiple users and items
  - Authentication edge cases
  - Data persistence

## Project Structure

```
SQL_Db_API/
├── code/
│   ├── app.py           # Main application
│   ├── user.py          # User model and registration
│   ├── security.py      # Authentication functions
│   ├── item.py          # Item model and endpoints
│   └── create_tables.py # Database initialization
├── tests/
│   ├── conftest.py      # Pytest fixtures
│   ├── test_user.py     # User tests
│   ├── test_security.py # Security tests
│   ├── test_item.py     # Item tests
│   └── test_api_integration.py  # Integration tests
├── requirements-dev.txt  # Development dependencies
└── .env.example         # Environment template
```

## Known Issues

1. **Flask-JWT Compatibility**: Flask-JWT (0.3.2) has installation issues with newer Python versions. Consider migrating to Flask-JWT-Extended.

2. **Error Handling**: Bare except clauses in item.py (lines 44, 80, 85) should be more specific.

3. **Database Connections**: Each operation opens a new connection. Consider using connection pooling or Flask-SQLAlchemy for production.

## Future Improvements

- Migrate to Flask-JWT-Extended for better maintenance
- Add input validation for price (min/max values, negative check)
- Implement connection pooling
- Add rate limiting
- Add API documentation with Swagger/OpenAPI
- Implement proper logging
- Add database migrations with Alembic
