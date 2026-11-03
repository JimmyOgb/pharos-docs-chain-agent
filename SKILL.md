---
name: pharos-docs-chain-agent
description: Composes official Pharos Developer Docs MCP with hosted Chain MCP for smart contract explanation, bytecode validation, read-only on-chain execution, and contextual interpretation on Pharos Pacific Mainnet.
version: 0.1.0
author: JimmyOgb
license: MIT
---

# Pharos Doc-Chain Action Agent

## Purpose

The `pharos-docs-chain-agent` skill provides a composition pipeline between the official **Pharos Developer Docs MCP** and the hosted **Pharos Chain MCP**. It bridges theoretical smart contract documentation with live on-chain reality on **Pharos Pacific Mainnet (Chain ID 1672)**.

## Supported Capabilities

1. **Semantic Documentation Lookup:** Searches and retrieves official canonical contract documentation via `searchDocumentation` and `getPage` on `https://docs.pharos.xyz/~gitbook/mcp`.
2. **Bytecode Preflight:** Verifies that a contract actually has deployed code on Pacific Mainnet using `get_code`.
3. **Read-Only On-Chain Execution:** Executes function selectors via `eth_call` on `https://mcp.pharos.xyz/mcp` under a strict read-only security allowlist.
4. **Contextual Synthesis:** Synthesizes the live hexadecimal return value with the documentation facts, providing human-readable explanations, parameter interpretations, and timestamps.
5. **Cryptographic Provenance:** Delineates documentation sources, GitBook URLs, Chain MCP session IDs, target addresses, selectors, and raw returns.

## Verified Targets (Pharos Pacific Mainnet 1672)

- **MultiCall3 (`0xcA11bde05977b3631167028862bE2a173976CA11`):**
  - `getCurrentBlockTimestamp()`: Selector `0x0f28c97d`, returns current EVM block timestamp.
  - `getBlockNumber()`: Selector `0x42cbb15c`, returns current head block height.
- **Permit2 (`0x000000000022D473030F116dDEE9F6B43aC78BA3`):**
  - `DOMAIN_SEPARATOR()`: Selector `0x3644e515`, returns EIP-712 domain separator hash.

## CLI Usage

```bash
# List all supported targets
pharos-docs-chain-agent list-targets

# Verify live Chain MCP connection
pharos-docs-chain-agent verify-chain

# Inspect a contract function
pharos-docs-chain-agent inspect MultiCall3 getCurrentBlockTimestamp
pharos-docs-chain-agent inspect MultiCall3 getBlockNumber
pharos-docs-chain-agent inspect Permit2 DOMAIN_SEPARATOR

# Inspect with JSON output
pharos-docs-chain-agent inspect MultiCall3 getCurrentBlockTimestamp --json
```

## Security Constraints

- Read-only tools ONLY (`get_chain_info`, `get_code`, `eth_call`, `get_block_number`, etc.).
- `send_raw_transaction` and any signing or state mutation are strictly blocked.
- Keyless architecture with $0 cost.
