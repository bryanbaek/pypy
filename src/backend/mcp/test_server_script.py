#!/usr/bin/env python3
"""
Test script for the Business MCP server functionality.
This script demonstrates how to use the business MCP server tools.
"""

import asyncio
import json
import sys
from pathlib import Path
import shutil

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import the FastMCP functions directly
from src.backend.mcp.business_server import (
    create_product,
    list_products,
    create_order,
    list_orders,
    update_order_status,
    create_appointment,
    list_appointments,
    get_business_stats,
)

# Set up test data directory
TEST_DATA_DIR = Path("test_data")


def setup_test_environment():
    """Set up test environment with separate data directory"""
    global DATA_DIR
    # Temporarily override DATA_DIR for testing
    from src.backend.mcp import server

    server.DATA_DIR = TEST_DATA_DIR
    TEST_DATA_DIR.mkdir(exist_ok=True)
    (TEST_DATA_DIR / "products").mkdir(exist_ok=True)
    (TEST_DATA_DIR / "orders").mkdir(exist_ok=True)
    (TEST_DATA_DIR / "appointments").mkdir(exist_ok=True)

    # Create some sample products for testing
    sample_products = [
        {
            "id": "prod-001",
            "name": "Basic Consultation Package",
            "price": 150.00,
            "category": "consultation",
            "stock_quantity": 10,
            "description": "60-minute consultation with health assessment",
            "specifications": {},
            "created_at": "2024-01-01T09:00:00",
            "updated_at": "2024-01-01T09:00:00",
        },
        {
            "id": "prod-002",
            "name": "Premium Health Checkup",
            "price": 300.00,
            "category": "health",
            "stock_quantity": 5,
            "description": "Comprehensive health checkup with lab tests",
            "specifications": {},
            "created_at": "2024-01-01T09:00:00",
            "updated_at": "2024-01-01T09:00:00",
        },
        {
            "id": "prod-003",
            "name": "Therapy Session Package",
            "price": 500.00,
            "category": "therapy",
            "stock_quantity": 3,
            "description": "5-session therapy package with certified therapist",
            "specifications": {},
            "created_at": "2024-01-01T09:00:00",
            "updated_at": "2024-01-01T09:00:00",
        },
    ]

    for product in sample_products:
        product_file = TEST_DATA_DIR / "products" / f"{product['id']}.json"
        with open(product_file, "w", encoding="utf-8") as f:
            json.dump(product, f, indent=2, ensure_ascii=False)


async def test_product_operations():
    """Test product management operations."""
    print("=" * 50)
    print("Testing Product Operations")
    print("=" * 50)

    # Test creating a new product
    print("\n1. Creating a new product...")

    create_result = create_product(
        name="Wellness Kit Pro",
        price=89.99,
        category="wellness",
        stock_quantity=20,
        description="Premium wellness kit with supplements and guides",
        specifications={"weight": "2 lbs", "dimensions": "12x8x4 inches"},
    )
    print(f"✓ {create_result}")

    # Test listing all products
    print("\n2. Listing all products...")

    products_list = list_products()
    print(f"✓ {products_list}")

    # Test filtering products by category
    print("\n3. Filtering products by category (health)...")

    health_products = list_products(category="health")
    print(f"✓ {health_products}")

    # Test filtering products by price range
    print("\n4. Filtering products by price range ($100-$200)...")

    price_filtered = list_products(min_price=100.0, max_price=200.0)
    print(f"✓ {price_filtered}")

    # Test filtering for in-stock only
    print("\n5. Filtering for in-stock products only...")

    in_stock = list_products(in_stock_only=True)
    print(f"✓ {in_stock}")


async def test_order_operations():
    """Test order creation and management."""
    print("\n" + "=" * 50)
    print("Testing Order Operations")
    print("=" * 50)

    # Test creating an order
    print("\n1. Creating a new order...")

    order_items = [
        {"product_id": "prod-001", "quantity": 2},
        {"product_id": "prod-002", "quantity": 1},
    ]

    create_result = create_order(
        customer_name="Alice Johnson",
        customer_email="alice.johnson@example.com",
        items=order_items,
        shipping_address="123 Main St, Anytown, AT 12345",
        notes="Please deliver after 5 PM",
    )
    print(f"✓ {create_result}")

    # Extract order ID for further testing
    if "Order created successfully" in create_result:
        # Extract order ID from the response
        order_id_start = create_result.find("ID: ") + 4
        order_id_end = create_result.find(".", order_id_start)
        order_id = create_result[order_id_start:order_id_end]

        # Test updating order status
        print(f"\n2. Updating order status for {order_id}...")

        update_result = update_order_status(
            order_id=order_id,
            status="confirmed",
            notes="Order confirmed and ready for processing",
        )
        print(f"✓ {update_result}")

    # Test listing all orders
    print("\n3. Listing all orders...")

    orders_list = list_orders()
    print(f"✓ {orders_list}")

    # Test filtering orders by customer
    print("\n4. Filtering orders by customer email...")

    customer_orders = list_orders(customer_email="alice.johnson@example.com")
    print(f"✓ {customer_orders}")

    # Test filtering orders by status
    print("\n5. Filtering orders by status (confirmed)...")

    confirmed_orders = list_orders(status="confirmed")
    print(f"✓ {confirmed_orders}")


