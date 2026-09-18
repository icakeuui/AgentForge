"""
plugin_marketplace.api.schemas
Pydantic schemas for the plugin marketplace API.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ConfigFieldItem(BaseModel):
    key: str
    label: str
    type: str = "text"
    required: bool = False
    placeholder: Optional[str] = None
    help_text: Optional[str] = None


class ExtensionListItem(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    icon_url: Optional[str] = None
    tool_type: str
    categories: List[str] = Field(default_factory=list)
    author: Optional[str] = None
    homepage: Optional[str] = None
    popularity: int = 0
    is_official: bool = False
    config_fields: List[ConfigFieldItem] = Field(default_factory=list)


class ExtensionDetail(ExtensionListItem):
    status: str
    tools: List["ToolListItem"] = Field(default_factory=list)


class ToolListItem(BaseModel):
    id: str
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    risk_level: str = "medium"
    side_effect: str = "read"
    requires_confirmation: bool = False
    allowed_intents: List[str] = Field(default_factory=list)
    domains: List[str] = Field(default_factory=list)
    max_calls_per_run: int = 2
    timeout_ms: int = 10000
    returns_sensitive_data: bool = False
    audit_payload_level: str = "summary"


class ToolExecuteRequest(BaseModel):
    tool_id: str = Field(..., description="Tool ID in format 'extension_id/tool_name'")
    arguments: Dict[str, Any] = Field(default_factory=dict)
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ToolExecuteResponse(BaseModel):
    result: str


class AgentToolBindRequest(BaseModel):
    tool_ids: List[str] = Field(..., description="List of tool IDs to bind")


class AgentToolListItem(BaseModel):
    tool_id: str
    config: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class ExtensionInstallRequest(BaseModel):
    user_id: str
    config: Dict[str, Any] = Field(default_factory=dict)


class ExtensionInstallResponse(BaseModel):
    extension_id: str
    status: str
    message: str = "ok"


class UserExtensionItem(BaseModel):
    extension_id: str
    name: str
    description: Optional[str] = None
    tool_type: str
    status: str
    error_message: Optional[str] = None


class ExtensionConnectionTestRequest(BaseModel):
    config: Dict[str, Any] = Field(default_factory=dict)


class ExtensionConnectionTestResponse(BaseModel):
    ok: bool
    message: str
    missing_fields: List[str] = Field(default_factory=list)


# Rebuild forward refs
ExtensionDetail.model_rebuild()
