# Contributing Guidelines

Thank you for contributing to AgentOS!

## Standard Agent Template Creation
When introducing a new agent to `agents/`, clone the template directory structure:
```
agents/<new_agent_name>/
├── agent.py
├── config.py
├── memory.py
├── prompts.py
├── tools.py
└── README.md
```

## Quality Standards
Before submitting pull requests, run:
```bash
ruff check .
black --check .
mypy core supervisor registry agents workflow task_queue knowledge observability evaluation apps
pytest
```