async def test_appointment_operations():
    """Test appointment scheduling operations."""
    print("\n" + "=" * 50)
    print("Testing Appointment Operations")
    print("=" * 50)

    # Test creating appointments
    print("\n1. Creating appointments...")

    appointment1_result = create_appointment(
        customer_name="John Doe",
        customer_email="john.doe@example.com",
        service_type="consultation",
        appointment_datetime="2025-01-20 10:00",
        duration_minutes=60,
        notes="First-time consultation for business planning",
    )
    print(f"✓ {appointment1_result}")

    appointment2_result = create_appointment(
        customer_name="Jane Smith",
        customer_email="jane.smith@example.com",
        service_type="therapy",
        appointment_datetime="2025-01-21 14:30",
        duration_minutes=45,
        notes="Follow-up therapy session",
    )
    print(f"✓ {appointment2_result}")

    # Test listing all appointments
    print("\n2. Listing all appointments...")

    appointments_list = list_appointments()
    print(f"✓ {appointments_list}")

    # Test filtering appointments by service type
    print("\n3. Filtering appointments by service type...")

    consultation_appointments = list_appointments(service_type="consultation")
    print(f"✓ {consultation_appointments}")

    # Test filtering appointments by status
    print("\n4. Filtering appointments by status...")

    scheduled_appointments = list_appointments(status="scheduled")
    print(f"✓ {scheduled_appointments}")

    # Test filtering appointments by date range
    print("\n5. Filtering appointments by date range...")

    date_filtered = list_appointments(date_from="2025-01-20", date_to="2025-01-25")
    print(f"✓ {date_filtered}")


async def test_error_handling():
    """Test error handling scenarios."""
    print("\n" + "=" * 50)
    print("Testing Error Handling")
    print("=" * 50)

    # Test creating order with non-existent product
    print("\n1. Testing order with non-existent product...")

    invalid_order = create_order(
        customer_name="Test User",
        customer_email="test@example.com",
        items=[{"product_id": "nonexistent", "quantity": 1}],
        shipping_address="Test Address",
    )
    print(f"✓ {invalid_order}")

    # Test creating order with insufficient stock
    print("\n2. Testing order with excessive quantity...")

    excessive_order = create_order(
        customer_name="Test User",
        customer_email="test@example.com",
        items=[{"product_id": "prod-003", "quantity": 100}],  # Only 3 in stock
        shipping_address="Test Address",
    )
    print(f"✓ {excessive_order}")

    # Test invalid appointment datetime format
    print("\n3. Testing invalid appointment datetime...")

    invalid_appointment = create_appointment(
        customer_name="Test User",
        customer_email="test@example.com",
        service_type="consultation",
        appointment_datetime="invalid-date-format",
    )
    print(f"✓ {invalid_appointment}")

    # Test updating non-existent order
    print("\n4. Testing update of non-existent order...")

    invalid_update = update_order_status(order_id="nonexistent", status="confirmed")
    print(f"✓ {invalid_update}")


async def test_business_scenarios():
    """Test realistic business scenarios."""
    print("\n" + "=" * 50)
    print("Testing Business Scenarios")
    print("=" * 50)

    print("\n1. Scenario: Customer books consultation and orders products...")

    # Book a consultation appointment
    consultation = create_appointment(
        customer_name="Sarah Wilson",
        customer_email="sarah.wilson@example.com",
        service_type="consultation",
        appointment_datetime="2025-01-25 11:00",
        notes="Interested in wellness program",
    )
    print(f"✓ Consultation booked: {consultation}")

    # Order related products
    wellness_order = create_order(
        customer_name="Sarah Wilson",
        customer_email="sarah.wilson@example.com",
        items=[
            {"product_id": "prod-001", "quantity": 1},  # Consultation package
        ],
        shipping_address="789 Wellness Ave, Health City, HC 54321",
        notes="Follow-up to consultation appointment",
    )
    print(f"✓ Products ordered: {wellness_order}")

    print("\n2. Scenario: Check all customer activities...")

    # Check customer's appointments
    customer_appointments = (
        list_appointments()
    )  # Would filter by email in real scenario
    print(f"✓ All appointments: {customer_appointments}")

    # Check customer's orders
    customer_orders = list_orders(customer_email="sarah.wilson@example.com")
    print(f"✓ Customer orders: {customer_orders}")


async def test_business_stats():
    """Test business statistics and reporting."""
    print("\n" + "=" * 50)
    print("Testing Business Statistics")
    print("=" * 50)

    print("\n1. Getting comprehensive business statistics...")

    stats = get_business_stats()
    print(f"✓ {stats}")


def cleanup_test_data():
    """Clean up test data directory."""
    if TEST_DATA_DIR.exists():
        shutil.rmtree(TEST_DATA_DIR)
        print("✓ Test data cleaned up")


async def main():
    """Run all tests."""
    print("🚀 Starting Business MCP Server Tests")
    print("=" * 60)

    try:
        # Set up test environment
        setup_test_environment()

        await test_product_operations()
        await test_order_operations()
        await test_appointment_operations()
        await test_error_handling()
        await test_business_scenarios()
        await test_business_stats()

        print("\n" + "=" * 60)
        print("✅ All tests completed successfully!")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        cleanup_test_data()


if __name__ == "__main__":
    asyncio.run(main())
