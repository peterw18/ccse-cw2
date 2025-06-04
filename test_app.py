# test_app.py
import pytest
import os
import bcrypt
from unittest.mock import patch, MagicMock
from flask import url_for # Ensure url_for is imported

# Helper function to add a product to the test database
def add_product(db_conn, name, description, price, stock, image):
    cursor = db_conn.cursor()
    cursor.execute("INSERT INTO products(name, description, price, stock, image) VALUES (?, ?, ?, ?, ?);",
                   (name, description, price, stock, image))
    db_conn.commit()
    return cursor.lastrowid

# Helper function to add a user to the test database
def add_user(db_conn, username, password, privilege="user"):
    cursor = db_conn.cursor()
    pswd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(pswd_bytes, salt)
    cursor.execute("INSERT INTO users (username, hash, privilege) VALUES (?, ?, ?);",
                   (username, hashed_password, privilege))
    db_conn.commit()

class TestApp:

    def test_index_page(self, client):
        """Test that the homepage loads successfully."""
        response = client.get('/')
        assert response.status_code == 200
        assert b"<!DOCTYPE html>" in response.data # Check for the DOCTYPE declaration

    def test_get_products_api_empty(self, client):
        """Test the /api/products endpoint when no products exist."""
        response = client.get('/api/products')
        assert response.status_code == 200
        assert response.json == []

    def test_get_products_api_with_data(self, client, db_conn):
        """Test the /api/products endpoint with existing products."""
        add_product(db_conn, "Test Product 1", "Desc 1", 1000, 10, "image1.jpg")
        add_product(db_conn, "Test Product 2", "Desc 2", 2000, 5, "image2.png")

        response = client.get('/api/products')
        assert response.status_code == 200
        products = response.json
        assert len(products) == 2
        assert products[0]['name'] == "Test Product 2" # Products are reversed
        assert products[1]['name'] == "Test Product 1"

    def test_display_product_valid_id(self, client, db_conn):
        """Test displaying a single product with a valid ID."""
        product_id = add_product(db_conn, "Single Product", "Details", 1500, 20, "single.jpg")
        response = client.get(f'/product?id={product_id}')
        assert response.status_code == 200
        assert b"Single Product" in response.data
        assert b"15.00" in response.data # Price formatting

    def test_display_product_invalid_id(self, client):
        """Test displaying a single product with an invalid ID."""
        response = client.get('/product?id=99999')
        assert response.status_code == 302 # Redirects to home page
        assert response.headers['Location'] == '/'

    def test_basket_add_item(self, client, db_conn):
        """Test adding an item to the basket."""
        product_id = add_product(db_conn, "Basket Item", "Desc", 500, 10, "basket.jpg")
        with client.session_transaction() as sess:
            sess["basket"] = {}
        
        response = client.post('/basket', data={'itemid': product_id, 'quantity': 2})
        assert response.status_code == 200
        with client.session_transaction() as sess:
            assert sess["basket"][str(product_id)] == 2

    def test_basket_update_quantity(self, client, db_conn):
        """Test updating an item's quantity in the basket."""
        product_id = add_product(db_conn, "Update Item", "Desc", 500, 10, "update.jpg")
        with client.session_transaction() as sess:
            sess["basket"] = {str(product_id): 2}
        
        response = client.post('/basket', data={'itemid': product_id, 'new_quantity': 5})
        assert response.status_code == 200
        with client.session_transaction() as sess:
            assert sess["basket"][str(product_id)] == 5

    def test_basket_remove_item(self, client, db_conn):
        """Test removing an item from the basket by setting quantity to 0."""
        product_id = add_product(db_conn, "Remove Item", "Desc", 500, 10, "remove.jpg")
        with client.session_transaction() as sess:
            sess["basket"] = {str(product_id): 1}
        
        response = client.post('/basket', data={'itemid': product_id, 'new_quantity': 0})
        assert response.status_code == 200
        with client.session_transaction() as sess:
            assert str(product_id) not in sess["basket"]

    def test_basket_quantity_exceeds_stock(self, client, db_conn):
        """Test adding more items than available in stock."""
        product_id = add_product(db_conn, "Limited Stock", "Desc", 500, 3, "limited.jpg")
        with client.session_transaction() as sess:
            sess["basket"] = {}
        
        response = client.post('/basket', data={'itemid': product_id, 'quantity': 5})
        assert response.status_code == 200
        with client.session_transaction() as sess:
            assert sess["basket"][str(product_id)] == 3 # Should be limited to available stock

    def test_register_successful(self, client, db_conn):
        """Test successful user registration."""
        response = client.post('/register', data={
            'username': 'newuser',
            'password': 'password123',
            'cpassword': 'password123'
        })
        assert response.status_code == 200
        assert b"Account successfully created! Please log in" in response.data

        cursor = db_conn.cursor()
        cursor.execute("SELECT username FROM users WHERE username = 'newuser';")
        user = cursor.fetchone()
        assert user is not None
        assert user[0] == 'newuser'

    def test_register_password_mismatch(self, client):
        """Test registration with mismatched passwords."""
        response = client.post('/register', data={
            'username': 'mismatchuser',
            'password': 'password123',
            'cpassword': 'wrongpassword'
        })
        assert response.status_code == 200
        assert b"Error: passwords do not match" in response.data

    def test_register_duplicate_username(self, client, db_conn):
        """Test registration with an already existing username."""
        add_user(db_conn, "existinguser", "password123")
        response = client.post('/register', data={
            'username': 'existinguser',
            'password': 'newpassword',
            'cpassword': 'newpassword'
        })
        assert response.status_code == 200
        assert b"Error: username already exists" in response.data

    def test_login_successful(self, client, db_conn):
        """Test successful user login."""
        add_user(db_conn, "testuser", "testpassword")
        response = client.post('/login', data={
            'username': 'testuser',
            'password': 'testpassword'
        })
        assert response.status_code == 302 # Redirect to home
        assert response.headers['Location'] == '/'
        with client.session_transaction() as sess:
            assert sess['username'] == 'testuser'
            assert sess['privilege'] == 'user'

    def test_login_incorrect_password(self, client, db_conn):
        """Test login with an incorrect password."""
        add_user(db_conn, "wrongpassuser", "correctpassword")
        response = client.post('/login', data={
            'username': 'wrongpassuser',
            'password': 'incorrectpassword'
        })
        assert response.status_code == 200
        assert b"Error: Incorrect Username or Password" in response.data
        with client.session_transaction() as sess:
            assert 'username' not in sess

    def test_login_nonexistent_user(self, client):
        """Test login with a nonexistent username."""
        response = client.post('/login', data={
            'username': 'nonexistent',
            'password': 'anypassword'
        })
        assert response.status_code == 200
        assert b"Error: incorrect username or password" in response.data # General error message for DB error
        with client.session_transaction() as sess:
            assert 'username' not in sess

    def test_logout(self, client, db_conn):
        """Test user logout functionality."""
        add_user(db_conn, "logoutuser", "password")
        with client.session_transaction() as sess:
            sess['username'] = 'logoutuser'
            sess['privilege'] = 'user'
        
        response = client.get('/logout')
        assert response.status_code == 302 # Redirect to home
        assert response.headers['Location'] == '/'
        with client.session_transaction() as sess:
            assert 'username' not in sess
            assert 'privilege' not in sess

    def test_checkout_unauthenticated(self, client):
        """Test checkout redirect for unauthenticated users."""
        response = client.get('/checkout')
        assert response.status_code == 302
        assert response.headers['Location'] == '/login'

    def test_checkout_get_authenticated_empty_basket(self, client, db_conn):
        """Test GET request to checkout as authenticated user with empty basket."""
        add_user(db_conn, "checkoutuser", "password")
        with client.session_transaction() as sess:
            sess['username'] = 'checkoutuser'
            sess['privilege'] = 'user'
            sess['basket'] = {}

        response = client.get('/checkout')
        assert response.status_code == 200
        assert b"<h2>Checkout</h2>" in response.data
        assert b"0.00" in response.data # Subtotal should be 0.00

    def test_checkout_post_successful(self, client, db_conn):
        """Test successful POST request to checkout."""
        user_id = add_user(db_conn, "checkouttest", "password")
        product_id = add_product(db_conn, "Checkout Product", "Desc", 2500, 10, "checkout.jpg")

        with client.session_transaction() as sess:
            sess['username'] = 'checkouttest'
            sess['privilege'] = 'user'
            sess['basket'] = {str(product_id): 2}

        response = client.post('/checkout', data={
            'addr_l1': '123 Test St',
            'addr_city': 'Testville',
            'addr_postcode': 'T3S T0ST',
            'payment_num': '1234567890123456',
            'payment_exp': '12/25',
            'payment_cvv': '123',
            'save_address': 'on',
            'save_payment': 'on'
        })
        assert response.status_code == 200
        assert b"Order Placed" in response.data # This assertion is crucial for confirming the state

        # Verify order in database
        cursor = db_conn.cursor()
        cursor.execute(f"SELECT userid, address, cost, status FROM orders WHERE userid = {user_id};")
        order = cursor.fetchone()
        assert order is not None
        assert order[0] == user_id
        assert "123 Test St, Testville, T3S T0ST" in order[1]
        assert order[2] == 5000 # 2 items * 2500 cents
        assert order[3] == "ORDERED"

    # Test the add_headers security measures (basic check)
    def test_security_headers(self, client):
        response = client.get('/')
        assert 'Content-Security-Policy' in response.headers
        assert 'X-Content-Type-Options' in response.headers
        assert "default-src 'self'" in response.headers['Content-Security-Policy']
        assert "nosniff" in response.headers['X-Content-Type-Options']