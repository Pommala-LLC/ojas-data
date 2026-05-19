# Ojas Data
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

**LLM understands the request, but policy controls execution.**

Ojas Data  is a governed AI-agent data access . It prevents agents from freely writing SQL or directly accessing databases. Instead, agents select registered tools, and the  enforces authorization, use-case policy, row or path scope, sensitive-field blocking, output masking, credential isolation, safe query construction, and policy-versioned audit before any data operation executes.


---

## What This Project Does

Ojas Data  provides a policy-controlled execution layer between AI agents and enterprise data stores.

It is designed for systems where AI agents need to read or update operational data, but the model must not receive raw database access, raw credentials, unrestricted SQL, or unmasked sensitive values.

```text
User request
  → LLM selects registered tool
  →  authorizes agent + use case
  →  builds safe SQL/document operation
  →  applies row/path scope
  →  masks protected output
  →  executes with least-privilege credential
  →  writes policy-versioned audit event
```

The LLM understands the user’s request.

The  controls execution.

---

## Core Principle

```text
The LLM may propose intent.
The policy engine decides access.
The  constructs the query.
The database executes only governed operations.
```

Ojas Data  does **not** rely on prompt instructions or post-hoc query checking as the primary security control.

Instead, it prevents model-generated executable SQL from being the execution path.

---

## Why This Exists

Generic SQL agents often work like this:

```text
User asks question
  → LLM generates SQL
  → optional query checker reviews SQL
  → SQL executes
```

That is risky.

The model may generate:

```sql
SELECT * FROM students;
SELECT password, ssn FROM students;
DELETE FROM students;
DROP TABLE students;
```

Ojas Data  uses a different model:

```text
User asks question
  → LLM selects approved tool
  → tool maps to one governed use case
  →  authorizes columns, rows, paths, and operation
  →  builds the query safely
```

The LLM does not write executable SQL.

---

## Key Capabilities

- Registered tool surface for AI agents
- Tool-to-use-case binding
- Agent-to-tool authorization
- SQL dialect registry
- Framework adapter registry
- Document/NoSQL dialect registry
- Safe SQL construction
- Document projection governance
- Sensitive-field blocking
- Masked-field transformation before LLM visibility
- Row-level and path-level scope enforcement
- Least-privilege credential roles
- Policy-versioned audit events
- Backend capability validation
- SQLite development mode with production refusal
- Optional framework adapters for CrewAI, LangChain, LangGraph, and OpenAI function calling
- MongoDB and DynamoDB document dialect foundations

---

## What Makes It Different

Most agent frameworks provide tool infrastructure.

Ojas Data  provides governance content.

```text
Frameworks provide:
  - tool calling
  - function schemas
  - graph orchestration
  - agent loops

Ojas Data  provides:
  - authorization boundary
  - policy validation
  - safe query construction
  - credential isolation
  - masking before LLM visibility
  - audit evidence
```

Framework adapters are wrappers.

The  core is the enforcement authority.

---

## Architecture

```text
AI Agent / Framework
        |
        v
Registered Tool Descriptor
        |
        v
Use-Case Policy
        |
        v
Core Authorization Boundary
        |
        v
Safe Query Builder / Document Operation Builder
        |
        v
Masking + Audit + Credential Selection
        |
        v
Database / Document Store
```

---

## Three Registry Architecture

Ojas Data  is organized around three extension registries.

### 1. SQL Dialect Registry

For relational databases.

Supported / planned dialects include:

```text
MySQL
PostgreSQL
SQLite
SQL Server
```

SQLite is for development and testing only. It is refused in production because it does not support database-user or GRANT-based credential isolation.

### 2. Framework Adapter Registry

For AI-agent frameworks.

Supported / planned adapters include:

```text
Python dispatcher
CrewAI
OpenAI function calling
LangChain
LangGraph
```

Adapters convert native tool descriptors into framework-specific tools.

They do not enforce security directly.

### 3. Document Dialect Registry

For document and NoSQL-style systems.

Supported / planned dialects include:

```text
MongoDB
DynamoDB
```

Document dialects use path-based governance instead of column-based governance.

---

## Security Model

Ojas Data  enforces security through multiple layers.

