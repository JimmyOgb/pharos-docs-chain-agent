"""Strict read-only safety guard and preflight interceptor."""

import re
from typing import Set

from .models import (
    SafetyViolationError,
    ChainIDMismatchError,
    ContractNotDeployedError
)

# ---------------------------------------------------------------------------
# Strict Read-Only Allowlist Policy
# ---------------------------------------------------------------------------

# The ONLY Chain MCP tools permitted by the safety policy:
SAFE_READ_ONLY_TOOLS: Set[str] = {
    "get_chain_info",
    "get_block_number",
    "get_balance",
    "get_transaction_count",
    "get_gas_price",
    "get_block",
    "get_transaction",
    "get_transaction_receipt",
    "get_code",
    "get_storage_at",
    "eth_call",
    "estimate_gas",
    "get_logs"
}

# Explicitly disallowed write-capable or state-mutating operations:
DISALLOWED_WRITE_TOOLS: Set[str] = {
    "send_raw_transaction",
    "send_transaction",
    "sign_transaction",
    "sign",
    "sign_typed_data",
    "wallet_sendTransaction",
    "eth_sendTransaction",
    "eth_sendRawTransaction"
}

REQUIRED_CHAIN_ID: int = 1672
PACIFIC_MAINNET_NAME: str = "Pharos Pacific Mainnet"


class SafetyGuard:
    """Enforces zero-gas, read-only safety invariant at the MCP client boundary."""

    @staticmethod
    def validate_tool(tool_name: str) -> None:
        """Validate that a tool belongs to the safe read-only allowlist.
        
        Raises SafetyViolationError if the tool is explicitly write-capable or unknown.
        """
        if tool_name in DISALLOWED_WRITE_TOOLS:
            raise SafetyViolationError(
                f"SAFETY POLICY REJECTION: Tool '{tool_name}' is write-capable or initiates "
                f"state changes. State mutations and gas spending are strictly prohibited."
            )
        if tool_name not in SAFE_READ_ONLY_TOOLS:
            raise SafetyViolationError(
                f"SAFETY POLICY REJECTION: Tool '{tool_name}' is not in the verified read-only "
                f"allowlist. Unknown tools are rejected by default."
            )

    @staticmethod
    def validate_chain_id(chain_id: int) -> None:
        """Assert that connected network matches Pharos Pacific Mainnet (1672)."""
        if chain_id != REQUIRED_CHAIN_ID:
            raise ChainIDMismatchError(
                f"NETWORK REJECTION: Connected chain ID is {chain_id}, but Pharos Pacific "
                f"Mainnet requires chain ID {REQUIRED_CHAIN_ID}. Aborting to protect state."
            )

    @staticmethod
    def validate_bytecode(bytecode: str, address: str) -> None:
        """Assert that deployed bytecode exists at the given contract address."""
        cleaned = bytecode.strip().lower()
        if not cleaned or cleaned in ("0x", "0x0", "0x00") or len(cleaned) <= 4:
            raise ContractNotDeployedError(
                f"CONTRACT REJECTION: Address {address} has no deployed bytecode (code is '{bytecode}'). "
                f"It is either an EOA or a contract on a different network (e.g. Atlantic Testnet)."
            )

    @staticmethod
    def validate_address(address: str) -> None:
        """Validate standard Ethereum/EVM hex address formatting."""
        if not re.match(r"^0x[a-fA-F0-9]{40}$", address):
            raise ValueError(f"Invalid Ethereum hex address format: '{address}'")
