"""
Product tools for the MCP booking server.
Handles product management, inventory, and purchasing.
"""

import json
from datetime import datetime
from typing import Dict, List
import uuid

from mcp import types


class ProductTools:
    """Tools for managing products and inventory."""

    def __init__(
        self, products_data: List[Dict], orders_data: List[Dict], data_dir: str
    ):
        self.products_data = products_data
        self.orders_data = orders_data
        self.data_dir = data_dir

    def get_tool_definitions(self) -> List[types.Tool]:
        """Get product tool definitions."""
        return [
            types.Tool(
                name="get_product",
                description="Get details of a specific product by ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "product_id": {
                            "type": "string",
                            "description": "ID of the product to retrieve",
                        }
                    },
                    "required": ["product_id"],
                },
            ),
            types.Tool(
                name="list_products",
                description="List all available products with optional filtering",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Optional: Filter by product category",
                        },
                        "available_only": {
                            "type": "boolean",
                            "description": "Optional: Show only products in stock (default: false)",
                        },
                        "min_price": {
                            "type": "number",
                            "description": "Optional: Minimum price filter",
                        },
                        "max_price": {
                            "type": "number",
                            "description": "Optional: Maximum price filter",
                        },
                    },
                    "required": [],
                },
            ),
            types.Tool(
                name="buy_product",
                description="Purchase a product and update inventory",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "product_id": {
                            "type": "string",
                            "description": "ID of the product to purchase",
                        },
                        "quantity": {
                            "type": "integer",
                            "description": "Quantity to purchase (default: 1)",
                        },
                        "customer_name": {
                            "type": "string",
                            "description": "Name of the customer",
                        },
                        "customer_email": {
                            "type": "string",
                            "description": "Email address of the customer",
                        },
                        "shipping_address": {
                            "type": "string",
                            "description": "Shipping address for the order",
                        },
                    },
                    "required": [
                        "product_id",
                        "customer_name",
                        "customer_email",
                        "shipping_address",
                    ],
                },
            ),
        ]

    async def get_product(self, args: dict) -> str:
        """Get details of a specific product by ID."""
        try:
            product_id = args.get("product_id")
            if not product_id:
                return "Error: Missing product_id"

            for product in self.products_data:
                if product["id"] == product_id:
                    # Add availability status
                    product_copy = product.copy()
                    product_copy["in_stock"] = product["stock_quantity"] > 0
                    product_copy["availability"] = (
                        "In Stock" if product["stock_quantity"] > 0 else "Out of Stock"
                    )

                    return json.dumps(
                        {"success": True, "product": product_copy}, indent=2
                    )

            return "Error: Product not found"

        except Exception as e:
            return f"Error retrieving product: {str(e)}"

    async def list_products(self, args: dict) -> str:
        """List all available products with optional filtering."""
        try:
            filtered_products = list(self.products_data)

            # Apply filters
            if "category" in args:
                filtered_products = [
                    product
                    for product in filtered_products
                    if product["category"].lower() == args["category"].lower()
                ]

            if args.get("available_only", False):
                filtered_products = [
                    product
                    for product in filtered_products
                    if product["stock_quantity"] > 0
                ]

            if "min_price" in args:
                min_price = float(args["min_price"])
                filtered_products = [
                    product
                    for product in filtered_products
                    if product["price"] >= min_price
                ]

            if "max_price" in args:
                max_price = float(args["max_price"])
                filtered_products = [
                    product
                    for product in filtered_products
                    if product["price"] <= max_price
                ]

            # Add availability info to each product
            for product in filtered_products:
                product["in_stock"] = product["stock_quantity"] > 0
                product["availability"] = (
                    "In Stock" if product["stock_quantity"] > 0 else "Out of Stock"
                )

            # Sort by name
            filtered_products.sort(key=lambda x: x["name"])

            result = {
                "total_products": len(filtered_products),
                "products": filtered_products,
            }

            if args:
                result["filters_applied"] = args

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error listing products: {str(e)}"

    async def buy_product(self, args: dict) -> str:
        """Purchase a product and update inventory."""
        try:
            # Validate required fields
            required_fields = [
                "product_id",
                "customer_name",
                "customer_email",
                "shipping_address",
            ]
            for field in required_fields:
                if field not in args:
                    return f"Error: Missing required field '{field}'"

            product_id = args["product_id"]
            quantity = args.get("quantity", 1)

            # Find the product
            product = None
            for p in self.products_data:
                if p["id"] == product_id:
                    product = p
                    break

            if not product:
                return "Error: Product not found"

            # Check stock availability
            if product["stock_quantity"] < quantity:
                return f"Error: Insufficient stock. Available: {product['stock_quantity']}, Requested: {quantity}"

            # Calculate total
            total_price = product["price"] * quantity

            # Create order
            order_id = str(uuid.uuid4())
            new_order = {
                "id": order_id,
                "customer_name": args["customer_name"],
                "customer_email": args["customer_email"],
                "shipping_address": args["shipping_address"],
                "status": "confirmed",
                "total_amount": total_price,
                "order_date": datetime.now().isoformat(),
                "items": [
                    {
                        "product_id": product_id,
                        "product_name": product["name"],
                        "quantity": quantity,
                        "unit_price": product["price"],
                        "total_price": total_price,
                    }
                ],
            }

            # Update inventory
            product["stock_quantity"] -= quantity

            # Add order to orders data
            self.orders_data.append(new_order)

            return json.dumps(
                {
                    "success": True,
                    "message": "Product purchased successfully",
                    "order": new_order,
                    "remaining_stock": product["stock_quantity"],
                },
                indent=2,
            )

        except Exception as e:
            return f"Error purchasing product: {str(e)}"
