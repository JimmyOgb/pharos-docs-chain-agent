"""Unit tests for models, decoders, contract registry, extractor, and composer."""

import pytest
from unittest.mock import MagicMock

from pharos_docs_chain_agent.contracts import (
    decode_uint256,
    decode_timestamp,
    decode_bytes32,
    get_canonical_contract,
    get_canonical_function,
    list_supported_targets,
    FunctionSpec
)
from pharos_docs_chain_agent.docs_extractor import DocsExtractor
from pharos_docs_chain_agent.models import (
    ABIEncodingError,
    DocSearchResult,
    DocumentationNotFoundError
)
from pharos_docs_chain_agent.composer import DocChainComposer
from pharos_docs_chain_agent.cli import format_report_console


# ---------------------------------------------------------------------------
# Decoder Tests
# ---------------------------------------------------------------------------

def test_decode_uint256():
    """Verify uint256 decoding from hex strings."""
    assert decode_uint256("0x000000000000000000000000000000000000000000000000000000000000002a") == 42
    assert decode_uint256("0x01") == 1
    assert decode_uint256("0x00") == 0
    assert decode_uint256("ff") == 255


def test_decode_uint256_errors():
    """Verify uint256 decoding raises ABIEncodingError on malformed inputs."""
    with pytest.raises(ABIEncodingError):
        decode_uint256("")
    with pytest.raises(ABIEncodingError):
        decode_uint256("0x")
    with pytest.raises(ABIEncodingError):
        decode_uint256("0xNOT_HEX")


def test_decode_timestamp():
    """Verify timestamp decoding converts to integer epoch and ISO-8601 string."""
    # 1700000000 in hex is 0x6553f100
    res = decode_timestamp("0x000000000000000000000000000000000000000000000000000000006553f100")
    assert res["epoch_seconds"] == 1700000000
    assert "2023-11-14" in res["iso_utc"]


def test_decode_bytes32():
    """Verify 32-byte hex decoding."""
    hex32 = "0x" + "aa" * 32
    assert decode_bytes32(hex32) == hex32.lower()

    # Without 0x prefix
    assert decode_bytes32("bb" * 32) == ("0x" + "bb" * 32)

    # Invalid length
    with pytest.raises(ABIEncodingError):
        decode_bytes32("0x1234")


# ---------------------------------------------------------------------------
# Contract Registry Tests
# ---------------------------------------------------------------------------

def test_contract_registry_multicall3():
    """Verify MultiCall3 contract specifications and functions."""
    contract = get_canonical_contract("MultiCall3")
    assert contract is not None
    assert contract.address == "0xcA11bde05977b3631167028862bE2a173976CA11"

    # Case-insensitive resolution
    assert get_canonical_contract("multicall3") is not None

    # Functions
    fn_ts = get_canonical_function("MultiCall3", "getCurrentBlockTimestamp")
    assert fn_ts is not None
    assert fn_ts.selector == "0x0f28c97d"

    # With parentheses
    fn_ts_parens = get_canonical_function("MultiCall3", "getCurrentBlockTimestamp()")
    assert fn_ts_parens is not None
    assert fn_ts_parens.selector == "0x0f28c97d"

    fn_bn = get_canonical_function("MultiCall3", "getBlockNumber")
    assert fn_bn is not None
    assert fn_bn.selector == "0x42cbb15c"


def test_contract_registry_permit2():
    """Verify Permit2 contract specifications and functions."""
    contract = get_canonical_contract("Permit2")
    assert contract is not None
    assert contract.address == "0x000000000022D473030F116dDEE9F6B43aC78BA3"

    fn_dom = get_canonical_function("Permit2", "DOMAIN_SEPARATOR")
    assert fn_dom is not None
    assert fn_dom.selector == "0x3644e515"


def test_list_supported_targets():
    """Verify all expected canonical functions are listed."""
    targets = list_supported_targets()
    assert len(targets) >= 3
    selectors = [t["selector"] for t in targets]
    assert "0x0f28c97d" in selectors
    assert "0x42cbb15c" in selectors
    assert "0x3644e515" in selectors


# ---------------------------------------------------------------------------
# Docs Extractor Tests
# ---------------------------------------------------------------------------

