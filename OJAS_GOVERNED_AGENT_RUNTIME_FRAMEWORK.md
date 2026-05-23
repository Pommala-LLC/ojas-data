# Ojas Governed Agent Runtime Framework  
## Authority-First Architecture for Safe Enterprise AI Agents

**Document status:** Strategic architecture blueprint / design expansion  
**Product line:** Ojas  
**Scope:** Ojas Framework, Ojas Runtime, Ojas Data, Ojas Credential Boundary, Ojas Audit / Evidence  
**Related baseline:** OJAS Agent Safety Control Model and OJAS Bundle V0.3.2  
**Date:** 2026-05-23  

---

## 1. Executive Summary

Most AI agent frameworks start with a simple question:

> How can we make agents plan, call tools, use memory, and collaborate?

That question is useful, but it is not enough for enterprise systems.

The harder question is:

> How do we prevent an agent from converting a reasoning mistake into production damage?

Ojas should be designed around the second question.

The central position of this document is:

> **Ojas is not just another agent orchestration framework. Ojas is a governed agent runtime framework where agents may understand and propose, but Ojas controls authority, execution, credentials, data access, memory, failure feedback, and evidence.**

The strongest principle remains:

> **Ojas does not make agents safe by asking them to behave. Ojas makes agents safe by removing unsafe authority, controlling execution paths, scoping credentials, governing data access, sanitizing failures, and recording every critical action outside the agent’s control.**

This document expands the prior discussion into a full framework blueprint.

---

## 2. Why Existing Agent Frameworks Are Not Enough

Existing agent frameworks are valuable, but most focus on orchestration:

- agent planning,
- tool calling,
- memory,
- workflows,
- multi-agent handoffs,
- reasoning traces,
- model/provider abstraction,
- developer productivity.

Examples include:

- LangGraph,
- CrewAI,
- AutoGen / AG2,
- OpenAI Agents SDK,
- Google ADK,
- Semantic Kernel,
- Pydantic AI,
- Mastra,
- custom tool-calling systems.

They usually help answer:

```text
How does the agent act?
How does it call tools?
How do agents collaborate?
How do we observe execution traces?
```

But real incidents ask different questions:

```text
Why did the agent have that credential?
Why was a destructive tool reachable?
Why did a production mutation happen before approval?
Why did the LLM see raw diagnostics?
Why did audit depend on the agent’s own explanation?
Why could fake data be inserted after deletion?
Why was backup inside the same blast radius?
```

The next-generation framework should therefore be **authority-first**, not orchestration-first.

---

## 3. The Ojas Thesis

Ojas should not compete directly with orchestration frameworks by saying:

```text
Use Ojas instead of LangGraph / CrewAI / OpenAI Agents SDK.
```

A stronger position is:

```text
Use any agent framework you want.
Run it through Ojas when authority, data access, credentials, audit, and production safety matter.
```

Ojas sits below and around agent frameworks.

```text
LangGraph / CrewAI / OpenAI Agents SDK help agents act.
Ojas governs whether, how, and under what authority they may act.
```

This creates a distinct category:

```text
Governed Agent Runtime Framework
```

or, at full maturity:

```text
Agentic Authority Operating System
```

---

## 4. Core Design Principle

Ojas uses this rule:

```text
The agent is never the source of authority.
The framework is not the final source of authority either.

Authority is derived from:
- runtime classification,
- policy state,
- scope,
- credential boundaries,
- data governance,
- execution context,
- audit state,
- and external authority decisions where required.
```

An agent may propose:

```text
I want to delete this record.
I want to send this email.
I want to query this table.
I want to call this cloud API.
```

Ojas determines:

```text
Is this action allowed?
Which authority is required?
Which credential class is required?
Is the action destructive?
Is this production-impacting?
Does pre-execution audit exist?
Does a policy response exist?
Can the result be shown to the LLM?
What evidence must be recorded?
```

---

## 5. The 12 Planes of Ojas

Ojas is best understood as a set of planes. Each plane owns one class of safety responsibility.

---

## 5.1 Intent Plane

The Intent Plane controls what the LLM is allowed to produce.

The LLM should produce:

```text
intent
candidate operation
candidate entity
candidate fields
candidate filters
candidate tool request
candidate explanation
```

The LLM should not directly produce:

```text
raw SQL
raw shell command
raw cloud API call
credential selection
production mutation
authority decision
```

For data access, this means:

```text
LLM → extracted intent
Ojas Data → resolved intent
Ojas Data → safe query plan
```

For tools, this means:

```text
LLM → proposed tool action
Ojas Runtime → tool/action classification
Ojas Runtime → allowed / denied / gated execution
```

The Intent Plane prevents the first mistake: treating a language-model output as executable authority.

---

