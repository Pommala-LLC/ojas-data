# Ojas Data — Positioning (v1.0)

This document captures the product positioning for Ojas Data: the category position, the developer experience, the three-altitude messaging, and the analysis of why the gap Ojas Data fills exists in current frameworks.

For architecture, see [`OJAS_DATA_RESOLVER_SCOPE.md`](./OJAS_DATA_RESOLVER_SCOPE.md) and [`OJAS_DATA_QUERY_REPAIR_BOUNDARY.md`](./OJAS_DATA_QUERY_REPAIR_BOUNDARY.md). For developer onboarding, see [`OJAS_DATA_DEVELOPER_GUIDE.md`](./OJAS_DATA_DEVELOPER_GUIDE.md).

---

## 1. Tagline and short positioning

### Tagline

> **Ojas Data — Retry that respects authority.**

### Short positioning

> **Ojas Data is the governed data-access layer for AI agents in regulated enterprises.**

### Three-altitude messaging

The positioning operates at three altitudes, each answering a different question for a different reader:

**Category position (analyst altitude):**
> General agent frameworks optimize for flexible execution. Ojas Data optimizes for governed enterprise data access. It complements those frameworks by adding the deterministic authority layer they intentionally leave to the application.

**Architectural principle (architect altitude):**
> Ojas Data discovers your schema automatically. Developers decide what is safe, visible, masked, scoped, and governed. Annotations generate the registry; the compiled registry governs runtime.

**Developer experience (engineer altitude):**
> Ojas Data scans your database, generates governed entity definitions, flags sensitive/scope fields, suggests aliases, and builds the safe runtime registry after developer approval.

---

## 2. Five product pillars

### Pillar 1 — Closed-world data authority

Ojas Data treats the compiled metadata registry as the only runtime authority for what data the LLM can see. A column that exists in the database but is not in the registry is, from the system's perspective, nonexistent. This is the foundation: every other guarantee derives from this one.

### Pillar 2 — Annotation-driven developer experience

Developers do not hand-write the runtime registry. They annotate their domain model (or accept scanner-generated drafts) and approve what is exposed. The compile step transforms approved annotations into immutable runtime authority. The developer's surface is small; the system's safety surface is large.

### Pillar 3 — Sanitized LLM-facing channels

The LLM never sees raw database errors, hints, physical identifiers, constraint names, candidate sets, or sensitive values. The privileged diagnostic classifier sits at the boundary, translating raw runtime artifacts into registry-derived safe forms or suppressing them entirely.

### Pillar 4 — Discriminator-first retry

Ojas Data classifies failures before deciding whether to retry. Extraction failures may be repaired by the LLM. Authority failures (resolver, scope, policy, sensitivity, credential, mutation) are terminal and never retried by the LLM. The LLM never probes the authorization surface by retrying into guaranteed failures.

### Pillar 5 — Audit-ready by default

Every LLM-facing emission carries an audit triple: profile ID and version, schema ID, envelope fingerprint. Every database interaction is filtered through the privileged diagnostic classifier. Every compile step produces reviewable artifacts. The system is auditable by construction, not by retrofit.

---

## 3. Category-gap analysis — why this gap exists in current frameworks

The gap Ojas Data fills is not an oversight by other frameworks. It is structural to their product missions. Understanding why is what makes the positioning durable rather than something competitors can close in a release cycle.

General-purpose agent frameworks — LangChain, LangGraph, OpenAI Agents SDK, LlamaIndex, CrewAI, Pydantic AI — are optimized for *"make agents useful, flexible, and easy to build."* Ojas Data is optimized for *"make agent data access deterministic, governed, auditable, and safe under enterprise constraints."* These are different product missions, and the eight reasons below trace how each mission produces its own design choices.

### 3.1 Primary abstraction: agent vs. data-authority layer

General frameworks center on agent orchestration: tool calls, handoffs, workflows, loops, retries, state, tracing, output validation. The OpenAI Agents SDK describes its agent loop as the LLM running, producing tool calls, observing results, and continuing until final output or `max_turns` is exceeded. LangGraph describes itself as a low-level orchestration framework for long-running, stateful agents.

Their center of gravity is:

```
LLM → tool call → observe result → try again
```

