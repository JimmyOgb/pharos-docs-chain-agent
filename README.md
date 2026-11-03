# Pharos Doc-Chain Action Agent

An autonomous agent that composes the official **Pharos Developer Docs MCP** and hosted **Pharos Chain MCP** into a single verified workflow: retrieving official smart contract documentation, validating Pacific Mainnet bytecode, executing read-only contract calls, and contextually synthesizing the live blockchain data with documented behavior.

Designed for **Pharos Agent Arena — Task 13: Docs MCP + Chain MCP Agent** (`docs-chain-mcp-agent`).

---

## Key Highlights

- **Dual Official MCP Integration:** Communicates via standard JSON-RPC 2.0 / SSE with:
  - Developer Docs MCP (`https://docs.pharos.xyz/~gitbook/mcp`) featuring dual-path retrieval resilience: executes primary semantic search (`searchDocumentation`), and automatically recovers via official targeted page retrieval (`getPage`) when GitBook's search index encounters upstream 500/Internal Server Error or empty results.
  - Hosted Chain MCP (`https://mcp.pharos.xyz/mcp`) on **Pharos Pacific Mainnet (Chain ID 1672)**.
- **Explain & Call the Same Function:** Seamlessly matches user queries to canonical contracts and functions, explains their purpose with official citations, executes the same function on-chain via `eth_call`, and provides contextual interpretation.
- **Multi-Contract / Multi-Function Coverage:** Full verified coverage for canonical contracts:
  - `MultiCall3` (`0xcA11bde05977b3631167028862bE2a173976CA11`): `getCurrentBlockTimestamp()`, `getBlockNumber()`
  - `Permit2` (`0x000000000022D473030F116dDEE9F6B43aC78BA3`): `DOMAIN_SEPARATOR()`
- **Strict Read-Only Safety Interceptor:** Hardware-level allowlist blocking `send_raw_transaction` and any state-mutating operation. Completely keyless, requiring no wallet, private keys, or gas ($0 budget maintained).
- **Fail-Closed Honesty:** Zero simulation or mock data in production. If documentation or on-chain bytecode is missing, the agent fails cleanly with transparent diagnostics.
- **Cryptographic Provenance:** Every response outputs four clearly delineated sections:
  1. `[1. DOCUMENTATION FACTS]`
  2. `[2. LIVE BLOCKCHAIN DATA]`
  3. `[3. AGENT CONTEXTUAL INTERPRETATION]`
  4. `[4. CRYPTOGRAPHIC & PROTOCOL PROVENANCE]`

---

## Architecture Overview

```
User Inquiry: "Explain MultiCall3 and retrieve the current timestamp"
     │
     ▼
[DocChainComposer]
     │
     ├── Step 1: Query Developer Docs MCP (searchDocumentation / getPage)
     │           Source: https://docs.pharos.xyz/getting-started/canonical-contracts
     │           Returns: Official purpose, parameters, return type
     │
     ├── Step 2: Query Hosted Chain MCP (Preflight & Validation)
     │           Asserts: Chain ID == 1672 (Pacific Mainnet)
     │           Asserts: get_code(target) > 0 (Bytecode deployed)
     │           Asserts: SafetyGuard allowlist (Rejects send_raw_transaction)
     │
     ├── Step 3: Execute Read-Only eth_call
     │           Target: 0xcA11bde05977b3631167028862bE2a173976CA11
     │           Calldata: 0x0f28c97d (getCurrentBlockTimestamp)
     │           Raw Return: 0x...6ae97276 -> Decoded: 1793684086 (2026-11-03T05:34:46Z)
     │
     └── Step 4: Contextual Synthesis & Provenance Recording
                 Combines documentation facts + live on-chain clock reading
```

---

## Prerequisites & Installation

- **Python:** Python 3.10 or higher.
- **Dependencies:** Standard library-first. Development and testing use `pytest`.
- **Operating System:** Windows, Linux, or macOS.

### Installation

```bash
git clone https://github.com/JimmyOgb/pharos-docs-chain-agent.git
cd pharos-docs-chain-agent
pip install -e .
```

Or run directly without installation:

```bash
set PYTHONPATH=.
python -m pharos_docs_chain_agent.cli --help
```

---

## CLI Usage

### 1. List Supported Canonical Targets
```bash
pharos-docs-chain-agent list-targets
```

### 2. Verify Chain MCP Connection
```bash
pharos-docs-chain-agent verify-chain
```

### 3. Inspect Contract Functions

#### Inspect MultiCall3 Block Timestamp:
```bash
pharos-docs-chain-agent inspect MultiCall3 getCurrentBlockTimestamp
```

#### Inspect MultiCall3 Current Block Height:
```bash
pharos-docs-chain-agent inspect MultiCall3 getBlockNumber
```

#### Inspect Permit2 EIP-712 Domain Separator:
```bash
pharos-docs-chain-agent inspect Permit2 DOMAIN_SEPARATOR
```

#### Output Machine-Readable JSON:
```bash
pharos-docs-chain-agent inspect MultiCall3 getCurrentBlockTimestamp --json
```

---

## Test Suite

The project includes 29 automated tests split between unit/safety verification and live integration:

```bash
# Run unit and safety tests (fast, mock-isolated):
pytest tests/test_unit.py tests/test_safety.py -v

# Run genuine live integration tests against Pacific Mainnet and Docs MCP:
pytest tests/test_live_integration.py -v

# Run entire test suite:
pytest -v
```

### Verification Breakdown:
- **17 Unit Tests:** ABI decoders, contract registry lookups, DocsExtractor, primary searchDocumentation, official getPage fallback recovery (handling upstream GitBook Internal Server Error and empty search matches), absent contract rejection, absent function rejection, getPage failure handling, and chain revert handling.
- **6 Safety Policy Tests:** Read-only allowlist enforcement, write tool rejection (`send_raw_transaction`), unknown tool blocking, chain ID enforcement (`1672`), bytecode preflight validation, address regex validation.
- **6 Live Integration Tests:** Real network calls to Developer Docs MCP (`https://docs.pharos.xyz/~gitbook/mcp`) and hosted Chain MCP (`https://mcp.pharos.xyz/mcp`) proving live execution for `getCurrentBlockTimestamp`, `getBlockNumber`, and `DOMAIN_SEPARATOR`, as well as honest rejection of testnet contracts.

---

## Read-Only Security Guarantees

1. **Zero Key Management:** No private keys, mnemonics, or wallets are loaded or requested.
2. **Strict Tool Allowlist:** The client inspects every tool call before transmission. If a tool is not in `SAFE_READ_ONLY_TOOLS` or is in `DISALLOWED_WRITE_TOOLS`, it is rejected locally with `SafetyViolationError`.
3. **Chain ID Enforcement:** Calls are only permitted if the connected RPC matches Pharos Pacific Mainnet (`1672`).
4. **Bytecode Preflight:** Contracts must have verified deployed bytecode before calling `eth_call`.

---

## Known Limitations

- **Read-Only Scope:** By design, this agent cannot sign transactions or modify state.
- **Upstream Rate Limits:** Developer Docs MCP may throttle excessive rapid queries; exponential backoff is recommended in high-frequency loops.
- **Network Dependency:** Live integration tests require internet access to connect to `docs.pharos.xyz` and `mcp.pharos.xyz`.

---

## License

MIT License. Copyright (c) 2026 JimmyOgb.
