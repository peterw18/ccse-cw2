# conftest.py
import pytest
from app import app
import sqlite3
from unittest.mock import patch
import os
import tempfile # Import tempfile for temporary file creation

# Define a global variable to store the path to the temporary test database file.
# This will be set dynamically by the 'client' fixture.
TEST_DB_PATH = None

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['DEBUG'] = False

    global TEST_DB_PATH
    # Create a temporary file for the database.
    # tempfile.mkstemp returns a tuple: (file descriptor, path).
    fd, path = tempfile.mkstemp(suffix=".db", prefix="test_db_")
    os.close(fd) # Close the file descriptor immediately
    TEST_DB_PATH = path # Store the generated path globally

    # Define the mock function that will replace app.get_db_connection.
    # This function will now connect to the physical test database file.
    def mock_get_db_connection():
        return sqlite3.connect(TEST_DB_PATH, check_same_thread=False)

    # IMPORTANT: Monkey-patch the Flask app instance's 'get_db_connection' attribute first.
    original_get_db_conn_attribute = getattr(app, 'get_db_connection', None)
    app.get_db_connection = mock_get_db_connection

    # Patch the global 'get_db_connection' function within the 'app' module.
    with patch('app.get_db_connection', side_effect=mock_get_db_connection):
        # Establish an initial connection for setting up the database schema.
        # This connection is used specifically for the fixture setup.
        initial_conn = sqlite3.connect(TEST_DB_PATH, check_same_thread=False)
        with app.test_client() as test_client:
            with app.app_context():
                # Setup schema using the initial connection
                cursor = initial_conn.cursor()
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
                initial_conn.commit()

                # Clear tables before each test to ensure test isolation.
                # We open a separate connection for clearing, just like the app would,
                # to ensure all operations go through the patched get_db_connection.
                clean_conn = sqlite3.connect(TEST_DB_PATH, check_same_thread=False)
                clean_cursor = clean_conn.cursor()
                clean_cursor.execute("DELETE FROM products;")
                clean_cursor.execute("DELETE FROM users;")
                clean_cursor.execute("DELETE FROM orders;")
                clean_cursor.execute("DELETE FROM orderitems;")
                clean_conn.commit()
                clean_conn.close() # Close the connection used for cleaning

            yield test_client # Yield the test client for the test function to use

    # Clean up after all tests using this fixture:
    # 1. Restore the original app.get_db_connection if it was set.
    if original_get_db_conn_attribute is not None:
        app.get_db_connection = original_get_db_conn_attribute
    else:
        # If 'get_db_connection' was not originally an attribute, remove the one we added.
        if hasattr(app, 'get_db_connection'):
            del app.get_db_connection
    
    # 2. Close the initial connection to the test database.
    initial_conn.close()

    # 3. Delete the temporary database file.
    # This ensures that no residual test database files are left behind.
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


@pytest.fixture
def db_conn(client): # This fixture depends on 'client' to ensure the patching is active.
    # This will call the patched `get_db_connection`, returning a new connection
    # to the persistent test database file for use within a test function.
    conn = app.get_db_connection()
    yield conn
    conn.close() # Ensure this connection opened by the fixture is also closed after the test.