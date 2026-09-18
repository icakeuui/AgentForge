from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List, Optional


class MCPServer:
    def __init__(
        self,
        command: str,
        args: List[str] | None = None,
        env_vars: Dict[str, str] | None = None,
    ) -> None:
        self.command = command
        self.args = args or []
        self.env_vars = env_vars or {}
        self.process: Optional[asyncio.subprocess.Process] = None

    async def start(self) -> None:
        env = os.environ.copy()
        env.update(self.env_vars)
        self.process = await asyncio.create_subprocess_exec(
            self.command,
            *self.args,
            env=env,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

    async def stop(self) -> None:
        if not self.process:
            return
        self.process.terminate()
        try:
            await asyncio.wait_for(self.process.wait(), timeout=5)
        except asyncio.TimeoutError:
            self.process.kill()
            await self.process.wait()

    @property
    def is_running(self) -> bool:
        return self.process is not None and self.process.returncode is None
