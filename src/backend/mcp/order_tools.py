"""
Order tools for the MCP booking server.
Handles order tracking and order management.
"""

import json
from datetime import datetime
from typing import Dict, List

from mcp import types


class OrderTools:
    """Tools for managing orders and order tracking."""

    def __init__(self, orders_data: List[Dict], data_dir: str):
        self.orders_data = orders_data
        self.data_dir = data_dir

    def get_tool_definitions(self) -> List[types.Tool]:
        """Get order tool definitions."""
        return [
            types.Tool(
                name="get_order_status",
                description="Get the status and details of a specific order",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "order_id": {
                            "type": "string",
                            "description": "ID of the order to check",
                        }
                    },
                    "required": ["order_id"],
                },
            ),
            types.Tool(
                name="list_orders",
                description="List orders with optional filtering",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "customer_email": {
                            "type": "string",
                            "description": "Optional: Filter orders by customer email",
                        },
                        "status": {
                            "type": "string",
                            "description": "Optional: Filter by order status (pending, confirmed, shipped, delivered, cancelled)",
                        },
                        "date_from": {
                            "type": "string",
                            "description": "Optional: Start date for filtering (YYYY-MM-DD format)",
                        },
                        "date_to": {
                            "type": "string",
                            "description": "Optional: End date for filtering (YYYY-MM-DD format)",
                        },
                        "min_amount": {
                            "type": "number",
                            "description": "Optional: Minimum order amount filter",
                        },
                        "max_amount": {
                            "type": "number",
                            "description": "Optional: Maximum order amount filter",
                        },
                    },
                    "required": [],
                },
            ),
        ]

    async def get_order_status(self, args: dict) -> str:
        """Get the status and details of a specific order."""
        try:
            order_id = args.get("order_id")
            if not order_id:
                return "Error: Missing order_id"

            for order in self.orders_data:
                if order["id"] == order_id:
                    # Add formatted date and additional info
                    order_copy = order.copy()
                    order_date = datetime.fromisoformat(order["order_date"])
                    order_copy["order_date_formatted"] = order_date.strftime(
                        "%B %d, %Y at %I:%M %p"
                    )
                    order_copy["days_since_order"] = (datetime.now() - order_date).days

                    # Calculate order summary
                    total_items = sum(item["quantity"] for item in order["items"])
                    order_copy["total_items"] = total_items

                    return json.dumps({"success": True, "order": order_copy}, indent=2)

            return "Error: Order not found"

        except Exception as e:
            return f"Error retrieving order: {str(e)}"

    async def list_orders(self, args: dict) -> str:
        """List orders with optional filtering."""
        try:
            filtered_orders = list(self.orders_data)

            # Apply filters
            if "customer_email" in args:
                filtered_orders = [
                    order
                    for order in filtered_orders
                    if order["customer_email"].lower() == args["customer_email"].lower()
                ]

            if "status" in args:
                filtered_orders = [
                    order
                    for order in filtered_orders
                    if order["status"].lower() == args["status"].lower()
                ]

            if "date_from" in args:
                try:
                    date_from = datetime.strptime(args["date_from"], "%Y-%m-%d")
                    filtered_orders = [
                        order
                        for order in filtered_orders
                        if datetime.fromisoformat(order["order_date"]) >= date_from
                    ]
                except ValueError:
                    return "Error: Invalid date_from format. Use YYYY-MM-DD"

            if "date_to" in args:
                try:
                    date_to = datetime.strptime(args["date_to"], "%Y-%m-%d")
                    # Include the entire day by setting time to end of day
                    date_to = date_to.replace(hour=23, minute=59, second=59)
                    filtered_orders = [
                        order
                        for order in filtered_orders
                        if datetime.fromisoformat(order["order_date"]) <= date_to
                    ]
                except ValueError:
                    return "Error: Invalid date_to format. Use YYYY-MM-DD"

            if "min_amount" in args:
                min_amount = float(args["min_amount"])
                filtered_orders = [
                    order
                    for order in filtered_orders
                    if order["total_amount"] >= min_amount
                ]

            if "max_amount" in args:
                max_amount = float(args["max_amount"])
                filtered_orders = [
                    order
                    for order in filtered_orders
                    if order["total_amount"] <= max_amount
                ]

            # Sort by order date (newest first)
            filtered_orders.sort(key=lambda x: x["order_date"], reverse=True)

            # Add summary information to each order
            for order in filtered_orders:
                order_date = datetime.fromisoformat(order["order_date"])
                order["order_date_formatted"] = order_date.strftime("%B %d, %Y")
                order["total_items"] = sum(item["quantity"] for item in order["items"])
                order["days_since_order"] = (datetime.now() - order_date).days

            # Calculate statistics
            total_orders = len(filtered_orders)
            total_revenue = sum(order["total_amount"] for order in filtered_orders)
            avg_order_value = total_revenue / total_orders if total_orders > 0 else 0

            result = {
                "total_orders": total_orders,
                "total_revenue": total_revenue,
                "average_order_value": round(avg_order_value, 2),
                "orders": filtered_orders,
            }

            if args:
                result["filters_applied"] = args

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error listing orders: {str(e)}"