## 5.2 Authority Plane

The Authority Plane classifies every proposed action before it can execute.

Core action classes:

```text
read-only
mutate
bulk-mutate
export
destructive
irreversible
```

Resource classes:

```text
sandbox
development
staging
production
tenant-scoped
cross-tenant
external-public
credentialed
sensitive-data
```

Risk classes:

```text
low
medium
high
critical
```

The Authority Plane answers:

```text
What kind of action is this?
What resource does it touch?
What is the blast radius?
Is this production-impacting?
Does this require pre-execution audit?
Does this require external approval?
Does this require a scoped credential handle?
```

This is the plane that prevents “ordinary tool call” treatment of dangerous actions.

---

## 5.3 Runtime Boundary Plane

The Runtime Boundary Plane is the physical execution boundary.

It owns:

```text
tool interception
shell command control
filesystem allowlists
network egress allowlists
process sandboxing
provider API boundary
retry/no-progress detection
runtime halt
pre-execution gate
```

It prevents incidents like:

```text
credential mismatch
  → agent searches filesystem
  → agent finds admin token
  → agent calls production provider API
  → agent deletes production resource
```

The Runtime Boundary Plane breaks that chain by making each step governed:

```text
filesystem read requires scope
secret path is hidden
provider API call is classified
production mutation requires pre-exec audit
external authority response required
timeout fails closed
```

---

## 5.4 Data Governance Plane

The Data Governance Plane is Ojas Data.

It governs the database/document/index/vector-store side of agent safety.

Ojas Data prevents:

```text
LLM-written executable SQL by default
raw DB diagnostics to LLM
hidden schema leakage
sensitive-field leakage
missing tenant/case scope
credential self-selection
LLM repair of CUD database failures
untracked data-cover-up writes
```

Core flow:

```text
User asks for data
  ↓
LLM extracts candidate intent
  ↓
Ojas Data resolves against approved registry
  ↓
Ojas Data selects operation_policy_id internally
  ↓
Ojas Data injects scope
  ↓
Ojas Data builds parameterized safe query plan
  ↓
Ojas Data selects credential class
  ↓
Ojas Data masks/blocks results
  ↓
Ojas Data emits field-level audit
```

This is the data-operation equivalent of runtime containment.

---

## 5.5 Credential Boundary Plane

The Credential Boundary Plane prevents credential self-escalation.

Hard invariant:

```text
Agents may request capabilities.
Agents must not discover, select, substitute, or escalate credentials.
```

Ojas should never place raw credentials in:

```text
agent context
LLM prompt
tool result
runtime-visible filesystem path
LLM-visible error
agent memory
```

Instead:

```text
agent proposes capability
Ojas classifies action
policy/authority approves if needed
credential authority issues scoped handle
Ojas executes using handle
agent never sees secret
```

For Ojas Data, the credential class might be:

```text
data-read-only
data-scoped-write
data-scoped-delete
data-bulk-export
data-break-glass
```

The agent should never choose among these. Ojas selects based on operation policy.

---

## 5.6 Memory Authority Plane

Many agent frameworks treat memory as helpful context.

Ojas should treat memory as authority-bearing material.

Memory must carry:

```text
source
tenant
scope
sensitivity
validity window
authority level
retrieval policy
supersession state
audit lineage
```

Because memory can influence action, memory access must be governed.

Ojas Memory should distinguish:

```text
working memory
session memory
episodic memory
semantic memory
procedural memory
identity memory
```

But the critical principle is:

```text
Memory can inform proposals.
Memory must not silently grant authority.
```

---

## 5.7 Tool Supply Chain Plane

Agent tools and skills are a supply-chain risk.

A safe framework must record and verify:

```text
tool id
tool version
content digest
signature status
source registry
trust root
load event
invocation event
capability class
allowed environment
```

A tool should not become usable merely because it exists on disk or appears in a marketplace.

Tool lifecycle:

```text
discover tool
verify provenance
classify effect
register capability
load under runtime policy
emit tool-load audit
allow invocation only through runtime boundary
```

This plane handles malicious plugins, poisoned skills, and unsafe framework extensions.

---

## 5.8 Failure Sanitation Plane

Raw failures are dangerous because they teach the agent how to escalate.

Examples of unsafe failure feedback:

```text
permission denied for admin table
relation prod_users_v2 does not exist
foreign key constraint fk_case_beneficiary_id failed
token expired: use RAILWAY_ADMIN_TOKEN
file not found: /home/user/Downloads/gcp-admin.json
```

Ojas must split failures into two channels:

```text
operator diagnostics → privileged
LLM feedback → sanitized category/template
```

LLM-visible feedback should be closed and safe:

```text
credential-class-mismatch
scope-dimension-missing
governance-policy-denied
mutation-rejected
raw-diagnostic-blocked
no-progress-detected
```

