# Security Architecture

Security in AgentOS is layered across tool execution, prompt sanitization, and authorization.
Not all layers have concrete implementations yet — this document distinguishes between what
is enforced today and what is planned.

---

## Tool Execution Permissions — **Done**

`PermissionManager` (`core/tools/permissions.py`) is fully implemented. Every capability
execution passes through `validate_permissions()`, which checks that the executing agent
holds all `CapabilityPermission` entries declared on the `CapabilityDescriptor`. Missing
permissions raise `PermissionDeniedError` before the tool is invoked. Grant/revoke
lifecycle is logged via structlog.

---

## Input Sanitization & Token Verification — **Not Started (Interface Only)**

`BaseSecurityManager` (`core/security/base.py`) defines two `@abstractmethod` stubs —
`sanitize_input()` and `verify_token()` — but **no concrete implementation exists** in
the codebase. Inputs are not currently sanitized before being forwarded to LLM providers.
No authentication/token verification is performed on incoming API requests.

---

## Secrets & Log Redaction — **Not Enforced (Incidental Only)**

API keys are loaded via Pydantic Settings from `.env` and are never hardcoded in source
files. However, **there is no active redaction or masking logic in `core/logging/`**.
Secrets do not currently appear in log output because no code paths log them — this is
incidental, not an enforced guarantee. A dedicated log-scrubbing layer is planned for
Phase 11.

---

## ToolSandbox Isolation — **Partial**

`ToolSandbox` (`core/tools/sandbox.py`) captures exceptions and enforces `asyncio`
timeouts per `CapabilityDescriptor.policy.timeout_ms`. Tools execute within the same
Python process as the orchestrator — **no OS-level, container (Docker/gVisor), or
network-level isolation is in place yet**.
