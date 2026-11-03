"""Core orchestration engine composing Developer Docs MCP and hosted Chain MCP."""

from typing import Optional

from .contracts import (
    get_canonical_contract,
    get_canonical_function
)
from .docs_extractor import DocsExtractor
from .docs_mcp_client import DocsMCPClient
from .chain_mcp_client import ChainMCPClient
from .models import (
    ChainExecutionResult,
    CompositionReport,
    DocChainBaseError,
    InterpretationResult,
    ProvenanceRecord
)


class DocChainComposer:
    """Orchestrates documentation lookup, read-only on-chain execution, and contextual interpretation."""

    def __init__(
        self,
        docs_client: Optional[DocsMCPClient] = None,
        chain_client: Optional[ChainMCPClient] = None
    ):
        self.docs_client = docs_client or DocsMCPClient()
        self.chain_client = chain_client or ChainMCPClient()

    def inspect_function(self, contract_name: str, function_name: str) -> CompositionReport:
        """Execute the full composition pipeline for a given contract and function."""
        # 1. Resolve contract and function specifications
        contract_spec = get_canonical_contract(contract_name)
        if not contract_spec:
            return CompositionReport(
                contract_name=contract_name,
                function_name=function_name,
                doc_excerpt=None,
                execution_result=None,
                interpretation=None,
                provenance=None,
                success=False,
                error_message=f"Contract '{contract_name}' is not in the canonical Pacific Mainnet registry."
            )

        function_spec = get_canonical_function(contract_name, function_name)
        if not function_spec:
            return CompositionReport(
                contract_name=contract_spec.name,
                function_name=function_name,
                doc_excerpt=None,
                execution_result=None,
                interpretation=None,
                provenance=None,
                success=False,
                error_message=(
                    f"Function '{function_name}' is not a verified function for contract '{contract_spec.name}'. "
                    f"Supported functions: {list(contract_spec.functions.keys())}"
                )
            )

        try:
            # 2. Query Developer Docs MCP (Primary path: searchDocumentation)
            self.docs_client.initialize()
            docs_tool_used = "searchDocumentation"
            search_results = []
            search_succeeded = False
            try:
                search_query = f"{contract_spec.name} canonical contract"
                search_results = self.docs_client.search_documentation(search_query)
                for r in search_results:
                    text_lower = (r.title + " " + r.content).lower()
                    if "internal server error" not in text_lower and contract_spec.name.lower() in text_lower:
                        search_succeeded = True
                        break
            except Exception:
                search_succeeded = False

            page_content = None
            if not search_succeeded:
                # Recovery path: official getPage tool
                docs_tool_used = "getPage"
                page_content = self.docs_client.get_page(contract_spec.docs_url)

            doc_excerpt = DocsExtractor.extract_excerpt(
                contract_spec=contract_spec,
                function_spec=function_spec,
                search_results=search_results if search_succeeded else [],
                page_content=page_content
            )

            # 3. Query hosted Chain MCP on Pacific Mainnet (1672)
            self.chain_client.initialize()
            chain_info = self.chain_client.get_chain_info()
            network_name = chain_info.get("name", "Pharos Pacific Mainnet")
            chain_id = int(chain_info.get("chainId", 1672))

            # 4. Preflight contract bytecode
            self.chain_client.get_code(contract_spec.address)

            # 5. Execute read-only eth_call
            raw_hex = self.chain_client.eth_call(contract_spec.address, function_spec.selector)

            # 6. Decode return value
            decoded_val = function_spec.decoder(raw_hex)

            # 7. Formulate Execution Result
            exec_result = ChainExecutionResult(
                network=network_name,
                chain_id=chain_id,
                contract_address=contract_spec.address,
                function_name=function_spec.name,
                selector=function_spec.selector,
                call_method="eth_call (read-only)",
                raw_hex=raw_hex,
                decoded_value=decoded_val
            )

            # 8. Synthesize Contextual Interpretation
            interpretation = self._synthesize_interpretation(
                contract_spec.name,
                function_spec.name,
                decoded_val,
                doc_excerpt.description
            )

            # 9. Record Full Provenance
            provenance = ProvenanceRecord(
                docs_tool_used=docs_tool_used,
                docs_source_url=doc_excerpt.source_url,
                chain_mcp_tool_used="eth_call",
                mcp_session_id=self.chain_client.session_id,
                abi_source=function_spec.abi_source,
                verification_status="LIVE_VERIFIED_GENUINE"
            )

            return CompositionReport(
                contract_name=contract_spec.name,
                function_name=function_spec.name,
                doc_excerpt=doc_excerpt,
                execution_result=exec_result,
                interpretation=interpretation,
                provenance=provenance,
                success=True
            )

        except DocChainBaseError as e:
            return CompositionReport(
                contract_name=contract_spec.name,
                function_name=function_spec.name,
                doc_excerpt=None,
                execution_result=None,
                interpretation=None,
                provenance=None,
                success=False,
                error_message=str(e)
            )
        except Exception as e:
            return CompositionReport(
                contract_name=contract_spec.name,
                function_name=function_spec.name,
                doc_excerpt=None,
                execution_result=None,
                interpretation=None,
                provenance=None,
                success=False,
                error_message=f"Unexpected error during composition: {e}"
            )

    def _synthesize_interpretation(
        self,
        contract_name: str,
        function_name: str,
        decoded_val: any,
        doc_desc: str
    ) -> InterpretationResult:
        """Ground the interpretation in the official documentation facts."""
        if function_name == "getCurrentBlockTimestamp":
            epoch = decoded_val.get("epoch_seconds") if isinstance(decoded_val, dict) else decoded_val
            iso = decoded_val.get("iso_utc") if isinstance(decoded_val, dict) else ""
            summary = "EVM block timestamp retrieved from canonical MultiCall3."
            live_summary = f"Epoch: {epoch} ({iso})"
            meaning = (
                f"As documented in '{doc_desc}', MultiCall3 provides synchronous block environment "
                f"data. The value {epoch} represents the EVM block timestamp for the latest mined "
                f"block on Pharos Pacific Mainnet, corresponding to {iso}."
            )
            limitations = "Timestamp is block-level granularity, determined by validator block proposal."

        elif function_name == "getBlockNumber":
            summary = "Current Pacific Mainnet block height retrieved via MultiCall3."
            live_summary = f"Block Height: {decoded_val:,}"
            meaning = (
                f"MultiCall3 allows callers to inspect the current chain block height. "
                f"The returned height {decoded_val:,} confirms active block production on Pharos Pacific "
                f"Mainnet (Chain ID 1672)."
            )
            limitations = "Subject to new block generation every ~2 seconds."

        elif function_name == "DOMAIN_SEPARATOR":
            summary = "EIP-712 Domain Separator hash retrieved from canonical Permit2."
            live_summary = f"Hash: {decoded_val}"
            meaning = (
                f"Permit2 uses the DOMAIN_SEPARATOR hash to uniquely bind signature-based approvals "
                f"to the Pharos Pacific Mainnet deployment (Chain ID 1672). Any off-chain permit "
                f"signature must match this hash ({decoded_val}) to prevent replay across chains."
            )
            limitations = "Static per chain and contract deployment; invalidates signatures signed for other chains."

        else:
            summary = f"Execution of {contract_name}.{function_name} completed."
            live_summary = f"Value: {decoded_val}"
            meaning = f"The live blockchain call returned {decoded_val}, matching the function specification."
            limitations = "None recorded."

        return InterpretationResult(
            explanation_summary=summary,
            live_value_summary=live_summary,
            contextual_meaning=meaning,
            limitations=limitations
        )
