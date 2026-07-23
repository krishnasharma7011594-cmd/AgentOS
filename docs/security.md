# Security Architecture

Security in AgentOS is enforced across tool execution, prompt sanitization, and authorization.

## Security Policies
- **Tool Execution Permissions**: Every tool invocation passes through `BaseToolPermissionsPolicy` in `core/tools/permissions.py`.
- **Input Sanitization**: `BaseSecurityManager` in `core/security/base.py` handles input filtering and token verification.
- **Environment Isolation**: API keys and secrets are loaded securely via Pydantic Settings and are never exposed in log files or hardcoded.
