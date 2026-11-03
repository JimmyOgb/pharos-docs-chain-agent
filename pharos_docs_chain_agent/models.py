"""Data models and exception hierarchy for Pharos Doc-Chain Action Agent."""

from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Typed Exception Hierarchy (Fail-Closed)
# ---------------------------------------------------------------------------

class DocChainBaseError(Exception):
    """Base exception for all Pharos Doc-Chain Action Agent errors."""
    pass


class DocsUnavailableError(DocChainBaseError):
    """Raised when Developer Docs MCP endpoint cannot be reached or fails negotiation."""
    pass


class DocumentationNotFoundError(DocChainBaseError):
    """Raised when Docs MCP search returns no relevant documentation for the target."""
    pass


class ChainUnavailableError(DocChainBaseError):
    """Raised when hosted Chain MCP endpoint cannot be reached or rejects session."""
    pass


class ChainIDMismatchError(DocChainBaseError):
    """Raised when Chain MCP connects to a network other than Pacific Mainnet (1672)."""
    pass


class ContractNotDeployedError(DocChainBaseError):
    """Raised when the target contract address has 0 bytes of bytecode on-chain."""
    pass


class SafetyViolationError(DocChainBaseError):
    """Raised when an operation attempts a write-capable tool or unknown tool."""
    pass


class ChainRevertError(DocChainBaseError):
    """Raised when read-only eth_call reverts or returns empty calldata."""
    pass


class ABIEncodingError(DocChainBaseError):
    """Raised when raw return data cannot be decoded using the verified ABI."""
    pass


class FunctionNotDocumentedError(DocChainBaseError):
    """Raised when requested function is not documented in official Pharos docs."""
    pass


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class DocSearchResult:
    """A search result item returned by Developer Docs MCP searchDocumentation."""
    title: str
    url: str
    content: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DocExcerpt:
    """Structured documentation findings extracted from Docs MCP."""
    contract_name: str
    function_name: str
    description: str
    parameters: str
    return_type: str
    source_url: str
    section_title: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ChainExecutionResult:
    """Result of a live read-only on-chain execution via hosted Chain MCP."""
    network: str
    chain_id: int
    contract_address: str
    function_name: str
    selector: str
    call_method: str
    raw_hex: str
    decoded_value: Any
    block_number: Optional[int] = None
    timestamp: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class InterpretationResult:
    """Contextual synthesis between documentation facts and live blockchain data."""
    explanation_summary: str
    live_value_summary: str
    contextual_meaning: str
    limitations: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProvenanceRecord:
    """Full cryptographic and protocol provenance for auditing and reproducibility."""
    docs_tool_used: str
    docs_source_url: str
    chain_mcp_tool_used: str
    mcp_session_id: Optional[str]
    abi_source: str
    verification_status: str
    recorded_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CompositionReport:
    """Complete end-to-end composition artifact combining docs, chain, and interpretation."""
    contract_name: str
    function_name: str
    doc_excerpt: Optional[DocExcerpt]
    execution_result: Optional[ChainExecutionResult]
    interpretation: Optional[InterpretationResult]
    provenance: Optional[ProvenanceRecord]
    success: bool
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_name": self.contract_name,
            "function_name": self.function_name,
            "success": self.success,
            "error_message": self.error_message,
            "doc_excerpt": self.doc_excerpt.to_dict() if self.doc_excerpt else None,
            "execution_result": self.execution_result.to_dict() if self.execution_result else None,
            "interpretation": self.interpretation.to_dict() if self.interpretation else None,
            "provenance": self.provenance.to_dict() if self.provenance else None
        }
