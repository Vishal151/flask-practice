"""
Unit tests for Item model and endpoints.
"""
import sys
import os
import sqlite3
import tempfile
import pytest

# Add code directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../code'))

from item import Item, ItemList


class TestItemModel:
    """Test Item model database operations."""

    def setup_method(self):
        """Create a temporary database for each test."""
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.connection = sqlite3.connect(self.db_path)
        self.cursor = self.connection.cursor()

        # Create items table
        self.cursor.execute(
            "CREATE TABLE items (name text PRIMARY KEY, price real)"
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

    def test_find_by_name_existing_item(self):
        """Test finding an item that exists."""
        self.cursor.execute(
            "INSERT INTO items VALUES ('test_item', 19.99)"
        )
        self.connection.commit()

        result = Item.find_by_name('test_item')

        assert result is not None
        assert result['item']['name'] == 'test_item'
        assert result['item']['price'] == 19.99

    def test_find_by_name_nonexistent_item(self):
        """Test finding an item that doesn't exist."""
        result = Item.find_by_name('nonexistent')
        assert result is None

    def test_insert_new_item(self):
        """Test inserting a new item."""
        item = {'name': 'new_item', 'price': 25.50}
        Item.insert(item)

        # Verify it was inserted
        self.cursor.execute("SELECT * FROM items WHERE name='new_item'")
        row = self.cursor.fetchone()

        assert row is not None
        assert row[0] == 'new_item'
        assert row[1] == 25.50

    def test_update_existing_item(self):
        """Test updating an existing item."""
        # Insert initial item
        self.cursor.execute("INSERT INTO items VALUES ('update_item', 10.00)")
        self.connection.commit()

        # Update it
        updated_item = {'name': 'update_item', 'price': 15.00}
        Item.update(updated_item)

        # Verify update
        self.cursor.execute("SELECT price FROM items WHERE name='update_item'")
        price = self.cursor.fetchone()[0]

        assert price == 15.00


class TestItemEndpoints:
    """Test Item resource endpoints."""

    def get_auth_token(self, client):
        """Helper to get authentication token."""
        # Register and authenticate
        client.post('/register', json={'username': 'testuser', 'password': 'testpass'})
        response = client.post('/auth', json={'username': 'testuser', 'password': 'testpass'})
        return response.json['access_token']

    def test_post_create_item_success(self, client):
        """Test creating a new item."""
        response = client.post('/item/chair', json={'price': 49.99})

        assert response.status_code == 201
        assert response.json['name'] == 'chair'
        assert response.json['price'] == 49.99

    def test_post_duplicate_item(self, client):
        """Test creating an item that already exists."""
        # Create first item
        client.post('/item/duplicate', json={'price': 10.00})

        # Try to create duplicate
        response = client.post('/item/duplicate', json={'price': 20.00})

        assert response.status_code == 400
        assert 'already exists' in response.json['message']

    def test_post_missing_price(self, client):
        """Test creating item without required price field."""
        response = client.post('/item/noPrice', json={})

        assert response.status_code == 400
        assert 'price' in str(response.json).lower()

    def test_post_invalid_price_type(self, client):
        """Test creating item with invalid price type."""
        response = client.post('/item/badprice', json={'price': 'not a number'})

        assert response.status_code == 400

    @pytest.mark.requires_auth
    def test_get_existing_item_with_auth(self, client):
        """Test getting an existing item with JWT token."""
        token = self.get_auth_token(client)

        # Create item
        client.post('/item/laptop', json={'price': 999.99})

        # Get item with auth
        response = client.get('/item/laptop', headers={
            'Authorization': f'JWT {token}'
        })

        assert response.status_code == 200
        assert response.json['item']['name'] == 'laptop'
        assert response.json['item']['price'] == 999.99

    @pytest.mark.requires_auth
    def test_get_item_without_auth(self, client):
        """Test getting an item without JWT token (should fail)."""
        # Create item
        client.post('/item/phone', json={'price': 599.99})

        # Try to get without auth
        response = client.get('/item/phone')

        assert response.status_code == 401

    @pytest.mark.requires_auth
    def test_get_nonexistent_item(self, client):
        """Test getting an item that doesn't exist."""
        token = self.get_auth_token(client)

        response = client.get('/item/nonexistent', headers={
            'Authorization': f'JWT {token}'
        })

        assert response.status_code == 404
        assert 'not found' in response.json['message'].lower()

    def test_delete_item(self, client):
        """Test deleting an item."""
        # Create item
        client.post('/item/deleteme', json={'price': 5.00})

        # Delete it
        response = client.delete('/item/deleteme')

        assert response.status_code == 200
        assert 'deleted' in response.json['message'].lower()

    def test_delete_nonexistent_item(self, client):
        """Test deleting an item that doesn't exist (should still succeed)."""
        response = client.delete('/item/nonexistent')

        # DELETE is idempotent - should succeed even if item doesn't exist
        assert response.status_code == 200

    def test_put_create_new_item(self, client):
        """Test PUT to create a new item (upsert)."""
        response = client.put('/item/newitem', json={'price': 12.34})

        assert response.status_code == 200
        assert response.json['name'] == 'newitem'
        assert response.json['price'] == 12.34

    @pytest.mark.requires_auth
    def test_put_update_existing_item(self, client):
        """Test PUT to update an existing item."""
        # Create item
        client.post('/item/updateme', json={'price': 10.00})

        # Update it with PUT
        response = client.put('/item/updateme', json={'price': 15.00})

        assert response.status_code == 200
        assert response.json['price'] == 15.00

        # Verify with GET
        token = self.get_auth_token(client)
        get_response = client.get('/item/updateme', headers={
            'Authorization': f'JWT {token}'
        })
        assert get_response.json['item']['price'] == 15.00

    def test_put_missing_price(self, client):
        """Test PUT without required price field."""
        response = client.put('/item/noPrice', json={})

        assert response.status_code == 400


class TestItemList:
    """Test ItemList endpoint."""

    def test_get_empty_list(self, client):
        """Test getting items when none exist."""
        response = client.get('/items')

        assert response.status_code == 200
        assert response.json['items'] == []

    def test_get_items_list(self, client):
        """Test getting list of items."""
        # Create some items
        client.post('/item/item1', json={'price': 10.00})
        client.post('/item/item2', json={'price': 20.00})
        client.post('/item/item3', json={'price': 30.00})

        # Get list
        response = client.get('/items')

        assert response.status_code == 200
        assert len(response.json['items']) == 3

        # Verify items are in response
        items = response.json['items']
        names = [item['name'] for item in items]
        assert 'item1' in names
        assert 'item2' in names
        assert 'item3' in names

    def test_get_items_no_auth_required(self, client):
        """Test that /items endpoint doesn't require authentication."""
        # Should work without auth token
        response = client.get('/items')

        assert response.status_code == 200


class TestItemErrorHandling:
    """Test error handling in Item endpoints."""

    def test_post_handles_database_errors_gracefully(self, client):
        """Test that database errors are handled gracefully."""
        # This test would need to mock a database failure
        # For now, we document that error handling exists at item.py:44
        pass

    def test_price_validation(self, client):
        """Test price field validation."""
        # Test negative price (should be accepted by current implementation)
        response = client.post('/item/negative', json={'price': -10.00})
        # Document current behavior - no validation for negative prices
        assert response.status_code == 201

        # Test zero price
        response = client.post('/item/zero', json={'price': 0.0})
        assert response.status_code == 201

        # Test very large price
        response = client.post('/item/expensive', json={'price': 999999.99})
        assert response.status_code == 201

    def test_special_characters_in_name(self, client):
        """Test item names with special characters."""
        # Test with spaces
        response = client.post('/item/item with spaces', json={'price': 10.00})
        assert response.status_code == 201

        # Test with special characters
        response = client.post('/item/item-with-dash', json={'price': 10.00})
        assert response.status_code == 201