Ojas Data's center of gravity is different:

```
LLM extraction → deterministic resolver → policy/scope/credential gates → approved data operation
```

The frameworks did not build Ojas-style resolver authority because resolver authority is not their primary abstraction.

### 3.2 Default-flexible vs. default-governed

General frameworks treat governance as **opt-in**, configured by the application developer through database permissions, prompt engineering, output validation, and human review steps. Ojas Data treats governance as **structural**, enforced by the platform before any application code runs. Both can produce governed outcomes when fully configured; the difference is whether governance is the *default* or the *configured-in* state.

A general-purpose framework that makes ambiguity terminal, blocks raw SQL repair, forbids many retries, and requires approved registries by default would lose the prototyping, chatbot, RAG, and research-demo segments that produce most of its adoption.

### 3.3 Security responsibility pushed to application and database layer

The frameworks state their security stance directly:

- LlamaIndex's text-to-SQL documentation warns that executing arbitrary SQL is a security risk and recommends restricted roles, read-only databases, and sandboxing as user-applied mitigations.
- LangChain's SQL agent reference notes that the agent can execute arbitrary SQL against the configured database; the framework relies on the SQL database itself to manage permissions.
- LangChain's security documentation says applications should limit agents to specific directories, give read-only API keys, and run agents in containers — all application-level mitigations.

Their stance is: *"We provide the agent and tool mechanism. You secure the DB connection, permissions, sandbox, and deployment."*

This is a defensible engineering choice for a general-purpose framework. Pushing security down lets one framework serve many database engines, permission models, and compliance regimes without taking a position on any of them. It is not an oversight — it is the consequence of being a framework that aims to be universal.

Ojas Data's stance is different: the framework itself owns the data-access authority boundary before execution.

### 3.4 Closed-world metadata is platform-grade work

Ojas Data requires an approved metadata registry, a compile step, introspection reconciliation, drift reports, scope dimensions, aliases, sensitivity flags, policy visibility, and conformance tests. That is powerful, but it adds real platform work.

For a general framework to impose this, it would have to own metadata lifecycle, schema governance, tenant overrides, drift management, safe alias authoring, policy integration, audit records, and approval workflows. Those responsibilities are heavy. A general-purpose framework cannot easily impose them without becoming an enterprise data-governance platform — which is a different product.

### 3.5 Raw-error retry works in low-stakes contexts

Giving the LLM raw DB errors works well in many real situations, not only demos:

```
column X does not exist → maybe use column Y → retry → success
```

This pattern is genuinely useful in CRUD-on-internal-tooling, developer-self-service analytics, and exploration of open data. The risk surface is acceptable when the database does not contain regulated data, when the database role has narrow permissions, or when the use case is interactive rather than autonomous.

The framework cannot tell low-stakes from high-stakes. It does not know whether the database it is querying contains customer SSNs or open-source documentation. So it defaults to the flexible behavior, and the application developer is supposed to constrain it for sensitive deployments. That default is reasonable for a general framework.

Ojas Data intentionally refuses the shortcut because regulated enterprise data access cannot rely on "the application developer will constrain it correctly."

### 3.6 Read-only vs CUD distinction requires data-platform semantics

Most agent frameworks treat tools generically. A tool is a tool. The framework may not deeply know whether a tool call is `SELECT`, `INSERT`, `UPDATE`, `DELETE`, an external API `POST`, an email send, a file write, or a payment operation.

To implement Ojas's CUD-never-LLM-repairable rule, the platform must understand mutation semantics, preflight checks, transaction policy, associations, version conflicts, uniqueness, tenant scope, and rollback behavior. That is beyond normal agent orchestration. It belongs to an enterprise data platform.

### 3.7 Composability vs. opinionated governance

Frameworks generally say: *"Use our components, add your own middleware, wrap your tools, configure your database, add guardrails."* That is composable and ecosystem-friendly.

Ojas Data is more opinionated:

- no unknown metadata
- terminal ambiguity
- no LLM authority repair
- no raw DB diagnostics to LLM
- registry-owned scope
- CUD never LLM-repairable
- audit every retry

This is stronger but less universal. It does not slot into arbitrary application architectures the way LangChain components do. That is a trade-off Ojas Data accepts because the target user — a regulated enterprise data deployment — values the opinionation.

