"""CLI Interface for Pharos Doc-Chain Action Agent."""

import argparse
import json
import sys
from typing import List

from .composer import DocChainComposer
from .contracts import list_supported_targets
from .chain_mcp_client import ChainMCPClient
from .models import CompositionReport


def format_report_console(report: CompositionReport) -> str:
    """Format composition report into clean, structured sections."""
    lines: List[str] = []
    lines.append("=" * 80)
    lines.append(f"  PHAROS DOC-CHAIN ACTION AGENT: {report.contract_name}.{report.function_name}()")
    lines.append("=" * 80)

    if not report.success:
        lines.append("\n[ERROR / REJECTION]")
        lines.append(f"  Status: FAILED")
        lines.append(f"  Details: {report.error_message}")
        lines.append("=" * 80)
        return "\n".join(lines)

    # 1. Documentation Facts
    lines.append("\n[1. DOCUMENTATION FACTS (Official Developer Docs MCP)]")
    if report.doc_excerpt:
        lines.append(f"  Contract:         {report.doc_excerpt.contract_name}")
        lines.append(f"  Function:         {report.doc_excerpt.function_name}()")
        lines.append(f"  Parameters:       {report.doc_excerpt.parameters}")
        lines.append(f"  Return Type:      {report.doc_excerpt.return_type}")
        lines.append(f"  Section:          {report.doc_excerpt.section_title}")
        lines.append(f"  Source URL:       {report.doc_excerpt.source_url}")
        lines.append(f"  Explanation:      {report.doc_excerpt.description}")

    # 2. Live Blockchain Data
    lines.append("\n[2. LIVE BLOCKCHAIN DATA (Official Hosted Chain MCP)]")
    if report.execution_result:
        lines.append(f"  Network:          {report.execution_result.network} (Chain ID: {report.execution_result.chain_id})")
        lines.append(f"  Contract Address: {report.execution_result.contract_address}")
        lines.append(f"  Function:         {report.execution_result.function_name}()")
        lines.append(f"  Selector:         {report.execution_result.selector}")
        lines.append(f"  Method:           {report.execution_result.call_method}")
        lines.append(f"  Raw Hex Return:   {report.execution_result.raw_hex}")
        lines.append(f"  Decoded Value:    {report.execution_result.decoded_value}")

    # 3. Agent Contextual Interpretation
    lines.append("\n[3. AGENT CONTEXTUAL INTERPRETATION]")
    if report.interpretation:
        lines.append(f"  Summary:          {report.interpretation.explanation_summary}")
        lines.append(f"  Live Reading:     {report.interpretation.live_value_summary}")
        lines.append(f"  Contextual Meaning:\n    {report.interpretation.contextual_meaning}")
        lines.append(f"  Limitations:      {report.interpretation.limitations}")

    # 4. Cryptographic Provenance
    lines.append("\n[4. CRYPTOGRAPHIC & PROTOCOL PROVENANCE]")
    if report.provenance:
        lines.append(f"  Docs Tool:        {report.provenance.docs_tool_used}")
        lines.append(f"  Docs Source:      {report.provenance.docs_source_url}")
        lines.append(f"  Chain Tool:       {report.provenance.chain_mcp_tool_used}")
        lines.append(f"  MCP Session ID:   {report.provenance.mcp_session_id}")
        lines.append(f"  ABI Source:       {report.provenance.abi_source}")
        lines.append(f"  Status:           {report.provenance.verification_status}")
        lines.append(f"  Recorded At:      {report.provenance.recorded_at}")

    lines.append("=" * 80)
    return "\n".join(lines)


def main():
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        prog="pharos-docs-chain-agent",
        description="Pharos Doc-Chain Action Agent connecting Docs MCP and Chain MCP."
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Subcommand: inspect
    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Inspect a contract function via Docs MCP and invoke it via Chain MCP"
    )
    inspect_parser.add_argument("contract", help="Canonical contract name (e.g. MultiCall3, Permit2)")
    inspect_parser.add_argument("function", help="Function name (e.g. getCurrentBlockTimestamp, getBlockNumber, DOMAIN_SEPARATOR)")
    inspect_parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    # Subcommand: list-targets
    list_parser = subparsers.add_parser(
        "list-targets",
        help="List all supported canonical contracts and verified functions"
    )
    list_parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    # Subcommand: verify-chain
    verify_parser = subparsers.add_parser(
        "verify-chain",
        help="Verify connection to hosted Chain MCP and validate Pacific Mainnet (1672)"
    )
    verify_parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "list-targets":
        targets = list_supported_targets()
        if args.json:
            print(json.dumps(targets, indent=2))
        else:
            print("\nSupported Canonical Targets on Pharos Pacific Mainnet (1672):\n")
            for t in targets:
                print(f"  - Contract:    {t['contract']} ({t['address']})")
                print(f"    Function:    {t['function']}() [{t['selector']}] -> {t['return_type']}")
                print(f"    Docs Source: {t['docs_url']}\n")
        sys.exit(0)

    elif args.command == "verify-chain":
        chain_client = ChainMCPClient()
        try:
            chain_client.initialize()
            info = chain_client.get_chain_info()
            if args.json:
                print(json.dumps(info, indent=2))
            else:
                print("\nChain MCP Connection Verified:")
                print(f"  Network:    {info.get('name')}")
                print(f"  Chain ID:   {info.get('chainId')} (matches expected: {info.get('chainIdMatches')})")
                print(f"  Head Block: {info.get('latestBlock')}")
                print(f"  Currency:   {info.get('nativeSymbol')}")
                print(f"  RPC URL:    {info.get('rpcUrl')}\n")
            sys.exit(0)
        except Exception as e:
            if args.json:
                print(json.dumps({"error": str(e)}, indent=2))
            else:
                print(f"\n[CHAIN VERIFICATION FAILED]: {e}\n", file=sys.stderr)
            sys.exit(1)

    elif args.command == "inspect":
        composer = DocChainComposer()
        report = composer.inspect_function(args.contract, args.function)
        if args.json:
            print(json.dumps(report.to_dict(), indent=2))
        else:
            print(format_report_console(report))
        sys.exit(0 if report.success else 1)


if __name__ == "__main__":
    main()
