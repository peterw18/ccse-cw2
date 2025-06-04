# conftest.py
import pytest
from app import app
import sqlite3
from unittest.mock import patch

# Define a global in-memory database name for consistent access across multiple connections.
# This allows multiple connections to the same in-memory database within a single test,
# simulating real-world database usage where multiple connections might be active
# but all interact with the same underlying data.
IN_MEMORY_DB_NAME = ":memory:test_db"

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['DEBUG'] = False

    # This will establish an initial connection for setting up the database schema.
    # It's crucial to keep this connection open while schema setup and initial data loading occur.
    initial_conn = sqlite3.connect(IN_MEMORY_DB_NAME, check_same_thread=False)

    # Define the mock function that will be used to replace app.get_db_connection.
    # This function will return a NEW connection object to the SAME named in-memory database
    # every time it is called. This prevents 'Cannot operate on a closed database' errors
    # if app.py closes connections after use, as each call gets a unique connection object.
    def mock_get_db_connection():
        return sqlite3.connect(IN_MEMORY_DB_NAME, check_same_thread=False)

    # IMPORTANT: Monkey-patch the Flask app instance's 'get_db_connection' attribute first.
    # This handles cases where the code under test might be looking for `app.get_db_connection`
    # as an attribute, which was reported in previous errors.
    original_get_db_conn_attribute = getattr(app, 'get_db_connection', None)
    app.get_db_connection = mock_get_db_connection

    # Patch the global 'get_db_connection' function within the 'app' module.
    # This handles calls to `get_db_connection()` directly in `app.py` or
    # if other modules import it as `from app import get_db_connection`.
    # Using `side_effect` tells the mock to call `mock_get_db_connection`
    # each time the patched function is invoked.
    with patch('app.get_db_connection', side_effect=mock_get_db_connection):
        with app.test_client() as test_client:
            with app.app_context():
                # Use the 'initial_conn' to execute schema creation.
                # This ensures the schema is set up on the in-memory database.
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
                # Open a separate connection for clearing to mimic app behavior and avoid closing 'initial_conn'.
                clean_conn = sqlite3.connect(IN_MEMORY_DB_NAME, check_same_thread=False)
                clean_cursor = clean_conn.cursor()
                clean_cursor.execute("DELETE FROM products;")
                clean_cursor.execute("DELETE FROM users;")
                clean_cursor.execute("DELETE FROM orders;")
                clean_cursor.execute("DELETE FROM orderitems;")
                clean_conn.commit()
                clean_conn.close() # Close the connection used for cleaning

            yield test_client # Yield the test client for the test function to use

    # Clean up after all tests using this fixture: restore original app.get_db_connection
    if original_get_db_conn_attribute is not None:
        app.get_db_connection = original_get_db_conn_attribute
    else:
        # If 'get_db_connection' was not originally an attribute, remove the one we added.
        if hasattr(app, 'get_db_connection'):
            del app.get_db_connection

    # Close the initial connection that was used for schema setup.
    initial_conn.close()

@pytest.fixture
def db_conn(client): # This fixture depends on 'client' to ensure the patching is active.
    # This will call the patched `get_db_connection`, returning a new connection
    # to the persistent in-memory database for use within a test function.
    conn = app.get_db_connection()
    yield conn
    conn.close() # Ensure this connection opened by the fixture is also closed after the test.