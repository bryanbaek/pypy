# MCP Booking & Ecommerce Server

A Model Context Protocol (MCP) server implementation for business booking, product management, and order tracking. The server provides structured tools for appointment scheduling, product sales, and order management with full business logic.

## 🏗️ Architecture

The MCP server is organized into modular components for better maintainability:

```
src/backend/mcp/
├── booking_server.py      # Main server orchestration
├── appointment_tools.py   # Appointment management tools
├── product_tools.py       # Product & inventory tools  
├── order_tools.py         # Order tracking tools
├── test_booking_server.py # Comprehensive test suite
└── README.md             # This documentation
```

## 📋 Available Tools

### 🗓️ Appointment Tools (4 tools)

#### 1. `create_appointment`
Create a new customer appointment with smart scheduling validation.

**Parameters:**
- `customer_name` (required): Customer's full name
- `customer_email` (required): Customer's email address  
- `service_type` (required): Type of service (consultation, health_checkup, therapy_session)
- `date` (required): Appointment date (YYYY-MM-DD format)
- `time` (required): Appointment time (HH:MM format, 9 AM to 5 PM)
- `notes` (optional): Additional appointment notes

**Example:**
```json
{
  "customer_name": "John Doe",
  "customer_email": "john.doe@email.com",
  "service_type": "consultation", 
  "date": "2024-02-15",
  "time": "10:00",
  "notes": "Initial consultation for wellness program"
}
```

#### 2. `delete_appointment`
Cancel and remove an existing appointment.

**Parameters:**
- `appointment_id` (required): ID of the appointment to delete

#### 3. `get_available_slots`
Check available appointment slots for a specific date.

**Parameters:**
- `date` (required): Date to check availability (YYYY-MM-DD format)
- `service_type` (optional): Filter by specific service type

**Features:**
- Business hours: 9 AM - 5 PM
- Hourly time slots
- Conflict detection with existing appointments

#### 4. `list_appointments`
List appointments with flexible filtering options.

**Optional Parameters:**
- `date`: Filter by specific date (YYYY-MM-DD)
- `customer_email`: Filter by customer email
- `service_type`: Filter by service type
- `status`: Filter by status (scheduled, completed, cancelled)

### 🛍️ Product Tools (3 tools)

#### 1. `get_product`
Retrieve detailed information about a specific product.

**Parameters:**
- `product_id` (required): ID of the product to retrieve

**Returns:** Complete product details including stock availability

#### 2. `list_products`
List all products with advanced filtering capabilities.

**Optional Parameters:**
- `category`: Filter by product category
- `available_only`: Show only in-stock products (boolean)
- `min_price`: Minimum price filter (number)
- `max_price`: Maximum price filter (number)

**Features:**
- Real-time stock status
- Category-based organization
- Price range filtering
- Availability indicators

#### 3. `buy_product`
Purchase products with automatic inventory management.

**Parameters:**
- `product_id` (required): ID of the product to purchase
- `quantity` (optional): Quantity to purchase (default: 1)
- `customer_name` (required): Customer's full name
- `customer_email` (required): Customer's email address
- `shipping_address` (required): Complete shipping address

**Features:**
- Stock validation and deduction
- Order creation with unique ID
- Customer tracking
- Inventory management

### 📦 Order Tools (2 tools)

#### 1. `get_order_status`
Check the status and details of a specific order.

**Parameters:**
- `order_id` (required): ID of the order to check

**Returns:** Complete order details with status, items, and tracking info

#### 2. `list_orders`
List orders with comprehensive filtering options.

**Optional Parameters:**
- `customer_email`: Filter by customer email
- `status`: Filter by order status (pending, confirmed, shipped, delivered, cancelled)
- `date_from`: Start date for filtering (YYYY-MM-DD)
- `date_to`: End date for filtering (YYYY-MM-DD)
- `min_amount`: Minimum order amount filter
- `max_amount`: Maximum order amount filter

**Analytics:**
- Total order count and revenue
- Average order value calculation
- Customer purchase history

## 🚀 Quick Start

### Installation

1. Install dependencies:
```bash
uv add mcp python-dateutil
```

2. Run the server:
```bash
uv run python src/backend/mcp/business_server.py
```

### Running Tests

