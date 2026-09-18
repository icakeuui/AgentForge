from typing import Any, Dict, Generic, List, Literal, Optional, TypeVar, Union
from pydantic import BaseModel, Field, UUID4, field_validator
from backend.models.constants import (
    ArcErrorCode,
    ResponseCode,
    ExecutionState,
    TerminationReason,
    ActionType,
    QuotaStatus,
    ExecutionStatus,
)

T = TypeVar("T")

class BaseResponse(BaseModel, Generic[T]):
    code: ResponseCode
    message: str
    data: Optional[T] = None

    @classmethod
    def success(cls, data: Any = None, message: str = "success"):
        return cls(code=ResponseCode.SUCCESS, message=message, data=data)

    @classmethod
    def error(cls, code: ResponseCode, message: str, data: Any = None):
        return cls(code=code, message=message, data=data)

class AuthContext(BaseModel):
    user_id: str
    team_id: str
    auth_mode: str
    request_id: str
    role: str = "member"
    is_dev: bool = False
    search_id: Optional[int] = None
    email: Optional[str] = None
    email_verified: bool = False


class AuthUserProfile(BaseModel):
    user_id: str
    search_id: int
    email: str
    email_verified: bool
    display_name: str
    avatar_url: Optional[str] = None
    status: str
    team_id: Optional[str] = None
    role: Optional[str] = None


class PublicUserProfile(BaseModel):
    search_id: int
    display_name: str
    avatar_url: Optional[str] = None
    status: str


class RegisterEmailRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        email = value.strip().lower()
        if "@" not in email or email.startswith("@") or email.endswith("@"):
            raise ValueError("invalid email")
        return email


class RegisterStartRequest(RegisterEmailRequest):
    delivery_mode: Optional[Literal["local"]] = None


class RegisterVerifyRequest(RegisterEmailRequest):
    code: str


class RegisterVerifyResponse(BaseModel):
    email: str
    registration_token: str
    expires_in_seconds: int


class RegisterCompleteRequest(RegisterEmailRequest):
    registration_token: str
    password: str
    confirm_password: str
    display_name: str
    avatar_url: Optional[str] = None

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        display_name = value.strip()
        if not display_name:
            raise ValueError("display_name cannot be empty")
        if len(display_name) > 80:
            raise ValueError("display_name is too long")
        return display_name


class RegisterStartResponse(BaseModel):
    email: str
    expires_in_seconds: int
    retry_after_seconds: int
    dev_code: Optional[str] = None


class AvatarUploadResponse(BaseModel):
    avatar_url: str


class LoginRequest(RegisterEmailRequest):
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class PasswordForgotRequest(RegisterEmailRequest):
    pass


class PasswordResetRequest(RegisterEmailRequest):
    code: str
    new_password: str


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    user: AuthUserProfile


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    usage_estimated: bool = False

