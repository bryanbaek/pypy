"""
MCP Server implementation for business management using FastMCP.
Provides tools, resources, and prompts for managing products, orders, and appointments.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from mcp.server import FastMCP
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastMCP server
mcp = FastMCP("business-mcp-server")

# Data directory setup
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
(DATA_DIR / "products").mkdir(exist_ok=True)
(DATA_DIR / "orders").mkdir(exist_ok=True)
(DATA_DIR / "appointments").mkdir(exist_ok=True)


# ============================================================================
# RESOURCES: Application-controlled contextual data
# ============================================================================


@mcp.resource("business://products/{product_id}")
def get_product_resource(product_id: str) -> str:
    """Get a product as a resource for AI context"""
    product_file = DATA_DIR / "products" / f"{product_id}.json"

    if not product_file.exists():
        raise ValueError(f"Product '{product_id}' not found")

    with open(product_file, "r", encoding="utf-8") as f:
        product_data = json.load(f)

    # Format as markdown for better AI consumption
    content = f"# {product_data['name']}\n\n"
    content += f"**Product ID:** {product_data['id']}\n"
    content += f"**Price:** ${product_data['price']:.2f}\n"
    content += f"**Category:** {product_data['category']}\n"
    content += f"**Stock Quantity:** {product_data['stock_quantity']}\n"
    content += f"**Status:** {'In Stock' if product_data['stock_quantity'] > 0 else 'Out of Stock'}\n"
    content += f"**Created:** {product_data['created_at']}\n"

    if product_data.get("description"):
        content += f"\n## Description\n{product_data['description']}\n"

    if product_data.get("specifications"):
        content += "\n## Specifications\n"
        for key, value in product_data["specifications"].items():
            content += f"- **{key}:** {value}\n"

    return content


@mcp.resource("business://orders/{order_id}")
def get_order_resource(order_id: str) -> str:
    """Get an order as a resource for AI context"""
    order_file = DATA_DIR / "orders" / f"{order_id}.json"

    if not order_file.exists():
        raise ValueError(f"Order '{order_id}' not found")

    with open(order_file, "r", encoding="utf-8") as f:
        order_data = json.load(f)

    # Format as markdown
    content = f"# Order #{order_data['id']}\n\n"
    content += f"**Customer:** {order_data['customer_name']} ({order_data['customer_email']})\n"
    content += f"**Status:** {order_data['status'].title()}\n"
    content += f"**Total Amount:** ${order_data['total_amount']:.2f}\n"
    content += f"**Order Date:** {order_data['order_date']}\n"

    if order_data.get("shipping_address"):
        content += f"**Shipping Address:** {order_data['shipping_address']}\n"

    content += "\n## Items\n"
    for item in order_data.get("items", []):
        content += f"- {item['product_name']} x{item['quantity']} = ${item['total_price']:.2f}\n"

    if order_data.get("notes"):
        content += f"\n## Notes\n{order_data['notes']}\n"

    return content


@mcp.resource("business://appointments/{appointment_id}")
def get_appointment_resource(appointment_id: str) -> str:
    """Get an appointment as a resource for AI context"""
    appointment_file = DATA_DIR / "appointments" / f"{appointment_id}.json"

    if not appointment_file.exists():
        raise ValueError(f"Appointment '{appointment_id}' not found")

    with open(appointment_file, "r", encoding="utf-8") as f:
        appointment_data = json.load(f)

    # Format as markdown
    content = f"# Appointment: {appointment_data['service_type'].title()}\n\n"
    content += f"**Appointment ID:** {appointment_data['id']}\n"
    content += f"**Customer:** {appointment_data['customer_name']} ({appointment_data['customer_email']})\n"
    content += f"**Service:** {appointment_data['service_type']}\n"
    content += f"**Date & Time:** {appointment_data['appointment_datetime']}\n"
    content += f"**Status:** {appointment_data['status'].title()}\n"
    content += f"**Duration:** {appointment_data.get('duration_minutes', 60)} minutes\n"

    if appointment_data.get("notes"):
        content += f"\n## Notes\n{appointment_data['notes']}\n"

    if appointment_data.get("preparation_instructions"):
        content += f"\n## Preparation Instructions\n{appointment_data['preparation_instructions']}\n"

    return content


@mcp.resource("business://dashboard")
def get_business_dashboard() -> str:
    """Get business dashboard summary for AI context"""
    # Get recent activity across all areas
    products_dir = DATA_DIR / "products"
    orders_dir = DATA_DIR / "orders"
    appointments_dir = DATA_DIR / "appointments"

    # Count totals
    total_products = len(list(products_dir.glob("*.json")))
    total_orders = len(list(orders_dir.glob("*.json")))
    total_appointments = len(list(appointments_dir.glob("*.json")))

    content = "# Business Dashboard\n\n"
    content += "## Overview\n"
    content += f"- **Total Products:** {total_products}\n"
    content += f"- **Total Orders:** {total_orders}\n"
    content += f"- **Total Appointments:** {total_appointments}\n\n"

    # Recent orders
    orders = []
    for order_file in orders_dir.glob("*.json"):
        try:
            with open(order_file, "r", encoding="utf-8") as f:
                orders.append(json.load(f))
        except Exception:
            continue

    orders.sort(key=lambda x: x["order_date"], reverse=True)
    recent_orders = orders[:3]

    if recent_orders:
        content += "## Recent Orders\n"
        for order in recent_orders:
            content += f"- **#{order['id']}** - {order['customer_name']} - ${order['total_amount']:.2f} - {order['status']}\n"
        content += "\n"

    # Upcoming appointments
    appointments = []
    for apt_file in appointments_dir.glob("*.json"):
        try:
            with open(apt_file, "r", encoding="utf-8") as f:
                apt_data = json.load(f)
                apt_datetime = datetime.fromisoformat(apt_data["appointment_datetime"])
                if apt_datetime >= datetime.now() and apt_data["status"] == "scheduled":
                    appointments.append(apt_data)
        except Exception:
            continue

    appointments.sort(key=lambda x: x["appointment_datetime"])
    upcoming_appointments = appointments[:3]

    if upcoming_appointments:
        content += "## Upcoming Appointments\n"
        for apt in upcoming_appointments:
            apt_date = datetime.fromisoformat(apt["appointment_datetime"])
            content += f"- **{apt['service_type']}** - {apt['customer_name']} - {apt_date.strftime('%Y-%m-%d %H:%M')}\n"
        content += "\n"

    # Low stock products
    low_stock = []
    for product_file in products_dir.glob("*.json"):
        try:
            with open(product_file, "r", encoding="utf-8") as f:
                product_data = json.load(f)
                if product_data["stock_quantity"] <= 5:
                    low_stock.append(product_data)
        except Exception:
            continue

    if low_stock:
        content += "## Low Stock Alert\n"
        for product in low_stock:
            content += (
                f"- **{product['name']}** - {product['stock_quantity']} remaining\n"
            )

    return content


# ============================================================================
# PROMPTS: User-controlled interactive templates
# ============================================================================


@mcp.prompt("daily-business-review")
def daily_business_review_prompt(date: str | None = None) -> str:
    """Generate a daily business review prompt"""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    return f"""# Daily Business Review - {date}