def test_docs_extractor_match():
    """Verify excerpt extraction when search result matches contract."""
    contract = get_canonical_contract("MultiCall3")
    fn = get_canonical_function("MultiCall3", "getBlockNumber")
    results = [
        DocSearchResult(
            title="Canonical Contracts",
            url="https://docs.pharos.xyz/getting-started/canonical-contracts",
            content="MultiCall3 allows bundling multiple transactions: 0xcA11bde05977b3631167028862bE2a173976CA11"
        )
    ]
    excerpt = DocsExtractor.extract_excerpt(contract, fn, results)
    assert excerpt.contract_name == "MultiCall3"
    assert excerpt.source_url == "https://docs.pharos.xyz/getting-started/canonical-contracts"
    assert "MultiCall3" in excerpt.description


def test_docs_extractor_fallback():
    """Verify fallback when search returns empty or unmatched results."""
    contract = get_canonical_contract("MultiCall3")
    fn = get_canonical_function("MultiCall3", "getBlockNumber")
    with pytest.raises(DocumentationNotFoundError):
        DocsExtractor.extract_excerpt(contract, fn, [])


# ---------------------------------------------------------------------------
# Composer Pipeline Mock Tests
# ---------------------------------------------------------------------------

def test_composer_pipeline_mock():
    """Verify end-to-end composer logic with controlled client fixtures."""
    mock_docs_client = MagicMock()
    mock_docs_client.search_documentation.return_value = [
        DocSearchResult(
            title="Canonical Contracts",
            url="https://docs.pharos.xyz/getting-started/canonical-contracts",
            content="MultiCall3: 0xcA11bde05977b3631167028862bE2a173976CA11"
        )
    ]

    mock_chain_client = MagicMock()
    mock_chain_client.session_id = "mock-session-123"
    mock_chain_client.get_chain_info.return_value = {
        "name": "Pharos Pacific Mainnet",
        "chainId": 1672
    }
    mock_chain_client.get_code.return_value = "0x608060405234801561001057600080fd5b50"
    mock_chain_client.eth_call.return_value = "0x00000000000000000000000000000000000000000000000000000000014f7d09"

    composer = DocChainComposer(docs_client=mock_docs_client, chain_client=mock_chain_client)
    report = composer.inspect_function("MultiCall3", "getBlockNumber")

    assert report.success is True
    assert report.execution_result.decoded_value == 21986569
    assert report.provenance.mcp_session_id == "mock-session-123"

    console_output = format_report_console(report)
    assert "[1. DOCUMENTATION FACTS (Official Developer Docs MCP)]" in console_output
    assert "[2. LIVE BLOCKCHAIN DATA (Official Hosted Chain MCP)]" in console_output
    assert "[3. AGENT CONTEXTUAL INTERPRETATION]" in console_output
    assert "[4. CRYPTOGRAPHIC & PROTOCOL PROVENANCE]" in console_output


# ---------------------------------------------------------------------------
# Recovery & Regression Tests (Gate 6.2)
# ---------------------------------------------------------------------------

def test_composer_primary_search_path():
    """Verify successful search uses searchDocumentation and records it in provenance."""
    mock_docs = MagicMock()
    mock_docs.search_documentation.return_value = [
        DocSearchResult(
            title="Canonical Contracts",
            url="https://docs.pharos.xyz/getting-started/canonical-contracts",
            content="MultiCall3: 0xcA11bde05977b3631167028862bE2a173976CA11"
        )
    ]
    mock_chain = MagicMock()
    mock_chain.session_id = "sess-1"
    mock_chain.get_chain_info.return_value = {"name": "Pharos", "chainId": 1672}
    mock_chain.get_code.return_value = "0x6080"
    mock_chain.eth_call.return_value = "0x00000000000000000000000000000000000000000000000000000000014f7d09"

    composer = DocChainComposer(docs_client=mock_docs, chain_client=mock_chain)
    report = composer.inspect_function("MultiCall3", "getBlockNumber")

    assert report.success is True
    assert report.provenance.docs_tool_used == "searchDocumentation"
    mock_docs.get_page.assert_not_called()


