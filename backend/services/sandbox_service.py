from typing import Any, Dict
from backend.core.sandbox.executor import PythonSandbox
from backend.core.logging import logger

class PythonSandboxService:
    """
    Python Sandbox Service.
    Responsible for wrapping the low-level executor and providing the ReAct 
    compatible observation format.
    """
    
    def __init__(self):
        self.sandbox = PythonSandbox()

    def execute_python(self, code: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Python code in a secure sandbox and return observation result.
        
        This method is the primary entry point for the ReAct Engine.
        It maps the executor's internal status to the unified 'observation' contract.
        
        Args:
            code: The Python code to execute.
            input_data: Data passed to the script.
            
        Returns:
            A dictionary following the observation contract:
            { "observation": { ... result ... } }
            or
            { "observation": { "error": "error message" } }
        """
        logger.info(f"Sandbox execution request. Code length: {len(code)}")
        
        # 1. Low-level execution (Internal Contract)
        # Returns: {"status": "success", "result": ...} or {"status": "error", "error": ...}
        raw_result = self.sandbox.execute(code, input_data)
        
        # 2. Map to Observation Contract
        if raw_result.get("status") == "success":
            logger.info("Sandbox execution success.")
            return {"observation": raw_result.get("result")}
        else:
            error_msg = raw_result.get("error", "Unknown sandbox error")
            logger.error(f"Sandbox execution error: {error_msg}")
            return {"observation": {"error": error_msg}}

# Global instance
sandbox_service = PythonSandboxService()