## 📊 **Sales & Revenue**
- What were today's total sales?
- Which products performed best?
- Any notable large orders or customers?
- How does today compare to yesterday/last week?

## 📦 **Inventory & Products**
- Any products running low on stock?
- New products added or updated?
- Customer feedback on products?
- Pricing adjustments needed?

## 📅 **Appointments & Services**
- How many appointments were completed today?
- Any no-shows or cancellations?
- Customer satisfaction from services?
- Schedule optimization opportunities?

## 💰 **Financial Performance**
- Revenue vs. goals for the day?
- Cost analysis (materials, labor, overhead)?
- Payment processing issues?
- Outstanding invoices or payments?

## 👥 **Customer Experience**
- Customer feedback or complaints?
- New customer acquisitions?
- Repeat customer activity?
- Service quality metrics?

## 🔧 **Operations**
- Any operational challenges today?
- Staff performance and productivity?
- System or process improvements needed?
- Supply chain or vendor issues?

## 🎯 **Tomorrow's Priorities**
- Key tasks for tomorrow?
- Appointments and deliveries scheduled?
- Marketing or promotional activities?
- Follow-ups needed with customers?

## 📈 **Growth Opportunities**
- Potential new business leads?
- Expansion or scaling opportunities?
- Process improvements identified?
- Investment or resource needs?

