# AI Architecture

## Purpose

Định nghĩa luồng AI để AI Planner có thể gọi LLM đúng lúc, đúng dữ liệu và đúng mục tiêu.

## AI pipeline

```text
User Action
  ↓
Backend
  ↓
Context Builder
  ↓
Prompt Builder
  ↓
OpenAI API
  ↓
Response Parser
  ↓
Database + Events
```

## Boundaries

- AI creates suggestions, not final state
- backend validates and decides persistence
- user confirmation is required for major schedule changes
- AI output must be structured and parseable

## Responsibilities

### Context Builder

- select the correct window
- collect event summary
- gather schedule and task state
- attach feedback and preferences

### Prompt Builder

- format the context into a stable prompt shape
- keep prompts maintainable
- avoid prompt duplication by use case

### Response Parser

- validate AI output
- map response into daily plan and suggestion objects
- reject malformed output safely

### Provider adapter

- isolate OpenAI API specifics
- support future provider swap without changing core business logic

## Input to AI

- user profile
- tasks and schedule for the active window
- recent events within the chosen context window
- feedback and preferences
- current date and time

## Output from AI

- suggested schedule items
- explanation blocks
- rationale labels
- confidence or priority hints
- context snapshot reference

## Structured output validation

- response must match expected schema
- invalid fields are rejected
- fallback to manual flow if parser fails

## Retry and timeout

- AI calls should have a bounded timeout
- retry only when the failure is likely transient
- do not retry blindly on malformed output

## Cost control

- call LLM only when rule-based logic cannot answer
- use context windows, not full history dumps
- prefer cached summaries for repeated requests

## Forbidden data

- password or secrets
- raw unrelated history
- data outside the current user scope
- UI-only metadata

## AI triggers

- today open
- daily generation
- adjustment after change
- end-of-day summary

## AI guardrails

- rule-based logic first
- call LLM only when needed
- never trust raw AI output without validation
- keep fallback paths for manual editing

## User confirmation rule

- generated plan can be previewed before applying
- user must confirm high-impact changes
- accepted AI output must still pass business validation before save

## Memory strategy

- short-term memory comes from context windows
- long-term memory comes from events and summaries
- do not store free-form memory without structure in MVP