class Message(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: Optional[str] = None
    reasoning_content: Optional[str] = None
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: List["GatewayToolCall"] = Field(default_factory=list)

class GatewayError(BaseModel):
    code: Union[ArcErrorCode, str]
    message: str

class GatewayResponse(BaseModel):
    content: str
    reasoning_content: Optional[str] = None
    token_usage: TokenUsage
    finish_reason: Optional[str] = None
    error: Optional[GatewayError] = None
    tool_calls: List["GatewayToolCall"] = Field(default_factory=list)
    tool_call: Optional["GatewayToolCall"] = None
    provider_tool_name_to_internal_id: Dict[str, str] = Field(default_factory=dict)
    internal_tool_id_to_provider_name: Dict[str, str] = Field(default_factory=dict)


class GatewayToolCall(BaseModel):
    id: str
    function_name: str
    function_arguments: str

class Action(BaseModel):
    type: ActionType
    tool_id: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None
    final_answer: Optional[str] = None

class ToolObservationError(BaseModel):
    code: str
    message: str


class ToolObservation(BaseModel):
    type: Literal["tool_observation"] = "tool_observation"
    tool_id: str
    ok: bool
    content_type: Literal["text", "json", "error"]
    content: Optional[Union[str, Dict[str, Any], List[Any]]] = None
    error: Optional[ToolObservationError] = None


class Observation(BaseModel):
    ok: bool = True
    content: Optional[Any] = None
    error: Optional[ToolObservationError] = None

class ExecutionErrorModel(BaseModel):
    error_code: str
    error_source: str
    error_message: str

    @field_validator("error_code", mode="before")
    @classmethod
    def convert_error_code_to_str(cls, v: Any) -> str:
        return str(v)

class ReactStep(BaseModel):
    step_index: int
    thought: Optional[str] = None
    action: Optional[Action] = None
    observation: Optional[Observation] = None
    state_before: ExecutionState
    state_after: ExecutionState
    error: Optional[ExecutionErrorModel] = None

class ExecutionResult(BaseModel):
    execution_id: UUID4
    final_state: ExecutionState
    steps_used: int
    termination_reason: TerminationReason
    execution_trace: List[ReactStep]
    final_answer: Optional[str] = None
    total_token_usage: TokenUsage = Field(default_factory=TokenUsage)
    status: ExecutionStatus = ExecutionStatus.PENDING
    summary: str = ""
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[ExecutionErrorModel] = None
    step_logs: List["ExecutionStepLogContract"] = Field(default_factory=list)


class ExecutionStepLogContract(BaseModel):
    execution_id: str
    step_index: int
    phase: Literal[
        "intent_classification",
        "pre_policy_gate",
        "knowledge_retrieval",
        "retrieval_policy_gate",
        "model_call",
        "tool_policy_gate",
        "tool_call",
        "observation",
        "final_answer_policy_gate",
        "final_answer",
    ]
    tool_id: Optional[str] = None
    status: Literal["success", "error"]
    payload: Dict[str, Any]
    timestamp: str


class IntentClassificationResult(BaseModel):
    intent_type: Literal[
        "DIRECT_CHAT",
        "KB_REQUIRED",
        "KB_OPTIONAL",
        "TOOL_REQUIRED",
        "TOOL_OPTIONAL",
        "HIGH_RISK_TOOL",
        "CLARIFY_REQUIRED",
        "UNSUPPORTED",
    ]
    query_subtype: Literal[
        "exact_clause",
        "policy_explanation",
        "document_summary",
        "fact_lookup",
        "tool_operation",
        "smalltalk",
    ]
    confidence: float
    matched_rules: List[str] = Field(default_factory=list)
    required_knowledge_domains: List[str] = Field(default_factory=list)
    candidate_tool_domains: List[str] = Field(default_factory=list)
    requires_citation: bool = False
    allow_direct_answer: bool = True
    requires_user_confirmation: bool = False
    missing_slots: List[str] = Field(default_factory=list)


class RetrievalPolicy(BaseModel):
    retrieval_mode: Literal["none", "optional_hybrid", "required_hybrid", "exact_clause", "document_summary"]
    limit: int = 4
    min_score: float = 0.0
    required: bool = False


class BlockedToolDecision(BaseModel):
    tool_id: str
    reason_code: str
    reason_message: str


class FinalAnswerConstraints(BaseModel):
    requires_citation: bool = False
    evidence_required: bool = False
    forbid_unverified_clause: bool = False


class PolicyGateDecision(BaseModel):
    retrieval_required: bool
    retrieval_mode: str
    direct_answer_allowed: bool
    requires_citation: bool
    allowed_tool_ids_for_turn: List[str] = Field(default_factory=list)
    blocked_tool_ids: List[BlockedToolDecision] = Field(default_factory=list)
    requires_user_confirmation: bool = False
    final_answer_constraints: FinalAnswerConstraints = Field(default_factory=FinalAnswerConstraints)


class ToolPolicyDecision(BaseModel):
    allowed: bool
    reason_code: Optional[str] = None
    reason_message: Optional[str] = None
    terminal: bool = False


class FinalAnswerPolicyDecision(BaseModel):
    accepted: bool
    violation_code: Optional[str] = None
    safe_final_answer: Optional[str] = None
    requires_retry: bool = False


class FinalAnswerContract(BaseModel):
    execution_id: str
    status: Literal["SUCCEEDED", "FAILED", "TERMINATED"]
    final_answer: str
    summary: str
    artifacts: List[Dict[str, Any]]
    error: Optional[Dict[str, Any]]

class ModelConfig(BaseModel):
    model: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None

class AgentCapabilityFlags(BaseModel):
    supports_tools: bool = True


class AgentRuntimeConfig(BaseModel):
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    context_window: Optional[int] = None
    reserved_completion_tokens: Optional[int] = None


class EmbeddingConfigRequest(BaseModel):
    provider: str = "openai_compatible"
    base_url: str = ""
    model: str = ""
    api_key: Optional[str] = None


class AgentCreateRequest(BaseModel):
    name: str
    description: str
    opening_statement: str = "你好，我是你的智能体。你可以直接告诉我想测试的问题或任务。"
    avatar_url: Optional[str] = None
    llm_provider_url: str
    llm_api_key: str
    llm_model_name: str
    embedding: Optional[EmbeddingConfigRequest] = None
    runtime_config: AgentRuntimeConfig = Field(default_factory=AgentRuntimeConfig)
    capability_flags: AgentCapabilityFlags = Field(default_factory=AgentCapabilityFlags)
    tools: List[str] = Field(default_factory=list)
    constraints: Dict[str, Any] = Field(default_factory=lambda: {"max_steps": 6})

    @field_validator("name", "description", "opening_statement", "llm_provider_url", "llm_api_key", "llm_model_name")
    @classmethod
    def validate_required_non_empty(cls, v: str) -> str:
        value = v.strip()
        if not value:
            raise ValueError("field cannot be empty")
        return value


class AgentUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    opening_statement: Optional[str] = None
    avatar_url: Optional[str] = None
    llm_provider_url: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_model_name: Optional[str] = None
    embedding: Optional[EmbeddingConfigRequest] = None
    runtime_config: Optional[AgentRuntimeConfig] = None
    capability_flags: Optional[AgentCapabilityFlags] = None
    tools: Optional[List[str]] = None
    constraints: Optional[Dict[str, Any]] = None
    archived: Optional[bool] = None

    @field_validator("name", "description", "opening_statement", "llm_provider_url", "llm_api_key", "llm_model_name")
    @classmethod
    def validate_optional_non_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        value = v.strip()
        if not value:
            raise ValueError("field cannot be empty")
        return value


class AgentRead(BaseModel):
    id: UUID4
    name: str
    description: str
    opening_statement: str = "你好，我是你的智能体。你可以直接告诉我想测试的问题或任务。"
    avatar_url: Optional[str] = None
    llm_provider_url: str
    llm_model_name: str
    runtime_config: AgentRuntimeConfig
    capability_flags: AgentCapabilityFlags
    tools: List[str]
    constraints: Dict[str, Any]
    has_api_key: bool
    archived: bool = False
    is_available: bool = True
    availability_reason: Optional[str] = None
    embedding: Optional[Dict[str, Any]] = None

class AgentCreateResponse(BaseModel):
    id: UUID4


class PublishedAgentUpsertRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    slug: Optional[str] = None
    status: Optional[Literal["ACTIVE", "DISABLED"]] = None

    @field_validator("title", "description", "slug", "status")
    @classmethod
    def validate_optional_text(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        value = v.strip()
        if not value:
            raise ValueError("field cannot be empty")
        return value


class PublishedAgentRead(BaseModel):
    id: UUID4
    agent_id: UUID4
    team_id: str
    slug: str
    title: str
    description: str
    status: Literal["ACTIVE", "DISABLED"]
    public_url: str
    created_at: str
    updated_at: str


class PublicAgentProfile(BaseModel):
    slug: str
    title: str
    description: str
    opening_statement: str
    avatar_url: Optional[str] = None


class PublicAgentSquareItem(PublicAgentProfile):
    pass


class PublicExecuteAgentRequest(BaseModel):
    input: str
    conversation_history: List["ConversationHistoryMessage"] = Field(default_factory=list)

    @field_validator("input")
    @classmethod
    def validate_input(cls, v: str) -> str:
        value = v.strip()
        if not value:
            raise ValueError("input cannot be empty")
        return value

class KnowledgeDocumentCreateRequest(BaseModel):
    title: str
    content: str

    @field_validator("title", "content")
    @classmethod
    def validate_required_text(cls, v: str) -> str:
        value = v.strip()
        if not value:
            raise ValueError("field cannot be empty")
        return value

class KnowledgeDocumentRead(BaseModel):
    id: UUID4
    agent_id: UUID4
    title: str
    content: str
    chunk_count: int = 0
    document_type: str = "other"
    source_filename: Optional[str] = None
    source_mime_type: Optional[str] = None
    source_hash: Optional[str] = None
    version_label: Optional[str] = None
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    status: str = "ACTIVE"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str
    embedding_status: str = "pending"
    embedding_provider: Optional[str] = None
    embedding_model_name: Optional[str] = None
    embedding_dimensions: Optional[int] = None
    embedding_error: Optional[str] = None
    embedded_chunk_count: int = 0

class KnowledgeSearchRequest(BaseModel):
    query: str
    limit: int = 5
    retrieval_mode: str = "optional_hybrid"
    document_type: Optional[str] = None
    article_no: Optional[str] = None
    include_near_misses: bool = True

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        value = v.strip()
        if not value:
            raise ValueError("query cannot be empty")
        return value

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        return min(max(v, 1), 10)

class KnowledgeSearchResult(BaseModel):
    document_id: UUID4
    chunk_id: UUID4
    title: str
    content: str
    score: float
    match_type: str = "keyword"
    document_type: str = "other"
    article_no: Optional[str] = None
    article_label: Optional[str] = None
    section_path: List[str] = Field(default_factory=list)
    page_no: Optional[int] = None
    citation_label: str = ""
    is_direct_evidence: bool = True

class ConversationHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        value = v.strip()
        if not value:
            raise ValueError("content cannot be empty")
        return value

class ExecuteAgentRequest(BaseModel):
    input: str
    conversation_history: List[ConversationHistoryMessage] = Field(default_factory=list)
    confirmed_tool_actions: List[Dict[str, Any]] = Field(default_factory=list)
    policy_overrides: Optional[Dict[str, Any]] = None

class ExecuteAgentResponse(BaseModel):
    execution_id: UUID4
    final_state: ExecutionState
    termination_reason: Optional[TerminationReason] = None
    steps_used: int
    request_id: str

class TeamQuotaStatusData(BaseModel):
    team_id: str
    token_limit: int
    token_used: int
    rate_limit: int
    current_usage_state: str
    quota_status: QuotaStatus

class SandboxRequest(BaseModel):
    code: str
    input_data: Dict[str, Any] = Field(default_factory=dict)

class SandboxResponse(BaseModel):
    observation: Dict[str, Any]