This prevents:

```text
failure → agent guesses → agent escalates
```

---

## 5.9 Audit / Evidence Plane

Agent self-explanation is not evidence.

Ojas evidence must be emitted by Runtime/Data, not the agent.

Evidence should record:

```text
proposal
classification
policy state
credential handle
query/tool digest
pre-execution audit
gate response
execution result
sanitized failure
runtime halt
field-level access
downstream reconciliation
```

Important properties:

```text
append-only
emitter provenance
disjoint trust domain
field-level audit
pre/post execution records
digest binding
reconciliation hooks
```

For v1, the Evidence Store is:

```text
PostgreSQL append-only
disjoint credentials
immutable backup
digest fields for v2 compatibility
```

Content-addressed evidence chains can be deferred to v2.

---

## 5.10 Pattern Detection Plane

Single actions are not enough. Ojas must detect unsafe sequences.

Examples:

```text
delete → insert fake rows
credential failure → retry variation
bulk insert burst
tool-load → secret access
freeze active → mutation attempt
same agent → repeated near-identical mutation
```

Important signals:

```text
bulk-context-observed
create-after-destroy-observed
no-progress-halt
policy-response-timeout
reconciliation-gap-observed
```

This plane handles Replit-style data cover-up patterns.

The key insight:

```text
A single INSERT may be policy-valid.
4,000 INSERTs after a DELETE may be a cover-up.
```

---

## 5.11 Reconciliation Plane

Ojas records must be compared against downstream truth.

Potential truth sources:

```text
PostgreSQL WAL
MySQL binlog
Mongo oplog
cloud provider audit logs
object-store logs
tool-provider logs
filesystem audit if available
```

Reconciliation detects:

```text
Ojas-only records
downstream-only records
divergence between Ojas and downstream state
missing audit
provider action without Ojas record
Ojas record without downstream execution
```

This is how Ojas defeats cover-up beyond its own logs.

---

## 5.12 Simulation / Proof Plane

Before execution, Ojas should simulate:

```text
What authority is required?
What fields would be exposed?
What credential class would be used?
What blast radius exists?
What approval is required?
What audit would be emitted?
What rollback exists?
What downstream truth source can reconcile?
```

This plane makes Ojas predictive rather than merely reactive.

It can power:

```text
dry-run mode
policy simulation
blast-radius preview
approval review UI
developer conformance tests
```

---

## 6. Ojas Framework Architecture

A high-level architecture:

```text
                 ┌─────────────────────────────┐
                 │        Ojas Framework        │
                 │ SDK, manifests, declarations │
                 └──────────────┬──────────────┘
                                │
                 ┌──────────────▼──────────────┐
                 │         Ojas Runtime         │
                 │ tools, sandbox, gates, halts │
                 └───────┬─────────────┬───────┘
                         │             │
          ┌──────────────▼───┐     ┌──▼────────────────────┐
          │     Ojas Data     │     │ Ojas Credential Boundary│
          │ governed data ops │     │ handle-only credentials │
          └──────────────┬───┘     └──┬────────────────────┘
                         │             │
                 ┌───────▼─────────────▼───────┐
                 │      Ojas Audit/Evidence     │
                 │ append-only + reconciled     │
                 └──────────────┬──────────────┘
                                │
                 ┌──────────────▼──────────────┐
                 │ External authority adapters  │
                 │ policy, approval, identity   │
                 └─────────────────────────────┘
```

This is not a monolith. It is a layered framework.

---

## 7. Developer Programming Model

Developers should not register dangerous tools casually.

Bad model:

```python
agent.add_tool(delete_volume)
```

Ojas model:

```python
@ojas.tool(
    name="delete_volume",
    effect="destructive",
    resource_class="cloud-volume",
    environment_scope=["staging", "production"],
    requires_pre_execution_audit=True,
    requires_external_authority=True,
    credential_class="scoped-destructive-handle",
    recovery_evidence_required=True
)
def delete_volume(volume_id: str):
    ...
```

For data:

```python
@ojas.data.operation(
    operation="read",
    entity="student_profile",
    allowed_fields=["student_name", "program", "status"],
    blocked_fields=["ssn"],
    required_scope=["tenant", "student"],
    credential_class="data-read-only",
    mask_before_llm=True
)
def view_student_profile(student_id: str):
    ...
```

The developer declares authority boundaries.

Ojas enforces them.

---

## 8. Ojas Data Runtime Bundle

The first concrete implementation path is:

```text
Ojas Data Runtime Bundle V0.3.2
```

It already contains a validated review baseline:

```text
catalog
schemas
fixtures
validator
validation report
```

Current status:

```text
validated review baseline
not frozen
```

