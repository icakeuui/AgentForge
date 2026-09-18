import sys
import os
import json
from pathlib import Path

# Add project root to PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from backend.core.sandbox.executor import PythonSandbox

def test_sandbox_basics():
    print("\n[Test] Sandbox Basics: Simple Execution")
    sandbox = PythonSandbox()
    code = "result = 1 + 1"
    res = sandbox.execute(code, {})
    print(f"Result: {res}")
    assert res["status"] == "success"
    assert res["result"] == 2

def test_sandbox_input_data():
    print("\n[Test] Sandbox Basics: Input Data")
    sandbox = PythonSandbox()
    code = "result = input_data['x'] * 10"
    res = sandbox.execute(code, {"x": 5})
    print(f"Result: {res}")
    assert res["status"] == "success"
    assert res["result"] == 50

def test_sandbox_output_pollution():
    print("\n[Test] Sandbox: Output Pollution Protection")
    sandbox = PythonSandbox()
    # Script tries to pollute stdout with non-JSON
    code = "print('DEBUG: checking internal state'); result = {'status': 'ok'}"
    res = sandbox.execute(code, {})
    print(f"Result: {res}")
    assert res["status"] == "success"
    assert res["result"]["status"] == "ok"

def test_sandbox_security_import():
    print("\n[Test] Sandbox Security: Forbidden Import (os)")
    sandbox = PythonSandbox()
    code = "import os; result = os.getcwd()"
    res = sandbox.execute(code, {})
    print(f"Result: {res}")
    assert res["status"] == "error"
    assert "not allowed" in res["error"].lower()

def test_sandbox_security_builtins(tmp_path):
    print("\n[Test] Sandbox Security: Forbidden Builtin (open)")
    sandbox = PythonSandbox()
    temp_file = tmp_path / "sandbox_test.txt"
    code = f"open({str(temp_file)!r}, 'w')"
    res = sandbox.execute(code, {})
    print(f"Result: {res}")
    assert res["status"] == "error"
    assert "name 'open' is not defined" in res["error"].lower()

def test_sandbox_security_eval():
    print("\n[Test] Sandbox Security: Forbidden Builtin (eval)")
    sandbox = PythonSandbox()
    code = "eval('1+1')"
    res = sandbox.execute(code, {})
    print(f"Result: {res}")
    assert res["status"] == "error"
    assert "name 'eval' is not defined" in res["error"].lower()

def test_sandbox_resource_cpu():
    print("\n[Test] Sandbox Resource: CPU Limit (Infinite Loop)")
    sandbox = PythonSandbox(cpu_limit=1)
    code = "while True: pass"
    res = sandbox.execute(code, {})
    print(f"Result: {res}")
    # Note: On macOS this might be 'error' via marker missing or signal.
    # On Linux it should be SIGXCPU.
    assert res["status"] == "error"
    assert "limit exceeded" in res["error"].lower() or "killed" in res["error"].lower() or "timeout" in res["error"].lower()

if False:
    try:
        test_sandbox_basics()
        test_sandbox_input_data()
        test_sandbox_output_pollution()
        test_sandbox_security_import()
        test_sandbox_security_builtins()
        test_sandbox_security_eval()
        test_sandbox_resource_cpu()
        print("\nPhase 3 Sandbox Verification: PASS")
    except Exception as e:
        print(f"\nPhase 3 Sandbox Verification: FAIL - {str(e)}")
        sys.exit(1)
