# Security & Safety Policy: Pharos Doc-Chain Action Agent

## 1. Zero-Gas, Keyless Design

The **Pharos Doc-Chain Action Agent** is fundamentally designed as a read-only, keyless system:
- **No Private Keys:** The system contains no key generation, private key import, mnemonic handling, or wallet connections.
- **Zero Gas Cost ($0):** All blockchain interaction is strictly read-only (`eth_call`, `get_code`, `get_chain_info`). No funds can be spent.

---

## 2. Strict Tool Allowlist

Rather than relying on blacklisting alone, the system enforces a strict allowlist at the application boundary:

### 2.1 Permitted Tools (`SAFE_READ_ONLY_TOOLS`)
- `get_chain_info`
- `get_block_number`
- `get_balance`
- `get_transaction_count`
- `get_gas_price`
- `get_block`
- `get_transaction`
- `get_transaction_receipt`
- `get_code`
- `get_storage_at`
- `eth_call`
- `estimate_gas`
- `get_logs`

### 2.2 Explicitly Rejected Tools (`DISALLOWED_WRITE_TOOLS`)
- `send_raw_transaction`
- `send_transaction`
- `sign_transaction`
- `sign`
- `sign_typed_data`
- `wallet_sendTransaction`
- `eth_sendTransaction`
- `eth_sendRawTransaction`
- Any unknown or unclassified tool.

Any attempt to call a disallowed or unknown tool immediately raises `SafetyViolationError` before any network request is transmitted.

---

## 3. Network & Bytecode Verification

1. **Chain ID Enforcement:** Before executing calls, the agent queries `get_chain_info` and validates that `chainId == 1672` (Pharos Pacific Mainnet). If connected to an unexpected chain, execution halts immediately with `ChainIDMismatchError`.
2. **Bytecode Preflight:** Before invoking `eth_call`, the agent calls `get_code(target)` to verify that contract bytecode exists. If the contract has 0 bytes (e.g. an EOA or an Atlantic Testnet address), it raises `ContractNotDeployedError`.

---

## 4. Fail-Closed Resilience

The agent adheres strictly to the fail-closed principle:
- If the Developer Docs MCP is unreachable, it raises `DocsUnavailableError` rather than inventing documentation.
- If the hosted Chain MCP is unreachable, it raises `ChainUnavailableError` rather than simulating RPC results.
- If an `eth_call` reverts or returns `0x`, it raises `ChainRevertError`.
- No fallback to mock data or placeholder results is ever permitted in production workflows.
