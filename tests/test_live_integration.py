"""Genuine live integration tests against official Docs MCP and hosted Chain MCP."""

import pytest

from pharos_docs_chain_agent.composer import DocChainComposer
from pharos_docs_chain_agent.docs_mcp_client import DocsMCPClient
from pharos_docs_chain_agent.chain_mcp_client import ChainMCPClient
from pharos_docs_chain_agent.models import ContractNotDeployedError


@pytest.fixture(scope="module")
def live_composer():
    """Create live composer with real MCP endpoints."""
    docs = DocsMCPClient()
    chain = ChainMCPClient()
    return DocChainComposer(docs_client=docs, chain_client=chain)


def test_live_docs_mcp_direct():
    """Verify Developer Docs MCP live connection and searchDocumentation."""
    client = DocsMCPClient()
    init_res = client.initialize()
    assert "protocolVersion" in init_res

    results = client.search_documentation("Canonical Contracts")
    assert len(results) > 0
    # Must contain links to official docs
    assert any("docs.pharos.xyz" in r.url for r in results)


def test_live_chain_mcp_direct():
    """Verify hosted Chain MCP live connection and Pacific Mainnet (1672) parameters."""
    client = ChainMCPClient()
    init_res = client.initialize()
    assert "serverInfo" in init_res
    assert client.session_id is not None

    chain_info = client.get_chain_info()
    assert chain_info.get("chainId") == 1672
    assert chain_info.get("nativeSymbol") == "PROS"
    assert chain_info.get("chainIdMatches") is True


def test_live_compose_multicall3_timestamp(live_composer):
    """Live Test 1: MultiCall3.getCurrentBlockTimestamp() genuine composition."""
    report = live_composer.inspect_function("MultiCall3", "getCurrentBlockTimestamp")
    assert report.success is True, f"Composition failed: {report.error_message}"

    # Documentation validation
    assert report.doc_excerpt is not None
    assert "canonical-contracts" in report.doc_excerpt.source_url

    # Chain execution validation
    assert report.execution_result is not None
    assert report.execution_result.chain_id == 1672
    assert report.execution_result.function_name == "getCurrentBlockTimestamp"
    assert report.execution_result.selector == "0x0f28c97d"

    # Value sanity check: epoch should be recent (greater than 1700000000)
    epoch = report.execution_result.decoded_value["epoch_seconds"]
    assert epoch > 1700000000
    assert "T" in report.execution_result.decoded_value["iso_utc"]

    # Provenance
    assert report.provenance is not None
    assert report.provenance.verification_status == "LIVE_VERIFIED_GENUINE"


def test_live_compose_multicall3_block_number(live_composer):
    """Live Test 2: MultiCall3.getBlockNumber() genuine composition."""
    report = live_composer.inspect_function("MultiCall3", "getBlockNumber")
    assert report.success is True, f"Composition failed: {report.error_message}"

    assert report.doc_excerpt is not None
    assert report.execution_result is not None
    assert report.execution_result.selector == "0x42cbb15c"

    # Current Pacific head block should be > 20,000,000
    block_num = report.execution_result.decoded_value
    assert isinstance(block_num, int)
    assert block_num > 20000000

    assert report.interpretation is not None
    assert f"{block_num:,}" in report.interpretation.live_value_summary


def test_live_compose_permit2_domain_separator(live_composer):
    """Live Test 3: Permit2.DOMAIN_SEPARATOR() genuine composition."""
    report = live_composer.inspect_function("Permit2", "DOMAIN_SEPARATOR")
    assert report.success is True, f"Composition failed: {report.error_message}"

    assert report.doc_excerpt is not None
    assert report.execution_result is not None
    assert report.execution_result.selector == "0x3644e515"

    domain_hash = report.execution_result.decoded_value
    assert isinstance(domain_hash, str)
    assert domain_hash.startswith("0x")
    assert len(domain_hash) == 66  # 32 bytes hex

    assert report.interpretation is not None
    assert domain_hash in report.interpretation.contextual_meaning


def test_live_reject_atlantic_testnet_contract():
    """Live Test 4: Verify that Atlantic testnet contract address is rejected on Pacific Mainnet."""
    client = ChainMCPClient()
    client.initialize()
    # Handover testnet address
    testnet_addr = "0x76A4De34D608AEf6003117565868E079d20c57F9"
    with pytest.raises(ContractNotDeployedError) as exc_info:
        client.get_code(testnet_addr)
    assert "no deployed bytecode" in str(exc_info.value)
