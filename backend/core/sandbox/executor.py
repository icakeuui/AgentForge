import json
import os
import subprocess
import sys
import signal
from typing import Any, Dict
from backend.core.logging import logger

try:
    import resource
except ImportError:  # pragma: no cover - Windows does not provide resource
    resource = None

class PythonSandbox:
    """
    Python Sandbox Executor.
    NOTE: This provides 'weak isolation' using OS-level resource limits and 
    built-in Python restriction. Full isolation requires Docker/gVisor.
    
    Resource limits (resource.setrlimit) are primarily designed for Linux.
    On macOS, limits like RLIMIT_AS and RLIMIT_CPU may behave inconsistently.
    """
    
    def __init__(self, cpu_limit: int = 5, mem_limit_mb: int = 256):
        """
        Initialize the Python Sandbox with resource limits.
        
        Args:
            cpu_limit: CPU time limit in seconds.
            mem_limit_mb: Memory limit in megabytes.
        """
        self.cpu_limit = cpu_limit
        self.mem_limit = mem_limit_mb * 1024 * 1024

    def _limit_resources(self):
        """
        Set resource limits for the child process.
        Called in the child process before executing the code.
        NOTE: Best-effort on non-Linux OS.
        """
        if resource is None:
            return

        try:
            # RLIMIT_CPU: Max CPU time in seconds
            resource.setrlimit(resource.RLIMIT_CPU, (self.cpu_limit, self.cpu_limit))
        except Exception:
            pass
            
        try:
            # RLIMIT_AS: Max address space (virtual memory)
            resource.setrlimit(resource.RLIMIT_AS, (self.mem_limit, self.mem_limit))
        except Exception:
            pass
            
        try:
            # RLIMIT_FSIZE: Max file size (0 prevents writing files)
            resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
        except Exception:
            pass
            
        try:
            # RLIMIT_NOFILE: Max open file descriptors
            resource.setrlimit(resource.RLIMIT_NOFILE, (16, 16))
        except Exception:
            pass

    def execute(self, code: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Python code in a restricted subprocess.
        
        Args:
            code: The Python code string to execute.
            input_data: Data to be passed to the script as 'input_data'.
            
        Returns:
            A dictionary following the contract: {"status": "success"|"error", "result"|"error": ...}
        """
        # Allowed standard modules
        allowed_modules = ['math', 'json', 'datetime', 're', 'random', 'collections', 'itertools']
        
        # Use a unique marker to identify the final result in stdout
        RESULT_MARKER = "---SANDBOX_RESULT_JSON---"

        wrapper_code = f"""
import json
import sys

# 1. Restricted __import__
_original_import = __import__
def _restricted_import(name, globals=None, locals=None, fromlist=(), level=0):
    if name not in {allowed_modules}:
        raise ImportError(f"Module '{{name}}' is not allowed in sandbox")
    return _original_import(name, globals, locals, fromlist, level)

# 2. Build a safe __builtins__ subset
# We remove dangerous functions like open, eval, exec, compile, etc.
safe_builtins = {{
    '__import__': _restricted_import,
    'abs': abs, 'all': all, 'any': any, 'ascii': ascii, 'bin': bin, 'bool': bool,
    'bytearray': bytearray, 'bytes': bytes, 'callable': callable, 'chr': chr,
    'complex': complex, 'dict': dict, 'dir': dir, 'divmod': divmod, 'enumerate': enumerate,
    'filter': filter, 'float': float, 'format': format, 'frozenset': frozenset,
    'getattr': getattr, 'hasattr': hasattr, 'hash': hash, 'hex': hex, 'id': id,
    'int': int, 'isinstance': isinstance, 'issubclass': issubclass, 'iter': iter,
    'len': len, 'list': list, 'locals': locals, 'map': map, 'max': max, 'min': min,
    'next': next, 'object': object, 'oct': oct, 'ord': ord, 'pow': pow, 'print': print,
    'property': property, 'range': range, 'repr': repr, 'reversed': reversed,
    'round': round, 'set': set, 'setattr': setattr, 'slice': slice, 'sorted': sorted,
    'str': str, 'sum': sum, 'tuple': tuple, 'type': type, 'vars': vars, 'zip': zip,
    'Exception': Exception, 'ValueError': ValueError, 'TypeError': TypeError,
    'KeyError': KeyError, 'IndexError': IndexError, 'StopIteration': StopIteration,
    'AssertionError': AssertionError, 'ImportError': ImportError, 'NameError': NameError,
    'AttributeError': AttributeError, 'RuntimeError': RuntimeError
}}

# Inject input data
input_data = {json.dumps(input_data)}
result = None

try:
    # Prepare execution environment
    exec_globals = {{
        'input_data': input_data,
        '__builtins__': safe_builtins,
        '__name__': '__main__'
    }}
    
    # Execute user code
    exec({repr(code)}, exec_globals)
    
    # Extract 'result' variable
    result = exec_globals.get('result')
    
    # Output structured result with marker
    sys.stdout.write("\\n" + "{RESULT_MARKER}" + json.dumps({{"status": "success", "result": result}}) + "\\n")
except Exception as e:
    sys.stdout.write("\\n" + "{RESULT_MARKER}" + json.dumps({{"status": "error", "error": str(e)}}) + "\\n")

sys.exit(0)
"""
        try:
            preexec_fn = self._limit_resources if os.name == "posix" else None
            # Capture both stdout and stderr from PIPE
            process = subprocess.Popen(
                [sys.executable, "-c", wrapper_code],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                preexec_fn=preexec_fn
            )
            
            # communicate handles the pipes and waits for the process
            # Add hard timeout here (5.0s) to prevent infinite loops
            stdout, stderr = process.communicate(timeout=5.0)
            
            # Check for OS-level termination signals first
            if process.returncode < 0:
                sig = -process.returncode
                if sig == signal.SIGXCPU:
                    return {"status": "error", "error": "Sandbox execution CPU limit exceeded (OS Signal)"}
                return {"status": "error", "error": f"Process killed by OS signal {sig}"}
            
            # Parse stdout to find the marker
            if RESULT_MARKER in stdout:
                _, result_json = stdout.split(RESULT_MARKER, 1)
                try:
                    return json.loads(result_json.strip().split('\n')[0])
                except (json.JSONDecodeError, IndexError):
                    pass
            
            # If marker not found or parse failed, check returncode and stderr
            error_msg = stderr.strip() or "Unknown error (No result marker found)"
            return {"status": "error", "error": f"Sandbox execution failed: {error_msg}"}
            
        except subprocess.TimeoutExpired:
            process.kill()
            return {"status": "error", "error": "Execution timeout after 5.0 seconds"}
        except Exception as e:
            logger.error(f"Sandbox execution fatal error: {str(e)}")
            return {"status": "error", "error": f"Sandbox execution fatal error: {str(e)}"}
