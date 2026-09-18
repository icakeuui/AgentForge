import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Type
import jsonschema
from jsonschema import validate, ValidationError

from backend.core.logging import logger, set_request_id
from backend.models.tool import BaseTool, ToolResponse, ToolError, ToolSuccessResponse, ToolFailureResponse
from backend.models.tool_runtime_errors import ToolRuntimeErrorCode, ToolRegistrationError

class ToolRegistry:
    """
    Registry for tools.
    Singleton pattern, registration is locked after startup.
    """
    _instance = None
    _tools: Dict[str, BaseTool] = {}
    _locked: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ToolRegistry, cls).__new__(cls)
        return cls._instance

    @classmethod
    def register(cls, tool: BaseTool):
        """
        Register a tool instance.
        """
        if cls._locked:
            logger.error(f"Cannot register tool {tool.definition.name}: Registry is locked.")
            raise ToolRegistrationError("Registry is locked after startup.")
        
        if tool.definition.name in cls._tools:
            logger.error(f"Cannot register tool {tool.definition.name}: Tool already exists.")
            raise ToolRegistrationError(f"Tool {tool.definition.name} already exists.")
        
        cls._tools[tool.definition.name] = tool
        logger.info(f"Tool registered: {tool.definition.name}")

    @classmethod
    def get_tool(cls, name: str) -> Optional[BaseTool]:
        """
        Retrieve a tool by name.
        """
        return cls._tools.get(name)

    @classmethod
    def lock(cls):
        """
        Lock the registry to prevent further registrations.
        """
        cls._locked = True
        logger.info("ToolRegistry locked.")

    @classmethod
    def list_tools(cls) -> Dict[str, Any]:
        """
        List all registered tool definitions.
        """
        return {name: tool.definition.model_dump() for name, tool in cls._tools.items()}

class ToolExecutor:
    """
    Main execution engine for tools.
    Handles validation, logging, and error isolation.
    """

    @staticmethod
    def _normalize_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively ensures additionalProperties=False for all object nodes
        unless explicitly specified.
        """
        if not isinstance(schema, dict):
            return schema

        new_schema = schema.copy()
        
        if new_schema.get("type") == "object":
            if "additionalProperties" not in new_schema:
                new_schema["additionalProperties"] = False
            
            if "properties" in new_schema:
                new_schema["properties"] = {
                    k: ToolExecutor._normalize_schema(v) 
                    for k, v in new_schema["properties"].items()
                }

        # Recursive for items in array
        if new_schema.get("type") == "array" and "items" in new_schema:
            new_schema["items"] = ToolExecutor._normalize_schema(new_schema["items"])

        # Recursive for combinators
        for combinator in ["anyOf", "oneOf", "allOf"]:
            if combinator in new_schema:
                new_schema[combinator] = [
                    ToolExecutor._normalize_schema(s) for s in new_schema[combinator]
                ]

        return new_schema

    @staticmethod
    def _validate_schema(data: Dict[str, Any], schema: Dict[str, Any], stage: str) -> None:
        """
        Helper for JSON Schema validation.
        Uses normalized schema.
        """
        normalized = ToolExecutor._normalize_schema(schema)
        try:
            validate(instance=data, schema=normalized)
        except ValidationError as e:
            logger.warning(f"Schema validation failed at {stage}: {str(e)}")
            raise

    @staticmethod
    def _extract_sandbox_error_message(output: Dict[str, Any]) -> Optional[str]:
        observation = output.get("observation")
        if isinstance(observation, dict) and "error" in observation:
            return str(observation.get("error"))
        if output.get("status") == "error" and "error" in output:
            return str(output.get("error"))
        return None

    @classmethod
    def execute(cls, name: str, input_data: Dict[str, Any], request_id: str) -> ToolResponse:
        """
        Standardized tool execution flow.
        """
        start_time_float = time.time()
        start_timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace("+00:00", "Z")
        set_request_id(request_id)
        
        # 1. Start log
        logger.bind(
            event="tool_execution_start",
            request_id=request_id,
            tool_name=name,
            input=input_data,
            timestamp=start_timestamp
        ).info(f"Starting execution for tool: {name}")

        try:
            # 2. Find tool
            registry = ToolRegistry()
            tool = registry.get_tool(name)
            if not tool:
                return cls._create_error_response(
                    ToolRuntimeErrorCode.TOOL_NOT_FOUND, 
                    f"Tool not found: {name}", 
                    name, request_id, start_time_float
                )

            # 3. Validate input
            try:
                cls._validate_schema(input_data, tool.definition.input_schema, "input")
            except ValidationError as e:
                return cls._create_error_response(
                    ToolRuntimeErrorCode.INVALID_INPUT, 
                    f"Invalid input schema: {str(e)}", 
                    name, request_id, start_time_float
                )

            # 4. Execute business logic
            try:
                output = tool.execute(input_data)
            except Exception as e:
                logger.exception(f"Tool execution failed: {name}")
                return cls._create_error_response(
                    ToolRuntimeErrorCode.TOOL_EXECUTION_ERROR, 
                    f"Tool execution failed: {str(e)}", 
                    name, request_id, start_time_float
                )

            # 5. Check if output is dict and validate output schema
            if not isinstance(output, dict):
                return cls._create_error_response(
                    ToolRuntimeErrorCode.INVALID_OUTPUT,
                    f"Tool output must be a dict, got {type(output).__name__}",
                    name, request_id, start_time_float
                )

            sandbox_error_message = cls._extract_sandbox_error_message(output)
            if sandbox_error_message is not None:
                return cls._create_error_response(
                    ToolRuntimeErrorCode.SANDBOX_ERROR,
                    f"Sandbox execution failed: {sandbox_error_message}",
                    name, request_id, start_time_float
                )

            try:
                cls._validate_schema(output, tool.definition.output_schema, "output")
            except ValidationError as e:
                return cls._create_error_response(
                    ToolRuntimeErrorCode.INVALID_OUTPUT, 
                    f"Invalid output schema: {str(e)}", 
                    name, request_id, start_time_float
                )

            # 6. Success end log
            end_timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace("+00:00", "Z")
            duration_ms = int((time.time() - start_time_float) * 1000)
            logger.bind(
                event="tool_execution_end",
                request_id=request_id,
                tool_name=name,
                success=True,
                output=output,
                duration_ms=duration_ms,
                timestamp=end_timestamp
            ).info(f"Execution successful for tool: {name}")

            return ToolSuccessResponse(data=output)

        except Exception as e:
            # 7. Unexpected runtime errors
            logger.exception(f"Internal runtime error during tool execution: {name}")
            return cls._create_error_response(
                ToolRuntimeErrorCode.INTERNAL_RUNTIME_ERROR, 
                f"Internal runtime error: {str(e)}", 
                name, request_id, start_time_float
            )

    @classmethod
    def _create_error_response(
        cls, code: ToolRuntimeErrorCode, message: str, tool_name: str, request_id: str, start_time_float: float
    ) -> ToolFailureResponse:
        """
        Helper to create standardized error response and log the failure.
        """
        end_timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace("+00:00", "Z")
        duration_ms = int((time.time() - start_time_float) * 1000)
        error_obj = ToolError(code=code, message=message)
        
        logger.bind(
            event="tool_execution_end",
            request_id=request_id,
            tool_name=tool_name,
            success=False,
            error=error_obj.model_dump(),
            duration_ms=duration_ms,
            timestamp=end_timestamp
        ).error(f"Execution failed for tool: {tool_name} | Code: {code}")
        
        return ToolFailureResponse(error=error_obj)
