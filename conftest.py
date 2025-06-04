# conftest.py
import pytest
from app import app # Import the Flask app instance
import sqlite3
from unittest.mock import patch # Import patch for mocking

# This fixture will provide the Flask test client and ensure the in-memory DB setup
@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['DEBUG'] = False

    # Create an in-memory connection *once* for this test run for the client
    # This connection will be the shared one for all database operations during the test.
    in_memory_conn = sqlite3.connect(":memory:")

    # Patch get_db_connection in the 'app' module to return this specific in-memory connection
    # This ensures any calls to get_db_connection throughout your app code during tests
    # will use this in-memory database.
    with patch('app.get_db_connection', return_value=in_memory_conn):
        with app.test_client() as test_client:
            with app.app_context():
                # Set up the database schema in the in-memory database
                # This ensures tables exist for tests before any operations
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
                # The 'client' fixture is typically run once per test function that uses it.
                cursor.execute("DELETE FROM products;")
                cursor.execute("DELETE FROM users;")
                cursor.execute("DELETE FROM orders;")
                cursor.execute("DELETE FROM orderitems;")
                in_memory_conn.commit()

            yield test_client # Yield the test client for the test function to use

    # This block runs after the test function finishes (teardown)
    # Ensure the in-memory connection is closed when the fixture scope ends
    in_memory_conn.close()

# This fixture provides a direct connection to the test database for test data setup.
# It now implicitly uses the *same* mocked in-memory connection that 'client' sets up.
@pytest.fixture
def db_conn(client): # Depend on 'client' fixture to ensure it runs first and sets up the mock
    # Because 'app.get_db_connection' is patched, calling it here will return
    # the same in_memory_conn that 'client' set up.
    # No need to store in app.config as patch handles it.
    conn = app.get_db_connection()
    yield conn
    # The connection is managed and closed by the 'client' fixture, so no explicit close here.