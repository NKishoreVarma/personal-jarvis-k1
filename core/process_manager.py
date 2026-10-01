"""
Process Manager for MARK XLVIII / JARVIS.
Handles non-blocking background server execution, output streaming,
regex port detection, and HTTP localhost readiness verification.
"""

from __future__ import annotations

import asyncio
import os
import re
import signal
import socket
import time
import urllib.error
import urllib.request
import uuid
from typing import Any, Dict, List, Optional

PORT_PATTERNS = [
    re.compile(r"localhost:(\d{2,5})", re.IGNORECASE),
    re.compile(r"127\.0\.0\.1:(\d{2,5})", re.IGNORECASE),
    re.compile(r"0\.0\.0\.0:(\d{2,5})", re.IGNORECASE),
    re.compile(r"port\s+(\d{2,5})", re.IGNORECASE),
    re.compile(r"listening\s+on\s+(?:http://[^\s:]+:)?(\d{2,5})", re.IGNORECASE),
    re.compile(r"http://[a-zA-Z0-9\.\-_]+:(\d{2,5})", re.IGNORECASE),
]


class ProcessManager:
    """
    Manages non-blocking background processes started by JARVIS.
    """

    SERVER_START_TIMEOUT = 30.0  # seconds

    def __init__(self):
        self._processes: Dict[str, Dict[str, Any]] = {}

    def detect_port(self, text: str) -> Optional[int]:
        """Scans process log text for listening port numbers."""
        for pattern in PORT_PATTERNS:
            match = pattern.search(text)
            if match:
                try:
                    port = int(match.group(1))
                    if 80 <= port <= 65535:
                        return port
                except ValueError:
                    continue
        return None

    def verify_port_open(self, port: int, host: str = "127.0.0.1", timeout: float = 1.0) -> bool:
        """Checks if a TCP port is listening on localhost."""
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False

    def verify_http(self, port: int, host: str = "127.0.0.1", path: str = "/", timeout: float = 2.0) -> bool:
        """Verifies HTTP response from localhost:port."""
        url = f"http://{host}:{port}{path}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "JARVIS-HealthCheck/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.status in (200, 201, 204, 301, 302, 304, 404)
        except urllib.error.HTTPError as he:
            # Server responded with an HTTP status code (even 404/500 means server is up and listening)
            return True
        except Exception:
            # Fallback to TCP port check
            return self.verify_port_open(port, host=host, timeout=timeout)

    async def start_process(
        self,
        command: List[str],
        cwd: str,
        project_name: str,
        timeout: float = SERVER_START_TIMEOUT,
    ) -> Dict[str, Any]:
        """
        Starts a background process asynchronously with non-blocking stdout/stderr capture.
        """
        process_id = f"proc_{uuid.uuid4().hex[:8]}"
        try:
            proc = await asyncio.create_subprocess_exec(
                *command,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            record: Dict[str, Any] = {
                "process_id": process_id,
                "project": project_name,
                "pid": proc.pid,
                "command": command,
                "working_directory": cwd,
                "status": "STARTING",
                "detected_port": None,
                "stdout_lines": [],
                "stderr_lines": [],
                "started_at": time.monotonic(),
                "_proc": proc,
            }
            self._processes[process_id] = record

            # Launch background output reader
            asyncio.create_task(self._stream_output(process_id, proc))

            print(f"[PROCESS] Started '{project_name}' (pid={proc.pid}, id={process_id})")
            return {
                "success": True,
                "process_id": process_id,
                "pid": proc.pid,
                "status": "STARTING",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to start process: {e}",
            }

    async def _stream_output(self, process_id: str, proc: asyncio.subprocess.Process) -> None:
        """Stream stdout and stderr lines asynchronously."""
        record = self._processes.get(process_id)
        if not record:
            return

        async def read_stream(stream, line_list):
            while not stream.at_eof():
                try:
                    line_bytes = await stream.readline()
                    if not line_bytes:
                        break
                    line = line_bytes.decode("utf-8", errors="replace").rstrip()
                    line_list.append(line)
                    if len(line_list) > 200:
                        line_list.pop(0)

                    # Check for port announcement
                    if record["detected_port"] is None:
                        port = self.detect_port(line)
                        if port:
                            record["detected_port"] = port
                            record["status"] = "RUNNING"
                            print(f"[PROCESS] Detected port {port} for {record['project']}")
                except Exception:
                    break

        await asyncio.gather(
            read_stream(proc.stdout, record["stdout_lines"]),
            read_stream(proc.stderr, record["stderr_lines"]),
        )

        returncode = await proc.wait()
        record["status"] = "STOPPED" if returncode == 0 else "FAILED"
        record["returncode"] = returncode
        print(f"[PROCESS] Process {process_id} finished with code {returncode}")

    def stop_process(self, process_id: str) -> bool:
        """Stops a background process started by JARVIS."""
        record = self._processes.get(process_id)
        if not record:
            return False

        proc: Optional[asyncio.subprocess.Process] = record.get("_proc")
        if proc and proc.returncode is None:
            try:
                proc.send_signal(signal.SIGTERM)
                record["status"] = "STOPPED"
                print(f"[PROCESS] Sent SIGTERM to process {process_id} (pid={proc.pid})")
                return True
            except Exception as e:
                try:
                    proc.kill()
                    record["status"] = "STOPPED"
                    return True
                except Exception:
                    return False
        return True

    def get_process_status(self, process_id: str) -> Optional[Dict[str, Any]]:
        """Returns public status dictionary for a process."""
        record = self._processes.get(process_id)
        if not record:
            return None
        return {
            "process_id": record["process_id"],
            "project": record["project"],
            "pid": record["pid"],
            "command": record["command"],
            "working_directory": record["working_directory"],
            "status": record["status"],
            "detected_port": record["detected_port"],
            "stdout_tail": record["stdout_lines"][-10:],
            "stderr_tail": record["stderr_lines"][-10:],
        }

    def list_active_processes(self) -> List[Dict[str, Any]]:
        return [
            self.get_process_status(pid)
            for pid, r in self._processes.items()
            if r["status"] in ("STARTING", "RUNNING")
        ]

    def list_processes(self) -> List[Dict[str, Any]]:
        return [
            self.get_process_status(pid)
            for pid in self._processes
            if self.get_process_status(pid) is not None
        ]

    def reset(self) -> None:
        """Stops all running processes and cleans state."""
        for pid in list(self._processes.keys()):
            self.stop_process(pid)
        self._processes.clear()


# Global singleton
process_manager = ProcessManager()
