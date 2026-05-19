# Ojas Data — Supported and Planned Frameworks / Databases

**Canonical line:** LLM understands the request, but policy controls execution.

This document lists only the frameworks, databases, and storage backends that are **currently supported** or **planned** for Ojas Data. It does not describe general support across external AI frameworks.

---

## 1. Framework Support

### Currently Supported

| Framework / Adapter | Status | Notes |
|---|---|---|
| Python Dispatcher | Supported | Direct runtime invocation path. No LLM framework required. |
| OpenAI Function Calling | Supported | Exports governed tool descriptors as function/function-call schemas. Execution still routes through Ojas Data core. |
| CrewAI | Supported | CrewAI tools wrap Ojas Data governed tool descriptors. Optional dependency. |
| LangChain | Supported | LangChain `StructuredTool` adapter routes tool execution through Ojas Data core. Optional dependency. |
| LangGraph | Supported | LangGraph adapter supports governed tool execution and approval workflow patterns. Optional dependency. |

### Planned / Future

| Framework / Adapter | Planned Phase | Notes |
|---|---|---|
| LlamaIndex | Future | Candidate adapter for RAG/data-indexing workflows. |
| AutoGen | Future | Candidate adapter for multi-agent orchestration. |
| MCP-style Tool Gateway | Future | Candidate gateway/export pattern for external tool ecosystems. |
| Java / Spring Boot | v7 reference/future | Future port, gated by Python stability and customer demand. |

---

## 2. SQL Database Support

### Currently Supported

| Database | Status | Notes |
|---|---|---|
| MySQL | Supported | Production-capable SQL dialect with role/credential separation. |
| PostgreSQL | Supported | Production-capable SQL dialect with role/credential separation. |
| SQLite | Supported for development/testing only | Refused in production because it does not support DB users or GRANT-based credential isolation. |
| SQL Server | Supported | Added under the SQL dialect registry. Production-capable when configured with least-privilege roles. |

### Planned / Future

| Database | Planned Phase | Notes |
|---|---|---|
| MariaDB | Future | Likely compatible with the MySQL-style SQL dialect path. |
| Oracle | Future | Requires separate SQL dialect and privilege/bootstrap handling. |

---

## 3. Document / NoSQL Database Support

### Currently Supported

| Database / Store | Status | Notes |
|---|---|---|
| MongoDB | Supported | Document dialect with path-based governance. |
| DynamoDB | Supported | Document/attribute dialect with IAM-aware capability model and sessions demo domain. |

### Planned / Future

| Database / Store | Planned Phase | Notes |
|---|---|---|
| Firestore | Future | Candidate document-store dialect. |
| Couchbase | Future | Candidate document/JSON dialect. |
| Cassandra / Astra DB | Future | Candidate wide-column/document-style backend if customer demand appears. |

---

## 4. Vector / Retrieval Store Support

### Currently Supported

| Store | Status | Notes |
|---|---|---|
| None as first-class Ojas Data dialect | Not yet supported | Vector/RAG support is currently planned, not part of the current core support matrix. |

### Planned / Future

| Store | Planned Phase | Notes |
|---|---|---|
| PostgreSQL + pgvector | Future | Best likely first vector/retrieval backend because PostgreSQL is already supported. |
| Qdrant | Future | Candidate dedicated vector database. |
| Milvus / Zilliz | Future | Candidate large-scale vector backend. |
| Weaviate | Future | Candidate semantic/vector backend. |
| Pinecone | Future | Candidate managed vector backend. |
| Redis Vector | Future | Candidate for fast cache + vector retrieval workloads. |
| Elasticsearch / OpenSearch Vector | Future | Candidate for combined text/vector search and audit search. |

---

## 5. Cache / Session / Memory Store Support

### Currently Supported

| Store | Status | Notes |
|---|---|---|
| None as first-class Ojas Data memory backend | Not yet supported | Session/cache/memory backend support is planned separately from SQL/document data access. |

### Planned / Future

| Store | Planned Phase | Notes |
|---|---|---|
| Redis | Future | Candidate for session memory, short-term state, cache, rate limits, and semantic cache. |

---

## 6. Analytics / Audit Store Support

### Currently Supported

| Store | Status | Notes |
|---|---|---|
| SQL audit table | Supported | Audit events can be stored in the configured SQL backend. |

### Planned / Future

| Store | Planned Phase | Notes |
|---|---|---|
| OpenSearch | Future | Candidate for audit/event search and trace search. |
| Elasticsearch | Future | Candidate for audit/event search and full-text search. |
| ClickHouse | Future | Candidate for high-volume audit analytics and observability. |

---

## 7. Streaming / Event Systems

### Currently Supported

| System | Status | Notes |
|---|---|---|
| None as first-class Ojas Data streaming backend | Not yet supported | Streaming/event integration is future work. |

### Planned / Future

| System | Planned Phase | Notes |
|---|---|---|
| Kafka | Future | Candidate for governed event streams, audit streams, and embedding/event pipelines. |
| Redpanda | Future | Kafka-compatible candidate. |
| Apache Pulsar | Future | Candidate event-streaming backend. |

---

## 8. Support Summary

### Current Support

```text
Frameworks:
  - Python Dispatcher
  - OpenAI Function Calling
  - CrewAI
  - LangChain
  - LangGraph

SQL Databases:
  - MySQL
  - PostgreSQL
  - SQLite for dev/test only
  - SQL Server

Document / NoSQL:
  - MongoDB
  - DynamoDB

Audit:
  - SQL audit table
```

### Planned Future Support

```text
Frameworks:
  - LlamaIndex
  - AutoGen
  - MCP-style tool gateway
  - Java / Spring Boot

SQL Databases:
  - MariaDB
  - Oracle

Document / NoSQL:
  - Firestore
  - Couchbase
  - Cassandra / Astra DB

Vector / Retrieval:
  - PostgreSQL + pgvector
  - Qdrant
  - Milvus / Zilliz
  - Weaviate
  - Pinecone
  - Redis Vector
  - Elasticsearch / OpenSearch Vector

Cache / Memory:
  - Redis

Analytics / Audit:
  - OpenSearch
  - Elasticsearch
  - ClickHouse

Streaming:
  - Kafka
  - Redpanda
  - Apache Pulsar
```

---

## 9. Positioning

Existing AI frameworks and data tools provide connectivity.

**Ojas Data provides governed execution.**

The supported and planned integrations should continue to follow this rule:

```text
Frameworks are adapters.
Databases are dialects.
Policy remains the authority.
The LLM never gets raw execution power.
```
