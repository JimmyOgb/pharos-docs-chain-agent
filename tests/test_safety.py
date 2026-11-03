"""Safety and security policy unit tests."""

import pytest
from pharos_docs_chain_agent.safety import (
    SafetyGuard,
    SAFE_READ_ONLY_TOOLS,
    DISALLOWED_WRITE_TOOLS
)
from pharos_docs_chain_agent.models import (
    SafetyViolationError,
    ChainIDMismatchError,
    ContractNotDeployedError
)


def test_safe_tools_allowed():
    """Verify all permitted read-only tools pass the safety guard."""
    for tool in SAFE_READ_ONLY_TOOLS:
        # Should not raise
        SafetyGuard.validate_tool(tool)


def test_disallowed_write_tools_rejected():
    """Verify write-capable and signing tools are strictly rejected."""
    for tool in DISALLOWED_WRITE_TOOLS:
        with pytest.raises(SafetyViolationError) as exc_info:
            SafetyGuard.validate_tool(tool)
        assert "SAFETY POLICY REJECTION" in str(exc_info.value)
        assert tool in str(exc_info.value)


def test_unknown_tools_rejected():
    """Verify arbitrary or unknown tools are rejected by default."""
    unknown_tools = ["custom_eval", "deploy_contract", "exec_cmd", "transfer_funds", ""]
    for tool in unknown_tools:
        with pytest.raises(SafetyViolationError) as exc_info:
            SafetyGuard.validate_tool(tool)
        assert "SAFETY POLICY REJECTION" in str(exc_info.value)


def test_chain_id_validation():
    """Verify only Pacific Mainnet chain ID 1672 is accepted."""
    # Accepted
    SafetyGuard.validate_chain_id(1672)

    # Rejected
    invalid_chains = [1, 5, 11155111, 688688, 137, 0]
    for cid in invalid_chains:
        with pytest.raises(ChainIDMismatchError) as exc_info:
            SafetyGuard.validate_chain_id(cid)
        assert "1672" in str(exc_info.value)


def test_bytecode_validation():
    """Verify contract bytecode presence is strictly checked."""
    # Accepted: deployed code
    SafetyGuard.validate_bytecode("0x608060405234801561001057600080fd5b50", "0xcA11bde05977b3631167028862bE2a173976CA11")

    # Rejected: empty code
    empty_codes = ["0x", "", "  0x  ", "0x00"]
    for code in empty_codes:
        with pytest.raises(ContractNotDeployedError) as exc_info:
            SafetyGuard.validate_bytecode(code, "0x76A4De34D608AEf6003117565868E079d20c57F9")
        assert "no deployed bytecode" in str(exc_info.value)


def test_address_validation():
    """Verify standard EVM hex address formatting."""
    # Accepted
    SafetyGuard.validate_address("0xcA11bde05977b3631167028862bE2a173976CA11")
    SafetyGuard.validate_address("0x000000000022D473030F116dDEE9F6B43aC78BA3")

    # Rejected
    invalid_addrs = [
        "0x123",
        "cA11bde05977b3631167028862bE2a173976CA11",
        "0xZZ11bde05977b3631167028862bE2a173976CA11",
        "",
        "not_an_address"
    ]
    for addr in invalid_addrs:
        with pytest.raises(ValueError):
            SafetyGuard.validate_address(addr)
