"""Official Hosted Chain MCP Client for Pharos Pacific Mainnet."""

import json
import urllib.request
import urllib.error
from typing import Any, Dict, Optional

from .models import (
    ChainUnavailableError,
    ChainRevertError
)
from .safety import SafetyGuard

DEFAULT_CHAIN_MCP_URL = "https://mcp.pharos.xyz/mcp"
DEFAULT_USER_AGENT = "PharosDocChainAgent/1.0 (+https://github.com/JimmyOgb/pharos-docs-chain-agent)"


class ChainMCPClient:
    """Client for executing read-only contract queries via the hosted Pharos Chain MCP server."""

    def __init__(self, endpoint_url: str = DEFAULT_CHAIN_MCP_URL, timeout: int = 30):
        self.endpoint_url = endpoint_url
        self.timeout = timeout
        self.session_id: Optional[str] = None
        self.server_info: Optional[Dict[str, Any]] = None
        self.chain_info: Optional[Dict[str, Any]] = None
        self._request_id = 0

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _parse_sse_response(self, raw_body: str) -> Dict[str, Any]:
        """Extract JSON-RPC payload from SSE event stream."""
        for line in raw_body.splitlines():
            line = line.strip()
            if line.startswith("data: "):
                try:
                    return json.loads(line[6:])
                except json.JSONDecodeError as e:
                    raise ChainUnavailableError(f"Malformed JSON in Chain MCP SSE stream: {e}")
        try:
            return json.loads(raw_body)
        except json.JSONDecodeError:
            raise ChainUnavailableError(
                f"Failed to parse Chain MCP response as either SSE or JSON: {raw_body[:200]}"
            )

    def _post_rpc(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a JSON-RPC 2.0 call with session header against Chain MCP."""
        req_id = self._next_id()
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {}
        }
        encoded_data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "User-Agent": DEFAULT_USER_AGENT
        }
        if self.session_id:
            headers["mcp-session-id"] = self.session_id

        req = urllib.request.Request(
            self.endpoint_url,
            data=encoded_data,
            headers=headers,
            method="POST"
        )

        for attempt in range(2):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    new_session = resp.headers.get("mcp-session-id")
                    if new_session:
                        self.session_id = new_session

                    status = resp.status
                    if status != 200:
                        raise ChainUnavailableError(
                            f"Chain MCP returned non-200 HTTP status: {status}"
                        )
                    raw_text = resp.read().decode("utf-8")
                    parsed = self._parse_sse_response(raw_text)
                    if "error" in parsed:
                        err = parsed["error"]
                        raise ChainUnavailableError(
                            f"Chain MCP JSON-RPC error ({err.get('code')}): {err.get('message')}"
                        )
                    return parsed.get("result", {})
            except (urllib.error.URLError, TimeoutError) as e:
                if attempt == 0:
                    continue
                raise ChainUnavailableError(
                    f"Failed to connect to Chain MCP at {self.endpoint_url}: {e}"
                )

    def initialize(self, force: bool = False) -> Dict[str, Any]:
        """Establish session and negotiate protocol with Chain MCP."""
        if self.session_id and not force:
            return {"serverInfo": self.server_info or {}}

        # initialize creates a new session; must clear existing session header
        self.session_id = None
        result = self._post_rpc(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "pharos-docs-chain-agent",
                    "version": "0.1.0"
                }
            }
        )
        self.server_info = result.get("serverInfo", {})
        return result

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Invoke a tool through Chain MCP, strictly governed by SafetyGuard allowlist."""
        # Enforce safety allowlist BEFORE network invocation
        SafetyGuard.validate_tool(tool_name)

        params = {
            "name": tool_name,
            "arguments": arguments
        }
        result = self._post_rpc("tools/call", params)
        content = result.get("content", [])
        if not content:
            return None

        # Return text payload
        raw_text = content[0].get("text", "")
        # Parse nested JSON string if applicable
        try:
            parsed_json = json.loads(raw_text)
            return parsed_json
        except (json.JSONDecodeError, TypeError):
            return raw_text

    def get_chain_info(self) -> Dict[str, Any]:
        """Retrieve connected chain information and validate against Pacific Mainnet (1672)."""
        res = self.call_tool("get_chain_info", {})
        if not isinstance(res, dict):
            raise ChainUnavailableError(f"Unexpected get_chain_info format: {res}")
        chain_id = res.get("chainId")
        if chain_id is None:
            raise ChainUnavailableError("Chain MCP did not return chainId")
        # Validate chain ID
        SafetyGuard.validate_chain_id(int(chain_id))
        self.chain_info = res
        return res

    def get_code(self, address: str) -> str:
        """Fetch bytecode for an address and preflight validate presence."""
        SafetyGuard.validate_address(address)
        res = self.call_tool("get_code", {"address": address})
        bytecode = ""
        if isinstance(res, dict):
            bytecode = res.get("code", "")
        elif isinstance(res, str):
            bytecode = res
        # Validate presence of deployed bytecode
        SafetyGuard.validate_bytecode(bytecode, address)
        return bytecode

    def eth_call(self, to_address: str, calldata: str) -> str:
        """Execute read-only contract call using eth_call."""
        SafetyGuard.validate_address(to_address)
        res = self.call_tool(
            "eth_call",
            {
                "transaction": {
                    "to": to_address,
                    "data": calldata
                }
            }
        )
        raw_hex = ""
        if isinstance(res, dict):
            raw_hex = res.get("result", "")
        elif isinstance(res, str):
            raw_hex = res

        if not raw_hex or raw_hex == "0x":
            raise ChainRevertError(
                f"eth_call to {to_address} with data {calldata} reverted or returned empty '0x'"
            )
        return raw_hex
