"""
plugin_marketplace.db.models
Database models for the plugin marketplace.
"""

from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import String, Text, Boolean, Integer, DateTime, ForeignKey, Index, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Use the same Base that database.py creates
from plugin_marketplace.db.database import Base


class Extension(Base):
    """Marketplace extension."""
    __tablename__ = "pm_extensions"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    author: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    homepage: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    repository: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tool_type: Mapped[str] = mapped_column(String(64), nullable=False, default="builtin")
    popularity: Mapped[int] = mapped_column(Integer, default=0)
    icon_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    categories: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    is_official: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), default="active")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    manifest: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    install_command: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    uninstall_command: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mcp_transport: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mcp_command: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mcp_args: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    mcp_env_vars: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    mcp_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    tools: Mapped[List["Tool"]] = relationship("Tool", back_populates="extension", lazy="selectin")
    user_extensions: Mapped[List["UserExtension"]] = relationship("UserExtension", back_populates="extension", lazy="selectin")

    __table_args__ = (
        Index("ix_pm_extensions_name", "name"),
        Index("ix_pm_extensions_tool_type", "tool_type"),
    )


class Tool(Base):
    """Tool provided by an extension."""
    __tablename__ = "pm_tools"

    id: Mapped[str] = mapped_column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    extension_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("pm_extensions.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    input_schema: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)
    output_schema: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    display_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mcp_tool_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False, default="medium")
    side_effect: Mapped[str] = mapped_column(String(64), nullable=False, default="read")
    requires_confirmation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allowed_intents: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    domains: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    requires_auth_scope: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    max_calls_per_run: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    timeout_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=10000)
    returns_sensitive_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    audit_payload_level: Mapped[str] = mapped_column(String(32), nullable=False, default="summary")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    extension: Mapped["Extension"] = relationship("Extension", back_populates="tools")
    agent_bindings: Mapped[List["AgentToolBinding"]] = relationship("AgentToolBinding", back_populates="tool", lazy="selectin")

    __table_args__ = (
        Index("ix_pm_tools_extension_id", "extension_id"),
        Index("ix_pm_tools_name", "name"),
        Index("ix_pm_tools_enabled", "enabled"),
    )


class UserExtension(Base):
    """User's installed extension."""
    __tablename__ = "pm_user_extensions"

    id: Mapped[str] = mapped_column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    extension_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("pm_extensions.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), default="installing")
    config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    extension: Mapped["Extension"] = relationship("Extension", back_populates="user_extensions")

    __table_args__ = (
        Index("ix_pm_user_extensions_user_id", "user_id"),
        Index("ix_pm_user_extensions_extension_id", "extension_id"),
    )


class AgentToolBinding(Base):
    """Binding between an agent and a tool."""
    __tablename__ = "pm_agent_tool_bindings"

    id: Mapped[str] = mapped_column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id: Mapped[str] = mapped_column(String(128), nullable=False)
    tool_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("pm_tools.id", ondelete="CASCADE"), nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    tool: Mapped["Tool"] = relationship("Tool", back_populates="agent_bindings")

    __table_args__ = (
        Index("ix_pm_agent_tool_bindings_agent_id", "agent_id"),
        Index("ix_pm_agent_tool_bindings_tool_id", "tool_id"),
    )
