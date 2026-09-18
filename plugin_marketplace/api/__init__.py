"""
plugin_marketplace.api
FastAPI routes and schemas for the plugin marketplace.
"""

from plugin_marketplace.api.routes import create_router
from plugin_marketplace.api import schemas

__all__ = ["create_router", "schemas"]
