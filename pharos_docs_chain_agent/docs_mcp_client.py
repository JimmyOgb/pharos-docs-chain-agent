"""Official Developer Docs MCP Client for Pharos Documentation."""

import json
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional

from .models import (
    DocSearchResult,
    DocsUnavailableError
)

DEFAULT_DOCS_MCP_URL = "https://docs.pharos.xyz/~gitbook/mcp"
DEFAULT_USER_AGENT = "PharosDocChainAgent/1.0 (+https://github.com/JimmyOgb/pharos-docs-chain-agent)"


class DocsMCPClient:
    """Client for querying the official Pharos Developer Docs MCP server."""

    def __init__(self, endpoint_url: str = DEFAULT_DOCS_MCP_URL, timeout: int = 20):
        self.endpoint_url = endpoint_url
        self.timeout = timeout
        self.server_info: Optional[Dict[str, Any]] = None
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
                    raise DocsUnavailableError(f"Malformed JSON in SSE response: {e}")
        # If not formatted as SSE data, try parsing direct JSON
        try:
            return json.loads(raw_body)
        except json.JSONDecodeError:
            raise DocsUnavailableError(
                f"Failed to parse Docs MCP response as either SSE or JSON: {raw_body[:200]}"
            )

    def _post_rpc(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a JSON-RPC 2.0 call against the Docs MCP endpoint."""
        req_id = self._next_id()
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {}
        }
        encoded_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint_url,
            data=encoded_data,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "User-Agent": DEFAULT_USER_AGENT
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status = resp.status
                if status != 200:
                    raise DocsUnavailableError(
                        f"Docs MCP returned non-200 HTTP status: {status}"
                    )
                raw_text = resp.read().decode("utf-8")
                parsed = self._parse_sse_response(raw_text)
                if "error" in parsed:
                    err = parsed["error"]
                    raise DocsUnavailableError(
                        f"Docs MCP JSON-RPC error ({err.get('code')}): {err.get('message')}"
                    )
                return parsed.get("result", {})
        except urllib.error.URLError as e:
            raise DocsUnavailableError(
                f"Failed to connect to Developer Docs MCP at {self.endpoint_url}: {e}"
            )
        except TimeoutError:
            raise DocsUnavailableError(
                f"Request to Developer Docs MCP at {self.endpoint_url} timed out after {self.timeout}s"
            )

    def initialize(self, force: bool = False) -> Dict[str, Any]:
        """Negotiate protocol and discover server capabilities."""
        if self.server_info and not force:
            return {"serverInfo": self.server_info}

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

    def search_documentation(self, query: str) -> List[DocSearchResult]:
        """Search official documentation using searchDocumentation tool."""
        call_params = {
            "name": "searchDocumentation",
            "arguments": {
                "query": query
            }
        }
        result = self._post_rpc("tools/call", call_params)
        raw_content = result.get("content", [])
        search_results: List[DocSearchResult] = []

        for item in raw_content:
            text = item.get("text", "")
            title = ""
            link = ""
            body_content = ""

            # Standard GitBook MCP formatting parses Title:, Link:, and Content:
            lines = text.splitlines()
            body_lines = []
            capture_content = False

            for line in lines:
                if line.startswith("Title: "):
                    title = line[7:].strip()
                elif line.startswith("Link: "):
                    link = line[6:].strip()
                elif line.startswith("Content: "):
                    capture_content = True
                    body_lines.append(line[9:].strip())
                elif capture_content:
                    body_lines.append(line)
                else:
                    body_lines.append(line)

            body_content = "\n".join(body_lines).strip()
            if not title:
                title = "Pharos Documentation"
            if not link:
                link = "https://docs.pharos.xyz"

            search_results.append(
                DocSearchResult(
                    title=title,
                    url=link,
                    content=body_content
                )
            )

        return search_results

    def get_page(self, page_url: str) -> str:
        """Retrieve full markdown page content via getPage tool."""
        call_params = {
            "name": "getPage",
            "arguments": {
                "url": page_url
            }
        }
        result = self._post_rpc("tools/call", call_params)
        raw_content = result.get("content", [])
        page_texts = [item.get("text", "") for item in raw_content]
        return "\n\n".join(page_texts)