Execute the comprehensive test suite:
```bash
# Using justfile
just booking-test

# Or directly
uv run python src/backend/mcp/test_booking_server.py
```

## 💼 Business Logic

### Appointment Management
- **Business Hours:** 9:00 AM - 5:00 PM  
- **Time Slots:** Hourly intervals
- **Conflict Detection:** Prevents double-booking
- **Status Tracking:** scheduled → completed/cancelled

### Product Catalog
- **Categories:** consultation, health, therapy, wellness, mental_health
- **Inventory Management:** Real-time stock tracking
- **Pricing:** Flexible pricing with filtering
- **Availability:** Automatic stock status updates

### Order Processing
- **Order States:** confirmed → shipped → delivered
- **Payment:** Total calculation with line items
- **Customer Tracking:** Email-based customer identification
- **Shipping:** Address validation and tracking

## 📊 Sample Data

The server includes realistic sample data:

### Products (5 items)
- Basic Consultation Package ($150.00)
- Premium Health Checkup ($300.00)  
- Therapy Session Package ($500.00)
- Wellness Kit ($89.99)
- Mental Health Assessment ($200.00)

### Appointments (3 scheduled)
- John Doe - Consultation (2024-01-15)
- Jane Smith - Health Checkup (2024-01-16)
- Bob Wilson - Therapy Session (2024-01-17)

### Orders (2 completed)
- Alice Johnson - Basic Consultation Package
- Mike Brown - Premium Health Checkup + Wellness Kit

## 🛠️ Development

### Project Structure

The MCP server follows a modular architecture:

- **`booking_server.py`**: Main server class that orchestrates all tools
- **`appointment_tools.py`**: Appointment-specific business logic and tools
- **`product_tools.py`**: Product management and e-commerce functionality  
- **`order_tools.py`**: Order processing and tracking capabilities
- **`test_booking_server.py`**: Comprehensive test suite covering all scenarios

### Adding New Tools

1. Create methods in the appropriate tool class
2. Add tool definitions to `get_tool_definitions()` 
3. Update the main server's tool routing in `handle_call_tool()`
4. Add tests to the test suite

### Error Handling

The server includes comprehensive error handling:
- Input validation for all parameters
- Business rule enforcement (stock levels, time conflicts)
- Graceful error messages with specific guidance
- Fallback behavior for invalid requests

## 🔧 Configuration

### Environment Setup

The server supports both development and production modes:

**Development Mode:** 
- Mock MCP classes when package unavailable
- In-memory data storage
- Debug logging enabled

**Production Mode:**
- Full MCP integration
- Persistent data storage
- Production logging

### Data Storage

Currently uses in-memory storage with sample data. For production:
- Integrate with PostgreSQL database
- Add data persistence layer
- Implement backup and recovery

## 🧪 Testing

The test suite covers:

### Functional Testing
- All tool operations (create, read, update, delete)
- Parameter validation and error cases
- Business logic enforcement

### Integration Testing  
- End-to-end customer scenarios
- Cross-tool data consistency
- Real-world business workflows

### Error Handling
- Invalid input validation
- Resource not found scenarios
- Business constraint violations

### Business Scenarios
- Customer journey testing
- Multi-tool workflow validation
- Data consistency across operations

## 📈 Use Cases

### Healthcare Practice
- Patient appointment scheduling
- Service package sales
- Treatment plan management

### Wellness Center
- Class and session bookings
- Product and supplement sales
- Member order tracking

### Consulting Business
- Client meeting scheduling
- Service package offerings
- Engagement tracking

### General Business
- Service appointment booking
- Product catalog management
- Customer order processing

## 🔄 Future Enhancements

### Planned Features
- Calendar integration (Google Calendar, Outlook)
- Payment processing integration
- Email notification system
- Customer portal interface
- Analytics and reporting dashboard
- Multi-location support

### Technical Improvements
- Database persistence layer
- Caching for improved performance  
- Real-time notifications
- API rate limiting
- Enhanced security features

## 📝 License

This project is part of the diary application suite. See the main LICENSE file for details.

## 🤝 Contributing

1. Follow the established code organization patterns
2. Add comprehensive tests for new features
3. Update documentation for any API changes
4. Ensure error handling for all edge cases
5. Test integration between tool modules 