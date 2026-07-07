# 🔬 Reposeer Studio

An automated, multi-agent engineering evaluation framework that runs live static analysis and AST crawling on target codebases to host deep architectural technical drills.

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=nextdotjs)](https://nextjs.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)

---

## 🌌 Overview

**Reposeer Studio** changes how engineering competence is evaluated. Instead of generic puzzle challenges or static questionnaires, Reposeer acts as an automated System Architect. It parses raw repository structures into Abstract Syntax Trees (ASTs), extracts critical functional vectors (e.g., database connection pools, transaction logic, API configurations), and targets real-world edge cases to test production safety boundaries.

### ✨ Core Features

* 🤖 **Multi-Agent Orchestration:** Utilises a LangGraph-driven routing architecture to harvest active context pools and assemble runtime code signatures into evaluation models.
* 🔬 **AST-Driven Evaluation Loops:** Executes a 5-step structured grading sequence probing critical operational bottlenecks like connection pool exhaustion, unhandled exception bubbling, and cascading failure states.
* 📡 **Stateful Session Checkpointing:** Features an asynchronous background thread layout that persists evaluation metrics against explicit session tokens, allowing recovery through upstream dependency failures.
* 🔄 **Idempotent Session Redo Pipeline:** Automatically caches and preloads the last evaluated repository path layout while providing a quick action to drop stale states and re-index the code footprint under a fresh tracking ID.
* ✨ **Premium Developer UI:** Styled around a modern, dark-themed, glassmorphic design system inspired by premium developer experiences.

---

## 🛠️ Architecture Blueprint

Reposeer separates raw file extraction, agent orchestration, and frontend visualization into localized layers to maintain strict processing isolation:

```text
       ┌─────────────────────────────────────────────────────────┐
       │                 Next.js Frontend Client                 │
       │     (Glassmorphic Workspace UI & Telemetry Logs)        │
       └────────────────────────────┬────────────────────────────┘
                                    │ HTTP / WebSocket REST
                                    ▼
       ┌─────────────────────────────────────────────────────────┐
       │                FastAPI Application Core                 │
       │      (Session Checkpointers & Endpoint Routing)         │
       └────────────────────────────┬────────────────────────────┘
                                    │
            ┌───────────────────────┴───────────────────────┐
            ▼                                               ▼
┌───────────────────────┐                       ┌───────────────────────┐
│     Router Agent      │                       │   Evaluator Agent     │
│ (AST Code Vectorizer) │                       │ (Structured Grading)  │
└───────────────────────┘                       └───────────────────────┘