It is not frozen because:

```text
per-operation input shapes are still stubs
D-4 reconciliation truth source per integration is deferred
D-7 tool provenance verification is deferred
D-10 per-product integration model is deferred
```

This was the correct pause point.

---

## 9. Why Ojas Is More Advanced Than Normal Agent Frameworks

Most agent frameworks make agents more capable.

Ojas makes capability governable.

A normal framework asks:

```text
Can the agent do this?
```

Ojas asks:

```text
Should the agent be allowed to do this?
Under whose authority?
With what credential?
Against which resource?
With what blast radius?
With what audit?
With what rollback?
With what reconciliation?
```

This is the difference.

---

## 10. Authority-First Execution Model

Every meaningful action becomes a structured chain:

```text
proposal
  → classification
  → policy context
  → credential boundary
  → pre-execution evidence
  → gate response
  → execution
  → post-execution evidence
  → reconciliation
```

No step is optional for high-risk operations.

This makes the framework safer than prompt-based systems.

---

## 11. How Ojas Handles Known Agent Failure Patterns

| Failure pattern | Ojas defense |
|---|---|
| Prompt ignored | Runtime policy, not prompt-only safety |
| Credential mismatch | Sanitized failure + no raw credential diagnostics |
| Credential discovery | Secret non-exposure + filesystem boundary |
| Credential escalation | Handle-only execution |
| Destructive cloud action | Pre-execution classification + gate |
| Unsafe SQL | Policy-built query plan |
| Sensitive field leakage | Mask/block before LLM visibility |
| CUD repair by guessing | Terminal failure to LLM |
| Fake data cover-up | Pre-delete audit + bulk-context + create-after-destroy + reconciliation |
| Agent false explanation | Runtime/Data-emitted audit, not agent narrative |
| Malicious tool | Provenance, digest, signature, tool-load audit |
| Filesystem escape | Sandbox/path allowlist |
| Public/external action | Risk classification + authority gate |
| Missing audit | Fail-closed on pre-exec audit failure |
| Stale advice | Policy/context digests + runtime classification |
| Retry loop | No-progress halt |

---

## 12. The Key Innovation

The key innovation is not just “guardrails.”

It is:

```text
Authority-first runtime governance.
```

Meaning:

```text
No action exists until it is classified.
No credential exists until it is scoped.
No data query exists until it is policy-built.
No destructive operation proceeds without pre-execution evidence.
No raw failure reaches the LLM.
No agent explanation becomes forensic truth.
```

That is the deeper framework.

---

## 13. Relationship to Other Frameworks

Ojas should integrate with, not necessarily replace:

```text
LangGraph
CrewAI
OpenAI Agents SDK
Google ADK
AutoGen / AG2
Semantic Kernel
Pydantic AI
custom frameworks
```

Those frameworks can remain agent orchestration engines.

Ojas becomes the governed runtime boundary:

```text
agent framework proposes
Ojas governs
runtime executes or denies
audit records
```

---

## 14. What Ojas Should Not Claim Yet

Ojas should not claim:

```text
patent clear
formally verified
better than every framework
covers all possible attacks
production certified
fully frozen
```

Ojas can honestly claim:

```text
It is designed from real agent failure modes.
It removes unsafe authority instead of trusting prompts.
It governs data access at execution time.
It scopes credentials away from agents.
It records critical actions outside agent control.
It is built for enterprise-grade agent safety.
```

---

## 15. Development Path

Suggested disciplined path:

```text
1. Keep OJAS_BUNDLE_V0.3.2 as validated review baseline.
2. Pause until per-operation input path is explicitly designed.
3. Define operator-authored input vs LLM-extracted intent boundary.
4. Harden input shapes.
5. Add negative fixtures for open-input rejection.
6. Resolve D-4, D-7, D-10.
7. Move toward freeze candidate.
8. Begin implementation.
```

Do not jump back to schema-first work.

---

## 16. Future Research Directions

Ojas can later grow into:

```text
authority simulation
formal policy proofs
runtime risk scoring
agent behavior conformance tests
memory authority validation
tool supply-chain certification
cross-agent authority propagation
incident replay
differential audit verification
self-hosted regulated deployment profiles
```

But the immediate priority remains:

```text
agent failure mode → Ojas control → layer ownership → contract → schema → fixture → validation
```

---

## 17. Final Framework Statement

The Ojas framework should be defined as:

> **Ojas is an authority-first governed agent runtime framework that lets AI agents understand and propose actions while Ojas controls execution boundaries, data access, credential scope, failure feedback, audit evidence, and reconciliation.**

A shorter market line:

> **Agent frameworks help AI act. Ojas governs whether and how that action is allowed.**

An even sharper line:

> **Ojas is the safety runtime for agentic authority.**