```text
Layer 0:    Allowed resources
Layer 1:    Schema / structure discovery
Layer 2:    Global sensitive / masked policy
Layer 3:    Tool-to-use-case policy
Layer 3A:   Agent-to-tool policy
Layer 3.5:  Row / record / path scope
Layer 4:    Operation guardrails
Layer 5:    Safe query builder
Layer 6:    Output masking
Layer 7:    Audit logging
Layer 8:    Policy validation
Layer 9A:   Secret storage
Layer 9B:   Credential / privilege isolation
Layer 9C:   Secret leak prevention
Layer 10:   Backend capability validation
```

---

## Sensitive Values Never Reach the LLM

Ojas Data  masks protected values before they leave the governed .

```text
Raw email in database:
  ravi@example.com

LLM-visible output:
  ***@***
```

The model cannot leak raw values it never received.

---

## Example

User asks:

```text
Show Ravi's contact details.
```

The LLM selects:

```text
Tool: view_student_profile
```

The  checks:

```text
Is this agent allowed to call this tool?
Which use case does this tool map to?
Which table or collection is allowed?
Which fields are allowed?
Which fields are sensitive?
Which fields must be masked?
Which credential role should be used?
What audit event should be recorded?
```

The  may execute:

```sql
SELECT id, name, course, email
FROM students
WHERE name = ?
LIMIT ?
```

Then return:

```json
{
  "id": 10,
  "name": "Ravi",
  "course": "Computer Science",
  "email": "***@***"
}
```

The LLM never sees the raw email.

---

## Tool Descriptor Example

```python
ToolDescriptor(
    name="view_student_profile",
    usecase="view_student_profile",
    operation="read",
    args_schema=ViewStudentProfileArgs,
    llm_visible=True,
)
```

The tool descriptor is framework-neutral.

It can be exported to:

```text
Python dispatcher
CrewAI tool
OpenAI function schema
LangChain StructuredTool
LangGraph node
```

All paths call the same core dispatcher.

---

## Use-Case Policy Example

```yaml
usecases:
  view_student_profile:
    table: students
    operation: read
    lookup:
      - id
      - name
    read:
      - id
      - name
      - age
      - course
      - email
    write: []
    row_scope: tenant_scope
    max_rows: 1
```

---

## Agent Policy Example

```yaml
agents:
  database_agent:
    allowed_tools:
      - list_students
      - view_student_profile
      - create_student
      - update_student
    db_credential: agent_write
    max_rows: 50

  read_only_agent:
    allowed_tools:
      - list_students
      - view_student_profile
    db_credential: agent_read
    max_rows: 100
```

---

## Column Protection Example

```yaml
sensitive_columns:
  students:
    - password
    - ssn

masked_columns:
  students:
    email: email_mask
    marks: default_mask
```

Sensitive columns are never selected.

Masked columns are transformed before LLM visibility.

---

## Document Path Policy Example

```yaml
document_policies:
  users:
    sensitive_paths:
      - credentials.password_hash
      - identity.ssn

    masked_paths:
      profile.email: email_mask
      profile.phone: phone_mask

    usecases:
      view_user_profile:
        resource: users
        projection:
          - profile.name
          - profile.email
          - profile.phone
        filter_scope: tenant_scope
```

---

## Supported  Modes

### Normal Mode

LLM/framework-native tool selection.

```text
User text
  → LLM selects tool
  →  authorizes
  →  executes
```

### Keyword Mode

Deterministic keyword or synonym mapping.

```text
User text
  → keyword resolver
  → tool/field candidates
  →  authorizes
  →  executes
```

### Hybrid Mode

LLM proposes candidates and keyword resolver normalizes.

```text
User text
  → LLM proposes
  → keyword resolver normalizes
  →  authorizes
  →  executes
```

All modes are non-authoritative. Policy remains the authority.

---

## Installation

```bash
git clone https://github.com/Pommala-LLC/ojas-data-.git
cd ojas-data-

python -m venv .venv
source .venv/bin/activate

pip install -r requirements-test.txt
pip install -r requirements-flask.txt
```

For optional adapters:

```bash
pip install -r requirements-crewai.txt
pip install -r requirements-langchain.txt
pip install -r requirements-langgraph.txt
```

For optional backends:

