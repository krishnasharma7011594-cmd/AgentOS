# Inter-Agent Communication Architecture

In AgentOS, direct inter-agent calls are strictly forbidden to preserve modularity and prevent coupling.

## Event Bus & Dispatcher

- `core/communication/messages.py`: Defines standard `AgentCommunicationEnvelope`.
- `core/communication/events.py`: System event schemas (`BaseEvent`).
- `core/communication/dispatcher.py`: `BaseCommunicationDispatcher` contract for broadcasting events and routing envelopes asynchronously.
- `core/communication/contracts.py`: Validation rules for message protocols.
