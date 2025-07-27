-- Database initialization script for Booking and Ecommerce application
-- This script sets up the initial database schema

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create tables for appointments
CREATE TABLE IF NOT EXISTS appointments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_name VARCHAR(255) NOT NULL,
    customer_email VARCHAR(255) NOT NULL,
    service_type VARCHAR(100) NOT NULL,
    appointment_date DATE NOT NULL,
    appointment_time TIME NOT NULL,
    duration_minutes INTEGER DEFAULT 60,
    notes TEXT,
    status VARCHAR(50) DEFAULT 'confirmed',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    user_id UUID NULL  -- For future multi-user support
);

-- Create tables for products
CREATE TABLE IF NOT EXISTS products (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    category VARCHAR(100),
    availability VARCHAR(50) DEFAULT 'in_stock',
    stock_quantity INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create tables for orders
CREATE TABLE IF NOT EXISTS orders (
    id VARCHAR(50) PRIMARY KEY,
    customer_name VARCHAR(255) NOT NULL,
    customer_email VARCHAR(255) NOT NULL,
    shipping_address TEXT,
    total_amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(50) DEFAULT 'confirmed',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    estimated_delivery TIMESTAMP WITH TIME ZONE,
    user_id UUID NULL  -- For future multi-user support
);

-- Create tables for order items
CREATE TABLE IF NOT EXISTS order_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id VARCHAR(50) NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id VARCHAR(50) NOT NULL REFERENCES products(id),
    product_name VARCHAR(255) NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    total_price DECIMAL(10,2) NOT NULL
);

-- Create tables for users (for future use)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments(appointment_date);
CREATE INDEX IF NOT EXISTS idx_appointments_customer_email ON appointments(customer_email);
CREATE INDEX IF NOT EXISTS idx_appointments_service_type ON appointments(service_type);
CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments(status);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_price ON products(price);
CREATE INDEX IF NOT EXISTS idx_orders_customer_email ON orders(customer_email);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items(product_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Create trigger function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at columns
DROP TRIGGER IF EXISTS update_appointments_updated_at ON appointments;
CREATE TRIGGER update_appointments_updated_at
    BEFORE UPDATE ON appointments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_products_updated_at ON products;
CREATE TRIGGER update_products_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert some sample data (optional)
INSERT INTO products (id, name, description, price, category, availability, stock_quantity) VALUES
    ('prod_001', 'Premium Consultation', '60-minute premium consultation session with expert advisor', 150.00, 'consultation', 'in_stock', 100),
    ('prod_002', 'Basic Health Checkup', '30-minute basic health assessment and wellness consultation', 75.00, 'health', 'in_stock', 50),
    ('prod_003', 'Therapy Session', '45-minute professional therapy session', 120.00, 'therapy', 'in_stock', 25),
    ('prod_004', 'Wellness Package', 'Complete wellness package including consultation and follow-up', 299.00, 'package', 'in_stock', 20),
    ('prod_005', 'Group Workshop', '90-minute group workshop on mindfulness and stress management', 45.00, 'workshop', 'in_stock', 15)
ON CONFLICT DO NOTHING;

INSERT INTO appointments (customer_name, customer_email, service_type, appointment_date, appointment_time, duration_minutes, notes, status) VALUES
    ('John Smith', 'john.smith@example.com', 'Premium Consultation', '2025-01-15', '10:00', 60, 'First-time consultation', 'confirmed'),
    ('Sarah Johnson', 'sarah.j@example.com', 'Therapy Session', '2025-01-16', '14:30', 45, 'Follow-up session', 'confirmed'),
    ('Mike Brown', 'mike.brown@example.com', 'Basic Health Checkup', '2025-01-17', '09:00', 30, 'Annual checkup', 'confirmed')
ON CONFLICT DO NOTHING;

INSERT INTO orders (id, customer_name, customer_email, shipping_address, total_amount, status, estimated_delivery) VALUES
    ('ord_20250115_001', 'Alice Wilson', 'alice.wilson@example.com', '123 Main St, Anytown, USA', 150.00, 'confirmed', '2025-01-22'),
    ('ord_20250115_002', 'Bob Davis', 'bob.davis@example.com', '456 Oak Ave, Other City, USA', 299.00, 'processing', '2025-01-20')
ON CONFLICT DO NOTHING;

INSERT INTO order_items (order_id, product_id, product_name, quantity, unit_price, total_price) VALUES
    ('ord_20250115_001', 'prod_001', 'Premium Consultation', 1, 150.00, 150.00),
    ('ord_20250115_002', 'prod_004', 'Wellness Package', 1, 299.00, 299.00)
ON CONFLICT DO NOTHING;

-- Grant permissions to the booking user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO diary_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO diary_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO diary_user; 