---
*Review each area and note specific metrics, challenges, and action items.*"""


@mcp.prompt("customer-consultation")
def customer_consultation_prompt(
    service_type: str | None = None, customer_name: str | None = None
) -> str:
    """Generate a customer consultation preparation prompt"""
    if service_type is None:
        service_type = "[Service Type]"
    if customer_name is None:
        customer_name = "[Customer Name]"

    return f"""# Customer Consultation Preparation

## 👤 **Customer Information**
- **Name:** {customer_name}
- **Service Requested:** {service_type}
- **Previous History:** [Review past orders/appointments]
- **Preferences:** [Known preferences or requirements]
- **Budget Range:** [If known]

## 🎯 **Consultation Objectives**
- **Primary Goal:** What does the customer want to achieve?
- **Pain Points:** What problems are they trying to solve?
- **Timeline:** When do they need the solution?
- **Success Criteria:** How will we measure success?

## 📋 **Preparation Checklist**
- [ ] Review customer history and previous interactions
- [ ] Prepare relevant product samples or demos
- [ ] Gather pricing information and options
- [ ] Prepare contract or agreement templates
- [ ] Set up presentation materials
- [ ] Confirm appointment logistics

## 💬 **Key Questions to Ask**
### Discovery Questions:
- What brought you to us today?
- What challenges are you currently facing?
- What solutions have you tried before?
- What's your ideal timeline for implementation?

### Qualification Questions:
- What's your budget range for this project?
- Who else is involved in the decision-making?
- What's your evaluation process?
- When do you need to make a decision?

### Closing Questions:
- Does this solution meet your needs?
- What concerns or questions do you have?
- What would need to happen for you to move forward?
- When would you like to start?

## 📝 **Follow-up Actions**
- [ ] Send consultation summary within 24 hours
- [ ] Provide detailed proposal or quote
- [ ] Schedule follow-up meeting if needed
- [ ] Add notes to customer record
- [ ] Set reminders for next steps

## 🎁 **Value Propositions**
- **Unique Benefits:** What sets us apart?
- **ROI/Cost Savings:** How do we provide value?
- **Quality Assurance:** What guarantees do we offer?
- **Support:** What ongoing support do we provide?

---
*Customize this template based on the specific service and customer needs.*"""


@mcp.prompt("inventory-planning")
def inventory_planning_prompt(period: str | None = None) -> str:
    """Generate an inventory planning and analysis prompt"""
    if period is None:
        period = "Monthly"

    return f"""# {period} Inventory Planning & Analysis

## 📊 **Current Inventory Status**
- **Total Products:** [Count active products]
- **Total Value:** [Calculate total inventory value]
- **Low Stock Items:** [Items below reorder point]
- **Out of Stock:** [Currently unavailable items]
- **Overstock Items:** [Items with excess inventory]

## 📈 **Sales Performance Analysis**
### Top Performers:
- **Best Selling Products:** [By quantity and revenue]
- **Highest Margin Items:** [Most profitable products]
- **Growth Products:** [Items with increasing demand]

### Underperformers:
- **Slow Moving Items:** [Products with low turnover]
- **Declining Sales:** [Items losing market share]
- **Low Margin Products:** [Items to review pricing]

