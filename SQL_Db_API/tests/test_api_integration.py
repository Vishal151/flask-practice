"""
Integration tests for the complete API workflow.
Tests end-to-end scenarios involving multiple endpoints.
"""
import sys
import os
import pytest

# Add code directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../code'))


@pytest.mark.requires_auth
class TestCompleteUserWorkflow:
    """Test complete user registration and authentication workflow."""

    def test_user_registration_and_login_flow(self, client):
        """Test the complete flow: register -> login -> use token."""
        # Step 1: Register a new user
        register_response = client.post('/register', json={
            'username': 'integrationuser',
            'password': 'integrationpass123'
        })
        assert register_response.status_code == 201

        # Step 2: Login to get JWT token
        auth_response = client.post('/auth', json={
            'username': 'integrationuser',
            'password': 'integrationpass123'
        })
        assert auth_response.status_code == 200
        assert 'access_token' in auth_response.json
        token = auth_response.json['access_token']

        # Step 3: Create an item (no auth required for POST)
        create_response = client.post('/item/testitem', json={
            'price': 99.99
        })
        assert create_response.status_code == 201

        # Step 4: Use token to access protected GET endpoint
        get_response = client.get('/item/testitem', headers={
            'Authorization': f'JWT {token}'
        })
        assert get_response.status_code == 200
        assert get_response.json['item']['price'] == 99.99


@pytest.mark.requires_auth
class TestCompleteItemWorkflow:
    """Test complete item CRUD workflow."""

    def test_item_crud_lifecycle(self, client):
        """Test creating, reading, updating, and deleting an item."""
        # Create
        create_response = client.post('/item/lifecycle', json={'price': 10.00})
        assert create_response.status_code == 201
        assert create_response.json['price'] == 10.00

        # Read (requires auth)
        client.post('/register', json={'username': 'reader', 'password': 'pass'})
        auth_response = client.post('/auth', json={'username': 'reader', 'password': 'pass'})
        token = auth_response.json['access_token']

        read_response = client.get('/item/lifecycle', headers={
            'Authorization': f'JWT {token}'
        })
        assert read_response.status_code == 200
        assert read_response.json['item']['price'] == 10.00

        # Update
        update_response = client.put('/item/lifecycle', json={'price': 20.00})
        assert update_response.status_code == 200
        assert update_response.json['price'] == 20.00

        # Verify update
        verify_response = client.get('/item/lifecycle', headers={
            'Authorization': f'JWT {token}'
        })
        assert verify_response.json['item']['price'] == 20.00

        # Delete
        delete_response = client.delete('/item/lifecycle')
        assert delete_response.status_code == 200

        # Verify deletion
        final_response = client.get('/item/lifecycle', headers={
            'Authorization': f'JWT {token}'
        })
        assert final_response.status_code == 404


@pytest.mark.requires_auth
class TestMultipleUsers:
    """Test scenarios with multiple users."""

    def test_multiple_users_can_register(self, client):
        """Test that multiple users can register independently."""
        # Register user 1
        response1 = client.post('/register', json={
            'username': 'user1',
            'password': 'pass1'
        })
        assert response1.status_code == 201

        # Register user 2
        response2 = client.post('/register', json={
            'username': 'user2',
            'password': 'pass2'
        })
        assert response2.status_code == 201

        # Both can authenticate independently
        auth1 = client.post('/auth', json={'username': 'user1', 'password': 'pass1'})
        assert auth1.status_code == 200

        auth2 = client.post('/auth', json={'username': 'user2', 'password': 'pass2'})
        assert auth2.status_code == 200

        # Tokens should be different
        assert auth1.json['access_token'] != auth2.json['access_token']

    def test_users_cannot_use_each_others_passwords(self, client):
        """Test that users can't authenticate with other users' passwords."""
        # Register two users
        client.post('/register', json={'username': 'alice', 'password': 'alicepass'})
        client.post('/register', json={'username': 'bob', 'password': 'bobpass'})

        # Alice can't use Bob's password
        response = client.post('/auth', json={'username': 'alice', 'password': 'bobpass'})
        assert response.status_code == 401

        # Bob can't use Alice's password
        response = client.post('/auth', json={'username': 'bob', 'password': 'alicepass'})
        assert response.status_code == 401


@pytest.mark.requires_auth
class TestMultipleItems:
    """Test scenarios with multiple items."""

    def test_multiple_items_in_list(self, client):
        """Test creating and listing multiple items."""
        # Create multiple items
        items_to_create = [
            ('apple', 1.50),
            ('banana', 0.75),
            ('orange', 1.25),
            ('grape', 3.00)
        ]

        for name, price in items_to_create:
            response = client.post(f'/item/{name}', json={'price': price})
            assert response.status_code == 201

        # Get all items
        list_response = client.get('/items')
        assert list_response.status_code == 200

        items = list_response.json['items']
        assert len(items) == 4

        # Verify all items are present
        item_dict = {item['name']: item['price'] for item in items}
        for name, price in items_to_create:
            assert name in item_dict
            assert item_dict[name] == price


