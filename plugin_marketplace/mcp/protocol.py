from __future__ import annotations

import itertools
from typing import Any, Dict


class MCPProtocol:
    def __init__(self) -> None:
        self._counter = itertools.count(1)

    def request(self, method: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": next(self._counter),
            "method": method,
        }
        if params is not None:
            payload["params"] = params
        return payload