## 🎯 **Demand Forecasting**
- **Seasonal Trends:** [Expected seasonal changes]
- **Market Trends:** [Industry or market factors]
- **Promotional Impact:** [Planned promotions or campaigns]
- **New Product Launches:** [Expected impact of new items]

## 📦 **Procurement Planning**
### Immediate Needs (Next 30 Days):
- [ ] [Product 1] - Quantity needed: [X]
- [ ] [Product 2] - Quantity needed: [X]
- [ ] [Product 3] - Quantity needed: [X]

### Medium-term Needs (30-90 Days):
- [ ] [Product 1] - Quantity needed: [X]
- [ ] [Product 2] - Quantity needed: [X]

### Long-term Planning (90+ Days):
- [ ] [Seasonal items for next season]
- [ ] [New product categories to explore]

## 💰 **Financial Considerations**
- **Available Budget:** [Current purchasing budget]
- **Cash Flow Impact:** [Payment terms and timing]
- **Storage Costs:** [Warehouse and holding costs]
- **Obsolescence Risk:** [Items at risk of becoming outdated]

## 🚚 **Supplier Management**
### Primary Suppliers:
- **Supplier A:** [Performance rating, lead times]
- **Supplier B:** [Performance rating, lead times]
- **Supplier C:** [Performance rating, lead times]

### Action Items:
- [ ] Review supplier performance and contracts
- [ ] Negotiate better terms or pricing
- [ ] Identify backup suppliers for critical items
- [ ] Evaluate new supplier opportunities

## 📋 **Process Improvements**
- **Automation Opportunities:** [Systems to streamline ordering]
- **Accuracy Improvements:** [Reduce counting errors]
- **Speed Enhancements:** [Faster order processing]
- **Cost Reductions:** [Lower procurement or holding costs]

## 🎯 **Goals & KPIs**
- **Inventory Turnover:** [Target ratio]
- **Service Level:** [% of orders fulfilled from stock]
- **Carrying Costs:** [Target % of inventory value]
- **Stockout Rate:** [Target % of time in stock]

