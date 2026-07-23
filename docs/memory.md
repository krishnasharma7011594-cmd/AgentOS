# Layered Memory Architecture

AgentOS provides a multi-tiered memory abstraction layer in `core/memory/`.

## Tiers

1. `working/`: Transient in-context window memory for active tasks.
2. `session/`: Session-scoped memory retaining user interaction context.
3. `long_term/`: Persistent episodic and semantic memory storage.
4. `cache/`: High-performance key-value memory caching layer.

All memory tiers inherit from the `BaseMemory` interface (`core/memory/interfaces/base.py`).
