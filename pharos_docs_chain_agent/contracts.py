"""Canonical contracts and verified function registry for Pharos Pacific Mainnet."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from .models import ABIEncodingError


@dataclass
class FunctionSpec:
    """Specification of a verified canonical contract function."""
    name: str
    signature: str
    selector: str
    input_types: List[str]
    return_type: str
    docs_description: str
    decoder: Callable[[str], Any]
    abi_source: str
    verification_notes: str


@dataclass
class ContractSpec:
    """Specification of a verified canonical contract on Pharos Pacific Mainnet."""
    name: str
    address: str
    docs_url: str
    docs_section: str
    functions: Dict[str, FunctionSpec]


# ---------------------------------------------------------------------------
# Decoders for EVM Return Types
# ---------------------------------------------------------------------------

def decode_uint256(raw_hex: str) -> int:
    """Decode raw 32-byte EVM return data into a Python integer."""
    cleaned = raw_hex.strip()
    if cleaned.startswith("0x"):
        cleaned = cleaned[2:]
    if not cleaned:
        raise ABIEncodingError("Cannot decode uint256 from empty hex return data")
    try:
        return int(cleaned, 16)
    except ValueError as e:
        raise ABIEncodingError(f"Failed to decode uint256 from '{raw_hex}': {e}")


def decode_timestamp(raw_hex: str) -> Dict[str, Any]:
    """Decode raw uint256 into epoch seconds and formatted ISO-8601 UTC string."""
    epoch_seconds = decode_uint256(raw_hex)
    try:
        dt = datetime.fromtimestamp(epoch_seconds, tz=timezone.utc)
        iso_str = dt.isoformat()
    except (OverflowError, OSError, ValueError):
        iso_str = "Invalid/Out of range timestamp"
    return {
        "epoch_seconds": epoch_seconds,
        "iso_utc": iso_str
    }


def decode_bytes32(raw_hex: str) -> str:
    """Decode raw 32-byte hex string, ensuring proper 0x prefix and length."""
    cleaned = raw_hex.strip().lower()
    if not cleaned.startswith("0x"):
        cleaned = "0x" + cleaned
    if len(cleaned) != 66:  # 0x + 64 hex chars
        raise ABIEncodingError(
            f"Expected 32-byte hex string (66 chars with 0x), got {len(cleaned)} chars: '{raw_hex}'"
        )
    return cleaned


# ---------------------------------------------------------------------------
# Canonical Contract Registry
# ---------------------------------------------------------------------------

CANONICAL_CONTRACTS: Dict[str, ContractSpec] = {
    "MultiCall3": ContractSpec(
        name="MultiCall3",
        address="0xcA11bde05977b3631167028862bE2a173976CA11",
        docs_url="https://docs.pharos.xyz/getting-started/canonical-contracts",
        docs_section="Canonical Contracts — MultiCall3",
        functions={
            "getCurrentBlockTimestamp": FunctionSpec(
                name="getCurrentBlockTimestamp",
                signature="getCurrentBlockTimestamp()",
                selector="0x0f28c97d",
                input_types=[],
                return_type="uint256",
                docs_description=(
                    "Returns the current block's timestamp as recorded by the EVM clock. "
                    "Allows client applications and smart contracts to obtain consistent timestamp data."
                ),
                decoder=decode_timestamp,
                abi_source="MultiCall3 Canonical Specification (documented in Pharos Canonical Contracts)",
                verification_notes="Selector 0x0f28c97d verified against keccak256('getCurrentBlockTimestamp()')."
            ),
            "getBlockNumber": FunctionSpec(
                name="getBlockNumber",
                signature="getBlockNumber()",
                selector="0x42cbb15c",
                input_types=[],
                return_type="uint256",
                docs_description=(
                    "Returns the current block number on the Pharos Pacific Mainnet blockchain. "
                    "Facilitates block height synchronization in bundled read transactions."
                ),
                decoder=decode_uint256,
                abi_source="MultiCall3 Canonical Specification (documented in Pharos Canonical Contracts)",
                verification_notes="Selector 0x42cbb15c verified against keccak256('getBlockNumber()')."
            )
        }
    ),
    "Permit2": ContractSpec(
        name="Permit2",
        address="0x000000000022D473030F116dDEE9F6B43aC78BA3",
        docs_url="https://docs.pharos.xyz/getting-started/canonical-contracts",
        docs_section="Canonical Contracts — Permit2",
        functions={
            "DOMAIN_SEPARATOR": FunctionSpec(
                name="DOMAIN_SEPARATOR",
                signature="DOMAIN_SEPARATOR()",
                selector="0x3644e515",
                input_types=[],
                return_type="bytes32",
                docs_description=(
                    "Returns the EIP-712 domain separator hash used by Permit2 to protect off-chain "
                    "signatures against replay attacks across different chains and applications."
                ),
                decoder=decode_bytes32,
                abi_source="Uniswap Permit2 Specification (documented in Pharos Canonical Contracts)",
                verification_notes="Selector 0x3644e515 verified against keccak256('DOMAIN_SEPARATOR()')."
            )
        }
    )
}


# ---------------------------------------------------------------------------
# Registry Query Helpers
# ---------------------------------------------------------------------------

def get_canonical_contract(name: str) -> Optional[ContractSpec]:
    """Retrieve contract specification by case-insensitive name."""
    clean_name = name.strip().lower()
    for key, spec in CANONICAL_CONTRACTS.items():
        if key.lower() == clean_name:
            return spec
    return None


def get_canonical_function(contract_name: str, function_name: str) -> Optional[FunctionSpec]:
    """Retrieve function specification by case-insensitive contract and function name."""
    contract = get_canonical_contract(contract_name)
    if not contract:
        return None
    # Normalize function name (remove trailing parentheses if present)
    clean_fn = function_name.strip().split("(")[0].lower()
    for fn_key, fn_spec in contract.functions.items():
        if fn_key.lower() == clean_fn:
            return fn_spec
    return None


def list_supported_targets() -> List[Dict[str, Any]]:
    """Return an overview list of supported canonical contracts and their verified functions."""
    targets = []
    for c_name, c_spec in CANONICAL_CONTRACTS.items():
        for f_name, f_spec in c_spec.functions.items():
            targets.append({
                "contract": c_name,
                "address": c_spec.address,
                "function": f_spec.name,
                "signature": f_spec.signature,
                "selector": f_spec.selector,
                "return_type": f_spec.return_type,
                "docs_url": c_spec.docs_url
            })
    return targets