def test_composer_recovery_on_internal_server_error():
    """Verify search returning Internal Server Error triggers getPage recovery."""
    mock_docs = MagicMock()
    mock_docs.search_documentation.return_value = [
        DocSearchResult(title="Pharos Documentation", url="https://docs.pharos.xyz", content="Internal Server Error")
    ]
    mock_docs.get_page.return_value = "# Canonical Contracts\nMultiCall3 0xcA11bde05977b3631167028862bE2a173976CA11"

    mock_chain = MagicMock()
    mock_chain.session_id = "sess-2"
    mock_chain.get_chain_info.return_value = {"name": "Pharos", "chainId": 1672}
    mock_chain.get_code.return_value = "0x6080"
    mock_chain.eth_call.return_value = "0x00000000000000000000000000000000000000000000000000000000014f7d09"

    composer = DocChainComposer(docs_client=mock_docs, chain_client=mock_chain)
    report = composer.inspect_function("MultiCall3", "getBlockNumber")

    assert report.success is True
    assert report.provenance.docs_tool_used == "getPage"
    mock_docs.get_page.assert_called_once_with("https://docs.pharos.xyz/getting-started/canonical-contracts")


def test_composer_recovery_on_empty_search():
    """Verify empty search results trigger getPage recovery."""
    mock_docs = MagicMock()
    mock_docs.search_documentation.return_value = []
    mock_docs.get_page.return_value = "Permit2 0x000000000022D473030F116dDEE9F6B43aC78BA3"

    mock_chain = MagicMock()
    mock_chain.session_id = "sess-3"
    mock_chain.get_chain_info.return_value = {"name": "Pharos", "chainId": 1672}
    mock_chain.get_code.return_value = "0x6080"
    mock_chain.eth_call.return_value = "0x45de4588c7712b7ad6e03439ca842a8a690d1e3e1f4982ec13ca05a25dfd4245"

    composer = DocChainComposer(docs_client=mock_docs, chain_client=mock_chain)
    report = composer.inspect_function("Permit2", "DOMAIN_SEPARATOR")

    assert report.success is True
    assert report.provenance.docs_tool_used == "getPage"


def test_docs_extractor_page_content_contract_absent():
    """Verify DocsExtractor fails closed if contract name is absent from retrieved page."""
    contract = get_canonical_contract("MultiCall3")
    fn = get_canonical_function("MultiCall3", "getBlockNumber")
    with pytest.raises(DocumentationNotFoundError) as exc_info:
        DocsExtractor.extract_excerpt(contract, fn, [], page_content="Unrelated page without the contract")
    assert "no matching documentation for contract 'MultiCall3'" in str(exc_info.value)


def test_docs_extractor_function_absent_fails_closed():
    """Verify DocsExtractor fails closed if function is not documented for the contract."""
    contract = get_canonical_contract("MultiCall3")
    fake_fn = FunctionSpec(
        name="nonExistentFunction",
        signature="nonExistentFunction()",
        selector="0x12345678",
        input_types=[],
        return_type="uint256",
        docs_description="",
        decoder=decode_uint256,
        abi_source="Unknown",
        verification_notes=""
    )
    with pytest.raises(DocumentationNotFoundError) as exc_info:
        DocsExtractor.extract_excerpt(contract, fake_fn, [], page_content="MultiCall3 description")
    assert "not documented" in str(exc_info.value)


def test_composer_getpage_failure_raises():
    """Verify composer reports failure when getPage raises an exception."""
    mock_docs = MagicMock()
    mock_docs.search_documentation.return_value = []
    mock_docs.get_page.side_effect = Exception("HTTP 500 Connection reset")

    mock_chain = MagicMock()
    composer = DocChainComposer(docs_client=mock_docs, chain_client=mock_chain)
    report = composer.inspect_function("MultiCall3", "getBlockNumber")

    assert report.success is False
    assert "HTTP 500 Connection reset" in report.error_message
    mock_chain.eth_call.assert_not_called()


def test_composer_chain_revert_fails_closed():
    """Verify that an eth_call revert fails closed without fabricating output."""
    mock_docs = MagicMock()
    mock_docs.search_documentation.return_value = [
        DocSearchResult(title="Canonical Contracts", url="https://docs.pharos.xyz", content="MultiCall3")
    ]
    mock_chain = MagicMock()
    mock_chain.session_id = "sess-4"
    mock_chain.get_chain_info.return_value = {"name": "Pharos", "chainId": 1672}
    mock_chain.get_code.return_value = "0x6080"
    mock_chain.eth_call.side_effect = Exception("Execution reverted: CALL_FAILED")

    composer = DocChainComposer(docs_client=mock_docs, chain_client=mock_chain)
    report = composer.inspect_function("MultiCall3", "getBlockNumber")

    assert report.success is False
    assert "Execution reverted" in report.error_message
