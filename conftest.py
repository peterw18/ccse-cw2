# conftest.py
import pytest
from app import app, get_db_connection as original_app_get_db_connection # Import the Flask app instance and the original function
import sqlite3
from unittest.mock import patch # Import patch for mocking

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['DEBUG'] = False

    # Create a single in-memory connection for this test run
    in_memory_conn = sqlite3.connect(":memory:")

    # Store the original get_db_connection function to restore it later
    # This handles cases where get_db_connection might be accessed as app.get_db_connection
    # even if it's a global function in app.py
    original_get_db_conn_attribute = getattr(app, 'get_db_connection', None)
    app.get_db_connection = lambda: in_memory_conn # Temporarily assign a lambda to app.get_db_connection

    # Patch the global get_db_connection function in the 'app' module.
    # This catches calls like 'get_db_connection()' directly in app.py or 'from app import get_db_connection' imports.
    with patch('app.get_db_connection', return_value=in_memory_conn):
        with app.test_client() as test_client:
            with app.app_context():
                # Set up the database schema in the in-memory database
                cursor = in_memory_conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS products (
                        itemid INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        description TEXT,
                        price INTEGER NOT NULL,
                        stock INTEGER NOT NULL,
                        image TEXT
                    );
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        userid INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL UNIQUE,
                        hash TEXT NOT NULL,
                        privilege TEXT NOT NULL,
                        addr_l1 TEXT,
                        addr_l2 TEXT,
                        addr_l3 TEXT,
                        addr_city TEXT,
                        addr_county TEXT,
                        addr_postcode TEXT,
                        addr_save INTEGER DEFAULT 0,
                        payment_num TEXT,
                        payment_exp TEXT,
                        payment_save INTEGER DEFAULT 0
                    );
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS orders (
                        orderid INTEGER PRIMARY KEY AUTOINCREMENT,
                        userid INTEGER NOT NULL,
                        placed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        address TEXT NOT NULL,
                        cost INTEGER NOT NULL,
                        status TEXT NOT NULL,
                        FOREIGN KEY(userid) REFERENCES users(userid)
                    );
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS orderitems (
                        orderitemid INTEGER PRIMARY KEY AUTOINCREMENT,
                        orderid INTEGER NOT NULL,
                        productid INTEGER NOT NULL,
                        quantity INTEGER NOT NULL,
                        FOREIGN KEY(orderid) REFERENCES orders(orderid),
                        FOREIGN KEY(productid) REFERENCES products(itemid)
                    );
                """)
                in_memory_conn.commit()

                # IMPORTANT: Clear tables for each test to ensure isolation.
                cursor.execute("DELETE FROM products;")
                cursor.execute("DELETE FROM users;")
                cursor.execute("DELETE FROM orders;")
                cursor.execute("DELETE FROM orderitems;")
                in_memory_conn.commit()

            yield test_client # Yield the test client for the test function to use

    # Clean up after tests: restore original app.get_db_connection attribute
    if original_get_db_conn_attribute is not None:
        app.get_db_connection = original_get_db_conn_attribute
    else:
        # If it wasn't originally an attribute, delete the one we added
        if hasattr(app, 'get_db_connection'):
            del app.get_db_connection

    # Close the in-memory connection
    in_memory_conn.close()

@pytest.fixture
def db_conn(client): # Depend on 'client' fixture to ensure it runs first and sets up the mock
    # This will now correctly return the in-memory connection, whether accessed via
    # app.get_db_connection or the patched global function.
    conn = app.get_db_connection()
    yield conn