```bash
pip install -r requirements-mysql.txt
pip install -r requirements-postgres.txt
pip install -r requirements-sqlserver.txt
pip install -r requirements-mongodb.txt
pip install -r requirements-dynamodb.txt
```

---

## Quick Start with SQLite

SQLite is for local development and testing.

```bash
export AGENT_DB=sqlite
export AGENT_ENV=development
export DB_SQLITE_PATH=./student_ai.db

python -m ojas_data_.entrypoints.bootstrap_sqlite ./student_ai.db
python -m ojas_data_.entrypoints.app
```

Then open:

```text
http://127.0.0.1:5000/admin
```

SQLite will be refused in production mode:

```bash
export AGENT_DB=sqlite
export AGENT_ENV=production
python -m ojas_data_.entrypoints.app
```

Expected behavior:

```text
BackendCapabilityError: SQLite cannot run in production
```

---

## Running Tests

```bash
pytest
```

Some integration tests are gated behind environment variables for real backends or LLM providers.

Examples:

```bash
OJAS_TEST_SQLSERVER_URL=...
OJAS_TEST_MONGODB_URL=...
OJAS_TEST_DYNAMODB_LOCAL_URL=...
OJAS_TEST_LANGCHAIN=1
OJAS_TEST_LANGGRAPH=1
```

---

## Optional Framework Adapters

### OpenAI Function Calling

Exports governed tool descriptors as function schemas.

```text
ToolDescriptor → OpenAI function schema → core dispatcher
```

### CrewAI

Wraps governed tool descriptors as CrewAI tools.

```text
CrewAI agent → CrewAI tool → core dispatcher
```

### LangChain

Wraps governed tool descriptors as LangChain `StructuredTool`s.

```text
LangChain agent → StructuredTool → core dispatcher
```

### LangGraph

Uses graph nodes for orchestration and approval.

```text
LangGraph node → governed tool node → core dispatcher
```

LangGraph may orchestrate approval.

The core  still authorizes and executes.

---

## Optional Backend Dialects

### SQL Dialects

```text
MySQL
PostgreSQL
SQLite
SQL Server
```

### Document Dialects

```text
MongoDB
DynamoDB
```

Document dialects use path-based governance rather than SQL-column governance.

---

## Audit Events

Every governed operation can produce a policy-versioned audit event.

Audit records may include:

```text
event_id
timestamp
correlation_id
policy_version
agent_id
tool_name
usecase_name
operation
resource_type
table_or_collection
backend_dialect
db_credential
decision
reason
requested_columns_or_paths
approved_columns_or_paths
blocked_columns_or_paths
masked_columns_or_paths
row_scope_or_filter_scope
query_fingerprint
result_count
sanitized_error
```

---

## What This Project Is Not

This project is not:

```text
A generic SQL agent
A prompt-only safety wrapper
A LangChain SQLDatabaseToolkit clone
A query checker
A database proxy
A replacement for database-level security
A replacement for IAM or secret management
```

It is a governed  that coordinates agent tools, policies, query construction, masking, credentials, and audit.

---

## Design Philosophy

```text
Frameworks provide infrastructure.
Ojas Data  provides governance content.
```

Frameworks decide how agents run.

Ojas Data  decides what data operations are allowed.

---

## Patent / Architecture Positioning

Ojas Data  is positioned around an integrated governed execution chain:

```text
agent identity
→ registered tool
→ use-case policy
→ row/path scope
→ safe SQL or document operation
→ pre-LLM masking
→ credential role
→ policy-versioned audit
```

The strongest technical distinction is:

```text
The LLM does not write executable SQL.
```

---

## Roadmap

### Current

```text
v6.5 — Registry-track closeout and architecture reconciliation
```

### Next

```text
v6.6 — Policy Authoring Layer
v6.7 — Annotation-first authoring
v6.x — Layer NL modes
v7   — Java / Spring Boot port
```

---

## Governance

The roadmap is planning guidance.

The project owner decides phase sequencing and scope.

The assistant should clarify ambiguous scope, then execute within the requested scope.

---

## License

Apache License 2.0.

See `LICENSE` for the full license text.

---

## Repository Naming

Recommended:

```text
Repo:        ojas-data-
Python pkg:  ojas_data_
CLI:         ojas-data
Docs title:  Ojas Data 
```