@pytest.mark.requires_auth
class TestAuthenticationBoundaries:
    """Test authentication edge cases."""

    def test_expired_or_invalid_token(self, client):
        """Test using an invalid JWT token."""
        # Create an item
        client.post('/item/protected', json={'price': 100.00})

        # Try to access with invalid token
        response = client.get('/item/protected', headers={
            'Authorization': 'JWT invalidtoken123'
        })

        assert response.status_code == 401

    def test_missing_authorization_header(self, client):
        """Test accessing protected endpoint without Authorization header."""
        client.post('/item/protected', json={'price': 100.00})

        response = client.get('/item/protected')
        assert response.status_code == 401

    def test_malformed_authorization_header(self, client):
        """Test with malformed Authorization header."""
        client.post('/item/protected', json={'price': 100.00})

        # Missing 'JWT' prefix
        response = client.get('/item/protected', headers={
            'Authorization': 'Bearer sometoken'
        })
        assert response.status_code == 401


@pytest.mark.requires_auth
class TestDataPersistence:
    """Test data persistence across operations."""

    def test_item_persists_after_creation(self, client):
        """Test that items persist across multiple requests."""
        # Create item
        client.post('/item/persistent', json={'price': 50.00})

        # Get auth token
        client.post('/register', json={'username': 'checker', 'password': 'pass'})
        auth_response = client.post('/auth', json={'username': 'checker', 'password': 'pass'})
        token = auth_response.json['access_token']

        # Check it exists multiple times
        for _ in range(3):
            response = client.get('/item/persistent', headers={
                'Authorization': f'JWT {token}'
            })
            assert response.status_code == 200
            assert response.json['item']['price'] == 50.00

    def test_user_persists_after_registration(self, client):
        """Test that users persist and can login multiple times."""
        # Register once
        client.post('/register', json={'username': 'persistent', 'password': 'mypass'})

        # Login multiple times
        for _ in range(3):
            response = client.post('/auth', json={
                'username': 'persistent',
                'password': 'mypass'
            })
            assert response.status_code == 200
            assert 'access_token' in response.json


@pytest.mark.requires_auth
class TestConcurrentOperations:
    """Test concurrent-like operations."""

    def test_multiple_operations_on_same_item(self, client):
        """Test multiple operations on the same item."""
        # Create
        client.post('/item/multi', json={'price': 10.00})

        # Update multiple times
        client.put('/item/multi', json={'price': 20.00})
        client.put('/item/multi', json={'price': 30.00})
        client.put('/item/multi', json={'price': 40.00})

        # Verify final state
        client.post('/register', json={'username': 'verifier', 'password': 'pass'})
        auth_response = client.post('/auth', json={'username': 'verifier', 'password': 'pass'})
        token = auth_response.json['access_token']

        response = client.get('/item/multi', headers={
            'Authorization': f'JWT {token}'
        })
        assert response.json['item']['price'] == 40.00


@pytest.mark.requires_auth
class TestCompleteScenario:
    """Test a complete realistic scenario."""

    def test_complete_store_scenario(self, client):
        """Test a complete e-commerce-like scenario."""
        # Store owner registers
        register_response = client.post('/register', json={
            'username': 'storeowner',
            'password': 'securepass123'
        })
        assert register_response.status_code == 201

        # Store owner logs in
        auth_response = client.post('/auth', json={
            'username': 'storeowner',
            'password': 'securepass123'
        })
        assert auth_response.status_code == 200
        token = auth_response.json['access_token']

        # Add products to store
        products = [
            ('laptop', 999.99),
            ('mouse', 29.99),
            ('keyboard', 79.99),
            ('monitor', 299.99)
        ]

        for name, price in products:
            response = client.post(f'/item/{name}', json={'price': price})
            assert response.status_code == 201

        # Verify all products are in the store
        list_response = client.get('/items')
        assert len(list_response.json['items']) == 4

        # Update a product price
        update_response = client.put('/item/laptop', json={'price': 899.99})
        assert update_response.status_code == 200

        # Verify the update
        check_response = client.get('/item/laptop', headers={
            'Authorization': f'JWT {token}'
        })
        assert check_response.json['item']['price'] == 899.99

        # Remove a product
        delete_response = client.delete('/item/mouse')
        assert delete_response.status_code == 200

        # Verify it's gone
        final_list = client.get('/items')
        assert len(final_list.json['items']) == 3
        item_names = [item['name'] for item in final_list.json['items']]
        assert 'mouse' not in item_names