### 3.8 Market timing — first-generation vs. second-generation problem

The ecosystem first solved: how to call tools, how to orchestrate agents, how to use memory, how to do RAG, how to parse structured output, how to retry failed actions.

Enterprises are now discovering the second-generation problem: *how do we let agents touch real business data without leaking schema, violating policy, or corrupting records?* Ojas Data is addressing that second-generation problem. The first-generation frameworks did not address it because it was not yet visible as a separate problem when they were designed.

### 3.9 What this means for positioning

The eight reasons above point to one conclusion: this is a category gap, not a feature gap. It is durable because the underlying choices are not arbitrary — they are forced by each framework's product mission. LangChain catching up to Ojas Data on governance would require LangChain to abandon its commercial position as a flexible general-purpose framework. They will not do that, because their commercial position is what produces their adoption.

The same logic that makes platform-vs-tool differentiation durable in other software categories applies here. Salesforce did not become Excel; Excel did not become Salesforce. Each product's mission constrains the design choices that produce its differentiation.

---

## 4. Competitive comparison

### 4.1 What general frameworks provide

The frameworks provide:

| Capability | Common in market |
|---|---|
| Retry malformed structured output | Yes (LangChain `RetryWithErrorOutputParser`, Pydantic AI `ModelRetry`, Guardrails `num_reasks`) |
| Tool retry / model retry | Yes (most frameworks) |
| SQL agent retries after DB error | Yes (LangChain SQL agent, LlamaIndex text-to-SQL) |
| Loop limits / max turns / recursion limits | Yes (LangGraph recursion, OpenAI Agents SDK `max_turns`, Pydantic AI usage limits) |
| Dual/quarantined LLM security | Emerging pattern (Simon Willison's Dual LLM, CaMeL) |

### 4.2 What Ojas Data adds

| Capability | Ojas Data position |
|---|---|
| Closed-world metadata registry | Core differentiator |
| Terminal resolver ambiguity | Core differentiator |
| Registry-owned row-scope columns | Core differentiator |
| CUD never LLM-repairable | Strong differentiator |
| Failure-enum-driven retry eligibility | Central to data access |
| Raw DB diagnostics blocked from LLM | Applied directly to SQL/data access |
| Privileged diagnostic classifier | Boundary component |
| Schema-first prompt contracts | Versioned, audited, validated |

### 4.3 What Ojas Data does not replace

Ojas Data does not replace framework-level retries for:

- Transient model/provider failures
- HTTP/network timeouts
- Structured-output parse failures (the framework's job, not Ojas Data's)
- Graph-node retries (LangGraph, etc.)
- External API backoff

These remain the responsibility of the orchestration framework. Ojas Data sits underneath the framework, owning the data-access authority boundary.

---

## 5. The developer journey

### 5.1 What adoption looks like

```
Install Ojas Data and configure database connection
  ↓
Run ojas-data scan to discover and draft entity definitions
  ↓
Review the generated drafts: approve aliases, classify sensitivity, set scope
  ↓
Run ojas-data compile to produce the immutable runtime registry
  ↓
Application code uses the compiled registry through the resolver
  ↓
When schema changes, re-run scan; the overlay survives, drift reports highlight changes
```

Six steps. A team can adopt Ojas Data on a Monday morning, scan their schema by lunch, review the flagged fields in the afternoon, and have a compiled registry running by end of day for a typical mid-sized application.

### 5.2 What this avoids

Adoption does not require:

- Hand-writing entity classes
- Hand-authoring annotations for every field
- Building a custom retry framework
- Engineering safe error messages from raw DB errors
- Building tenant scope filtering from scratch
- Writing custom audit trails for LLM-data interactions
- Implementing prompt versioning manually

The scanner generates drafts; the developer approves meaning; the compiler enforces safety; the runtime audits everything by construction.

### 5.3 The two-role split

Ojas Data assumes two roles:

- **Application developers** integrate by reviewing scanner-generated entity definitions and approving the business meaning. Their surface is the overlay file.
- **Platform operators / data stewards** author the policy, sensitivity, alias, and scope conventions that the developer review draws on. They review compiled artifacts and approve changes.

Both roles exist in Spring Data + Spring Security deployments today, in JPA + role-based access control deployments, and in any mature enterprise data platform. Ojas Data follows the same pattern.

---

## 6. Target buyers and users

### 6.1 Buyer profile

Ojas Data is for organizations that need AI agents to be operationally safe when touching production data:

- **Regulated enterprises** — banks, insurance, healthcare, immigration services, payment processors
- **Multi-tenant SaaS** — where tenant data isolation is a regulatory and contractual requirement
- **Compliance-sensitive teams** — those subject to GDPR, HIPAA, SOX, PCI-DSS, or industry-specific data handling rules
- **Enterprise platforms** — internal AI deployments where audit trails matter as much as the AI's outputs

### 6.2 User profile

The day-to-day users are:

- **Platform engineering teams** who own the data layer
- **Security architects** who review what the LLM can see
- **Data stewards** who classify what data is sensitive
- **Application developers** who integrate AI features against this safe foundation

### 6.3 When Ojas Data is not the right fit

Ojas Data is not the right fit for:

- **Prototyping and demos** — the closed-world model adds friction that prototypes don't need
- **Open-data exploration** — where raw schema discovery is desirable, not a security risk
- **Single-developer projects** — the two-role split is overhead when one person owns everything
- **Non-regulated SaaS with low-stakes data** — general frameworks are simpler and sufficient

Naming these explicitly prevents adoption mismatch. Ojas Data is opinionated; the opinions pay off in regulated contexts and create friction in unregulated ones.

---

## 7. Strategic posture

### 7.1 Internal-first for v1.0

Ojas Data is **internal-first** for the next 12–18 months. It is built primarily as the governed data-access layer for Pommala's own platform deployments. Standalone packaging is milestone-gated, not promised by default.

### 7.2 Standalone milestone criteria

Ojas Data becomes packageable as a standalone product when all of the following are true:

1. The four LLM-facing safety freezes are operationally enforced across at least two production deployments
2. The privileged diagnostic classifier has been reviewed by an external security audit
3. The conformance suite covers all freeze rules with documented test cases
4. At least two domain packs (PDF/JRXML, HireFlux, or others) are using Ojas Data in production
5. The scanner has been validated against at least three database engines (PostgreSQL, plus two of MySQL/SQL Server/Oracle)
6. The CLI exit-code contract has been validated through real CI integration in production deployments
7. Deferred design topics from [`OJAS_DATA_DEFERRED_DESIGN_TOPICS.md`](./OJAS_DATA_DEFERRED_DESIGN_TOPICS.md) have known holding positions that survive external review

### 7.3 What this implies

The internal-first posture means:

- v1.0 documentation is for internal teams and reviewers, not yet for external developers
- Production hardening happens through internal deployments first
- External developer experience polish (IDE integrations, tutorial content, sample applications) is deferred to post-standalone
- Sales and analyst conversations focus on Pommala-internal value, not yet on broad market adoption

---

## 8. Website hero (when standalone packaging arrives)

```
Ojas Data
Retry that respects authority.

The governed data-access layer for AI agents in regulated enterprises.

Ojas Data scans your database, generates governed entity definitions,
flags sensitive and scope fields, suggests aliases, and builds the safe
runtime registry after developer approval. The LLM never sees raw schema,
raw errors, or sensitive values. Every interaction is auditable by
construction.

Built for regulated enterprise data access.
Complementary to general agent frameworks.
```

---

## Appendix A — Positioning frozen principles

1. Ojas Data is a category-different product from general agent frameworks, not a feature-different one
2. The differentiation is durable because it derives from product-mission choices, not implementation choices
3. The three-altitude messaging (analyst, architect, engineer) provides distinct entry points for distinct readers
4. The five product pillars (closed-world authority, annotation-driven DX, sanitized channels, discriminator-first retry, audit by default) define the value surface
5. The internal-first posture is deliberate — standalone packaging is milestone-gated
6. The target buyer is regulated enterprise; non-regulated contexts are explicitly not the fit
7. Competitor catch-up is structurally difficult because it would require those competitors to abandon their commercial position
8. The positioning does not require any competitor to be wrong; it requires only that they have a different product mission
