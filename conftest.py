# conftest.py
import pytest
from app import app, get_db_connection
import sqlite3
import os

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False # Disable CSRF for testing forms
    app.config['DEBUG'] = False # Disable debug mode

    # Use an in-memory database for testing
    app.config['DATABASE'] = ':memory:'
    
    with app.test_client() as client:
        with app.app_context():
            # Create tables for testing
            conn = get_db_connection()
            cursor = conn.cursor()
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
            conn.commit()
            conn.close()
        yield client

@pytest.fixture
def db_conn():
    # This fixture provides a direct connection to the test database
    # for inserting test data directly.
    conn = sqlite3.connect(":memory:")
    yield conn
    conn.close()