---
*Use this framework to develop comprehensive inventory strategies.*"""


# ============================================================================
# TOOLS: Model-controlled functions for taking actions
# ============================================================================


@mcp.tool()
def create_product(
    name: str,
    price: float,
    category: str,
    stock_quantity: int,
    description: str | None = None,
    specifications: dict | None = None,
) -> str:
    """Create a new product in the inventory"""
    product_id = (
        f"prod_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
    )

    product_data = {
        "id": product_id,
        "name": name,
        "price": price,
        "category": category,
        "stock_quantity": stock_quantity,
        "description": description or "",
        "specifications": specifications or {},
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }

    product_file = DATA_DIR / "products" / f"{product_id}.json"
    with open(product_file, "w", encoding="utf-8") as f:
        json.dump(product_data, f, indent=2, ensure_ascii=False)

    return f"Product '{name}' created successfully with ID: {product_id}. Access via resource: business://products/{product_id}"


@mcp.tool()
def list_products(
    limit: int = 20,
    category: str | None = None,
    in_stock_only: bool = False,
    min_price: float | None = None,
    max_price: float | None = None,
) -> str:
    """List products with optional filtering"""
    products_dir = DATA_DIR / "products"
    products = []

    for product_file in products_dir.glob("*.json"):
        try:
            with open(product_file, "r", encoding="utf-8") as f:
                product_data = json.load(f)

            # Apply filters
            if category and product_data["category"] != category:
                continue
            if in_stock_only and product_data["stock_quantity"] <= 0:
                continue
            if min_price and product_data["price"] < min_price:
                continue
            if max_price and product_data["price"] > max_price:
                continue

            products.append(product_data)

        except Exception as e:
            logger.error(f"Error reading product {product_file}: {e}")
            continue

    products.sort(key=lambda x: x["name"])
    products = products[:limit]

    if not products:
        return "No products found matching the criteria."

    result = f"Found {len(products)} products:\n\n"
    for product in products:
        stock_status = (
            "✅ In Stock" if product["stock_quantity"] > 0 else "❌ Out of Stock"
        )
        result += f"**{product['name']}** (ID: {product['id']})\n"
        result += f"Price: ${product['price']:.2f} | Category: {product['category']} | Stock: {product['stock_quantity']} {stock_status}\n"
        result += f"Resource: business://products/{product['id']}\n"
        if product.get("description"):
            result += f"Description: {product['description'][:100]}{'...' if len(product['description']) > 100 else ''}\n"
        result += "-" * 50 + "\n"

    return result


@mcp.tool()
def create_order(
    customer_name: str,
    customer_email: str,
    items: list[dict],
    shipping_address: str | None = None,
    notes: str | None = None,
) -> str:
    """Create a new order with items list. Items format: [{"product_id": "prod_123", "quantity": 2}]"""
    order_id = f"ord_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"

    # Calculate order total and validate products
    order_items = []
    total_amount = 0.0

    for item in items:
        product_id = item["product_id"]
        quantity = item["quantity"]

        # Load product data
        product_file = DATA_DIR / "products" / f"{product_id}.json"
        if not product_file.exists():
            return f"Error: Product {product_id} not found"

        with open(product_file, "r", encoding="utf-8") as f:
            product_data = json.load(f)

        if product_data["stock_quantity"] < quantity:
            return f"Error: Insufficient stock for {product_data['name']}. Available: {product_data['stock_quantity']}, Requested: {quantity}"

        item_total = product_data["price"] * quantity
        total_amount += item_total

        order_items.append(
            {
                "product_id": product_id,
                "product_name": product_data["name"],
                "quantity": quantity,
                "unit_price": product_data["price"],
                "total_price": item_total,
            }
        )

        # Update product stock
        product_data["stock_quantity"] -= quantity
        product_data["updated_at"] = datetime.now().isoformat()
        with open(product_file, "w", encoding="utf-8") as f:
            json.dump(product_data, f, indent=2, ensure_ascii=False)

    order_data = {
        "id": order_id,
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": order_items,
        "total_amount": total_amount,
        "status": "pending",
        "shipping_address": shipping_address or "",
        "notes": notes or "",
        "order_date": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }

    order_file = DATA_DIR / "orders" / f"{order_id}.json"
    with open(order_file, "w", encoding="utf-8") as f:
        json.dump(order_data, f, indent=2, ensure_ascii=False)

    return f"Order created successfully with ID: {order_id}. Total: ${total_amount:.2f}. Access via resource: business://orders/{order_id}"


@mcp.tool()
def list_orders(
    limit: int = 20,
    status: str | None = None,
    customer_email: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> str:
    """List orders with optional filtering"""
    orders_dir = DATA_DIR / "orders"
    orders = []

    for order_file in orders_dir.glob("*.json"):
        try:
            with open(order_file, "r", encoding="utf-8") as f:
                order_data = json.load(f)

            # Apply filters
            if status and order_data["status"] != status:
                continue
            if customer_email and order_data["customer_email"] != customer_email:
                continue

            if date_from or date_to:
                order_date = datetime.fromisoformat(order_data["order_date"]).date()
                if date_from and order_date < datetime.fromisoformat(date_from).date():
                    continue
                if date_to and order_date > datetime.fromisoformat(date_to).date():
                    continue

            orders.append(order_data)

        except Exception as e:
            logger.error(f"Error reading order {order_file}: {e}")
            continue

    orders.sort(key=lambda x: x["order_date"], reverse=True)
    orders = orders[:limit]

    if not orders:
        return "No orders found matching the criteria."

    result = f"Found {len(orders)} orders:\n\n"
    for order in orders:
        status_emoji = {
            "pending": "⏳",
            "confirmed": "✅",
            "shipped": "🚚",
            "delivered": "📦",
            "cancelled": "❌",
        }.get(order["status"], "📋")
        result += f"**Order #{order['id']}** {status_emoji} {order['status'].title()}\n"
        result += f"Customer: {order['customer_name']} ({order['customer_email']})\n"
        result += (
            f"Total: ${order['total_amount']:.2f} | Date: {order['order_date'][:10]}\n"
        )
        result += f"Items: {len(order['items'])} | Resource: business://orders/{order['id']}\n"
        result += "-" * 50 + "\n"

    return result


@mcp.tool()
def create_appointment(
    customer_name: str,
    customer_email: str,
    service_type: str,
    appointment_datetime: str,
    duration_minutes: int = 60,
    notes: str | None = None,
) -> str:
    """Create a new appointment. Datetime format: YYYY-MM-DD HH:MM"""
    appointment_id = (
        f"apt_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
    )

    # Validate datetime format
    try:
        apt_datetime = datetime.fromisoformat(appointment_datetime.replace(" ", "T"))
    except ValueError:
        return "Error: Invalid datetime format. Use YYYY-MM-DD HH:MM"

    # Check if time slot is available (basic check)
    appointments_dir = DATA_DIR / "appointments"
    for apt_file in appointments_dir.glob("*.json"):
        try:
            with open(apt_file, "r", encoding="utf-8") as f:
                existing_apt = json.load(f)

            existing_datetime = datetime.fromisoformat(
                existing_apt["appointment_datetime"]
            )
            if (
                existing_datetime == apt_datetime
                and existing_apt["status"] == "scheduled"
            ):
                return f"Error: Time slot {appointment_datetime} is already booked"
        except Exception:
            continue

    appointment_data = {
        "id": appointment_id,
        "customer_name": customer_name,
        "customer_email": customer_email,
        "service_type": service_type,
        "appointment_datetime": apt_datetime.isoformat(),
        "duration_minutes": duration_minutes,
        "status": "scheduled",
        "notes": notes or "",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }

    appointment_file = DATA_DIR / "appointments" / f"{appointment_id}.json"
    with open(appointment_file, "w", encoding="utf-8") as f:
        json.dump(appointment_data, f, indent=2, ensure_ascii=False)

    return f"Appointment scheduled successfully with ID: {appointment_id} for {customer_name} on {appointment_datetime}. Access via resource: business://appointments/{appointment_id}"


@mcp.tool()
def list_appointments(
    limit: int = 20,
    status: str | None = None,
    service_type: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> str:
    """List appointments with optional filtering"""
    appointments_dir = DATA_DIR / "appointments"
    appointments = []

    for apt_file in appointments_dir.glob("*.json"):
        try:
            with open(apt_file, "r", encoding="utf-8") as f:
                apt_data = json.load(f)

            # Apply filters
            if status and apt_data["status"] != status:
                continue
            if service_type and apt_data["service_type"] != service_type:
                continue

            if date_from or date_to:
                apt_date = datetime.fromisoformat(
                    apt_data["appointment_datetime"]
                ).date()
                if date_from and apt_date < datetime.fromisoformat(date_from).date():
                    continue
                if date_to and apt_date > datetime.fromisoformat(date_to).date():
                    continue

            appointments.append(apt_data)

        except Exception as e:
            logger.error(f"Error reading appointment {apt_file}: {e}")
            continue

    appointments.sort(key=lambda x: x["appointment_datetime"])
    appointments = appointments[:limit]

    if not appointments:
        return "No appointments found matching the criteria."

    result = f"Found {len(appointments)} appointments:\n\n"
    for apt in appointments:
        apt_datetime = datetime.fromisoformat(apt["appointment_datetime"])
        status_emoji = {
            "scheduled": "📅",
            "completed": "✅",
            "cancelled": "❌",
            "no_show": "⚠️",
        }.get(apt["status"], "📋")
        result += f"**{apt['service_type'].title()}** {status_emoji} {apt['status'].title()}\n"
        result += f"Customer: {apt['customer_name']} ({apt['customer_email']})\n"
        result += f"Date & Time: {apt_datetime.strftime('%Y-%m-%d %H:%M')} ({apt['duration_minutes']} min)\n"
        result += f"Resource: business://appointments/{apt['id']}\n"
        if apt.get("notes"):
            result += (
                f"Notes: {apt['notes'][:50]}{'...' if len(apt['notes']) > 50 else ''}\n"
            )
        result += "-" * 50 + "\n"

    return result


@mcp.tool()
def update_order_status(order_id: str, status: str, notes: str | None = None) -> str:
    """Update order status. Valid statuses: pending, confirmed, shipped, delivered, cancelled"""
    valid_statuses = ["pending", "confirmed", "shipped", "delivered", "cancelled"]
    if status not in valid_statuses:
        return f"Error: Invalid status. Valid options: {', '.join(valid_statuses)}"

    order_file = DATA_DIR / "orders" / f"{order_id}.json"
    if not order_file.exists():
        return f"Order {order_id} not found"

    with open(order_file, "r", encoding="utf-8") as f:
        order_data = json.load(f)

    old_status = order_data["status"]
    order_data["status"] = status
    order_data["updated_at"] = datetime.now().isoformat()

    if notes:
        order_data["notes"] = notes

    with open(order_file, "w", encoding="utf-8") as f:
        json.dump(order_data, f, indent=2, ensure_ascii=False)

    return f"Order {order_id} status updated from '{old_status}' to '{status}'. Resource: business://orders/{order_id}"


@mcp.tool()
def get_business_stats() -> str:
    """Get comprehensive business statistics"""
    products_dir = DATA_DIR / "products"
    orders_dir = DATA_DIR / "orders"
    appointments_dir = DATA_DIR / "appointments"

    # Product stats
    products = []
    total_inventory_value = 0
    low_stock_count = 0

    for product_file in products_dir.glob("*.json"):
        try:
            with open(product_file, "r", encoding="utf-8") as f:
                product = json.load(f)
            products.append(product)
            total_inventory_value += product["price"] * product["stock_quantity"]
            if product["stock_quantity"] <= 5:
                low_stock_count += 1
        except Exception:
            continue

    # Order stats
    orders = []
    total_revenue = 0

    for order_file in orders_dir.glob("*.json"):
        try:
            with open(order_file, "r", encoding="utf-8") as f:
                order = json.load(f)
            orders.append(order)
            if order["status"] != "cancelled":
                total_revenue += order["total_amount"]
        except Exception:
            continue

    # Appointment stats
    appointments = []
    upcoming_appointments = 0

    for apt_file in appointments_dir.glob("*.json"):
        try:
            with open(apt_file, "r", encoding="utf-8") as f:
                apt = json.load(f)
            appointments.append(apt)
            apt_datetime = datetime.fromisoformat(apt["appointment_datetime"])
            if apt_datetime >= datetime.now() and apt["status"] == "scheduled":
                upcoming_appointments += 1
        except Exception:
            continue

    result = "📊 **Business Statistics**\n\n"
    result += "## Products & Inventory\n"
    result += f"- Total Products: {len(products)}\n"
    result += f"- Total Inventory Value: ${total_inventory_value:.2f}\n"
    result += f"- Low Stock Alert: {low_stock_count} products\n\n"

    result += "## Orders & Revenue\n"
    result += f"- Total Orders: {len(orders)}\n"
    result += f"- Total Revenue: ${total_revenue:.2f}\n"
    result += f"- Average Order Value: ${total_revenue / len(orders):.2f if orders else 0}\n\n"

    result += "## Appointments & Services\n"
    result += f"- Total Appointments: {len(appointments)}\n"
    result += f"- Upcoming Scheduled: {upcoming_appointments}\n\n"

    result += "## Quick Access\n"
    result += "- Dashboard Resource: business://dashboard\n"
    result += f"- Data Directory: {DATA_DIR.absolute()}"

    return result


if __name__ == "__main__":
    mcp.run()
