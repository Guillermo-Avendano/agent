-- ═══════════════════════════════════════════════════════════
-- Sample database schema for the AI SQL Agent
-- This runs automatically on first PostgreSQL start.
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS customers (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(200) NOT NULL,
    email       VARCHAR(255) NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS products (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(200) NOT NULL,
    price       NUMERIC(10,2) NOT NULL CHECK (price >= 0),
    category    VARCHAR(100),
    stock       INTEGER DEFAULT 0 CHECK (stock >= 0)
);

CREATE TABLE IF NOT EXISTS orders (
    id          SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    total       NUMERIC(12,2) NOT NULL DEFAULT 0,
    status      VARCHAR(50) NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending','shipped','delivered','cancelled')),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS order_items (
    id          SERIAL PRIMARY KEY,
    order_id    INTEGER NOT NULL REFERENCES orders(id),
    product_id  INTEGER NOT NULL REFERENCES products(id),
    quantity    INTEGER NOT NULL CHECK (quantity > 0),
    unit_price  NUMERIC(10,2) NOT NULL CHECK (unit_price >= 0)
);

-- ─── Sample Data ────────────────────────────────────────────
INSERT INTO customers (name, email) VALUES
    ('Alice Johnson', 'alice@example.com'),
    ('John Smith', 'john@example.com'),
    ('Carmen García', 'carmen@example.com'),
    ('David Lee', 'david@example.com'),
    ('Elena Petrova', 'elena@example.com');

INSERT INTO products (name, price, category, stock) VALUES
    ('Laptop Pro 15', 1299.99, 'Electronics', 50),
    ('Wireless Mouse', 29.99, 'Electronics', 200),
    ('Standing Desk', 499.00, 'Furniture', 30),
    ('Mechanical Keyboard', 149.99, 'Electronics', 100),
    ('Monitor 27"', 349.99, 'Electronics', 75),
    ('Desk Lamp', 45.00, 'Furniture', 150),
    ('USB-C Hub', 59.99, 'Electronics', 120),
    ('Ergonomic Chair', 699.00, 'Furniture', 25);

INSERT INTO orders (customer_id, total, status, created_at) VALUES
    (1, 1329.98, 'delivered',  NOW() - INTERVAL '30 days'),
    (2, 499.00,  'shipped',    NOW() - INTERVAL '15 days'),
    (3, 209.98,  'delivered',  NOW() - INTERVAL '20 days'),
    (1, 349.99,  'pending',    NOW() - INTERVAL '2 days'),
    (4, 1498.98, 'delivered',  NOW() - INTERVAL '25 days'),
    (5, 59.99,   'cancelled',  NOW() - INTERVAL '10 days'),
    (3, 849.00,  'shipped',    NOW() - INTERVAL '5 days'),
    (2, 179.98,  'pending',    NOW() - INTERVAL '1 day');

INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
    (1, 1, 1, 1299.99),
    (1, 2, 1, 29.99),
    (2, 3, 1, 499.00),
    (3, 4, 1, 149.99),
    (3, 7, 1, 59.99),
    (4, 5, 1, 349.99),
    (5, 1, 1, 1299.99),
    (5, 6, 1, 45.00),
    (5, 4, 1, 149.99),
    (6, 7, 1, 59.99),
    (7, 8, 1, 699.00),
    (7, 4, 1, 149.99),
    (8, 2, 2, 29.99),
    (8, 4, 1, 149.99);
