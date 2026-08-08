# AgentGraph OS Architecture


## Overview


AgentGraph OS is a local-first AI agent orchestration platform.


## Main Components


1. Frontend
2. Agent Runtime
3. Model Router
4. Memory System
5. Tool System
6. Plugin System


## Data Flow


User

↓

Frontend

↓

Agent Manager

↓

LangGraph

↓

Agents

↓

Tools

↓

Memory


## AI Providers


Local:

- Ollama


Cloud:

- OpenAI
- OpenRouter

