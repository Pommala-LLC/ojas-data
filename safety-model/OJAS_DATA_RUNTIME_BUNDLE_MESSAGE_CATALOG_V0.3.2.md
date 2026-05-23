# Ojas Data Runtime Bundle — Message Catalog v0.3.2

| Field | Value |
|---|---|
| Status | Review-correction draft, supersedes v0.3.1 |
| Freeze status | Not frozen |
| Parent document | OJAS_AGENT_SAFETY_CONTROL_MODEL.md (freeze candidate) |
| Schema language | Neutral. JSON Schema artifacts derived later per parent Section 10. |
| Scope | Ojas Data v1 Runtime Bundle: data-core, runtime-data, evidence-core, credential-boundary-adapter |
| Date | 2026-05-23 |
| Owner | SPHUTA / Ojas |
| Supersedes | v0.3.1 of this catalog (preserved for lineage; this revision resolves O-1 through O-5 and patches two small wording issues) |
| Lineage | Ojas Data CDDL v0.2 → catalog v0.3 → catalog v0.3.1 → catalog v0.3.2 |
| Applies | Seven v0.3 deltas (§10.1) + five v0.3.1 corrections (§10.2) + five v0.3.2 open-item resolutions (§10.4) |

---

## 0. Purpose and reading guide

This catalog defines the messages that cross every governed boundary in the Ojas Data v1 Runtime Bundle. It is **schema-language-neutral** — JSON Schema artifacts are derived from this catalog downstream, per the parent document's Section 10 sequencing.

The catalog is organized by **module boundary**, not by message type. Each section covers the messages owned by one module in the v1 bundle. A message is "owned" by the module that emits it or that mandates its shape.

**Reading order:** Section 1 (request context and common primitives) is required reading for every other section. Sections 2–9 can be read in any order, but the dependency graph is:

```
common (§1) ─┬──→ data-core (§2) ──┬──→ runtime-data (§3) ──→ evidence-core (§5)
             ├──→ credential-boundary-adapter (§4) ──→ evidence-core (§5)
             └──→ bulk/create-after-destroy signals (§6) ──→ evidence-core (§5)
                                                              │
                                                              ▼
                                                       reconciliation hooks (§7)
                                                              │
                                                              ▼
                                                       stream emission (§8)
```

**Convention for field optionality:**
- **required** — must be present, validation rejects messages without it
- **conditional** — required when a stated condition holds, otherwise omitted
- **optional** — may be present, downstream behavior is defined for both presence and absence

**Convention for closed enums:** All discriminator fields are closed enums. Open string fields are explicitly marked `freeform-bounded` (constrained-but-not-enumerated) or `freeform` (no constraint).

---

## 1. Common primitives and request context

These types appear across every other section. They are the shared vocabulary of the bundle.

### 1.1 Identifier types

| Type | Form | Notes |
|---|---|---|
| `identifier` | lowercase-snake-case string, max 128 chars | Logical names from the registry |
| `policy-id` | dotted form, e.g. `student_profile.read.default` | Internal policy identifier, never LLM-supplied |
| `digest` | `sha256:<64 hex chars>` | Used wherever a hash reference is recorded |
| `correlation-id` | string, max 128 chars, freeform-bounded | Cross-boundary request tracing |
| `tenant-id` | identifier | Scoping primitive |
| `principal-id` | identifier | Human or service principal |
| `agent-id` | identifier | Agent identity within session |
| `runtime-session-id` | identifier | Session lifetime scope |
| `credential-handle-id` | identifier | Opaque reference; never the credential itself |
| `audit-id` | opaque operational ID, regex `^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$` | **v0.3.1 delta:** distinct from `identifier`. Allows ULID, UUID-with-hyphens, KSUID, mixed case. Excludes whitespace, dots, slashes, curly braces, URL-like values. Used for per-record operational IDs. |
| `external-ref` | URI or opaque ref string | Reference into Evidence Store, downstream audit, etc. |
| `timestamp-ms` | unsigned integer (Unix epoch ms) | Single time representation across the bundle |

**v0.3.1 type discipline:** `audit-id` is an **operational** identifier (per-record, globally unique, generator-chosen format), distinct from `identifier` (registry-style logical name). All catalog references to audit-record IDs use `audit-id`, not `identifier`. Sections that referenced `identifier` for audit-record IDs in v0.3 are corrected in this revision to use `audit-id` (see §3.6, §3.7, §5.1, §5.2 below).

### 1.2 Environment classification

Closed enum (`environment-code`):

| Value | Meaning |
|---|---|
| `local` | Developer machine |
| `sandbox` | Isolated sandbox env |
| `development` | Shared development env |
| `qa` | QA env |
| `uat` | User acceptance env |
| `staging` | Pre-production |
| `production` | Production env |

The `production` value triggers the production-class branch of D-3 (destructive-class taxonomy).

### 1.3 Actor classification

Closed enum (`actor-kind-code`):

| Value | Meaning |
|---|---|
| `human` | Direct human action |
| `agent` | LLM-driven autonomous agent |
| `runtime` | Ojas Runtime itself (system action) |
| `system` | Non-Ojas system service |
| `operator` | Privileged operator with break-glass scope |

### 1.4 Action classification (D-3 three-axis)

Three closed enums, recorded together on every governed action.

**Axis 1 — `data-action-class-code`:**

| Value | Meaning |
|---|---|
| `read-only` | SELECT, GET, list, describe |
| `mutate` | UPDATE, INSERT, file write, configuration change |
| `bulk-mutate` | Mutation crossing bulk threshold |
| `export` | Data leaves the governed boundary |
| `destructive` | DELETE, DROP, TRUNCATE, volume/bucket/file deletion |
| `irreversible` | External message, external publish, payment, ownership transfer |

**Axis 2 — `data-resource-class-code`:**

| Value | Meaning |
|---|---|
| `table` | Relational table |
| `view` | Database view |
| `collection` | Document store collection |
| `document-path` | Document or path identifier |
| `index` | Search/vector index |
| `report-result` | Computed result resource |
| `export-object` | Object produced by export |

**Axis 3 — `data-risk-class-code`:**

| Value | Meaning |
|---|---|
| `low` | No production impact, no cross-tenant |
| `medium` | Production read or non-prod mutation |
| `high` | Production mutation or bulk threshold met |
| `critical` | Destructive, irreversible, or cross-tenant production |

Pre-execution audit is required when D-3's rules hold (see parent §9.1 D-3). The combination is recorded; the trigger condition is computed.

### 1.5 Request context (`request-context`)

Every governed message carries this block.

| Field | Required? | Type | Notes |
|---|---|---|---|
| `correlation-id` | required | correlation-id | |
| `tenant-id` | required | tenant-id | Forgeable; integrity rests on session binding (Section 3.1) |
| `environment` | required | environment-code | |
| `actor` | required | actor-context (§1.6) | |
| `policy-state-digest` | optional at message level, **conditionally required by runtime** | digest | Active policy/freeze state at message time. See tiered rule below. |
| `instruction-context-digest` | optional at message level, **conditionally required by runtime** | digest | Active instruction context (for I-1 enforcement evidence). See tiered rule below. |

**v0.3.1 delta — tiered digest requirement (D-F4):**

These two digests are structurally optional at request entry, because risk class and action class are not yet known at message ingress. Runtime validation enforces the tiered rule below **after** policy classification:

| Tier | Conditions | `policy-state-digest` | `instruction-context-digest` |
|---|---|---|---|
| Tier A | `risk-class` in (`critical`, `high`) | required | required |
| Tier B | `action-class` in (`destructive`, `irreversible`) | required | required |
| Tier C | `action-class = mutate` AND `resource-class = production` | required | required |
| Tier D | `actor-kind = agent` AND `operation` in (`insert`, `update`, `delete`, `export`) | required | required |
| Tier E | All other paths (e.g., human/operator low-risk reads, sandbox/dev mutations) | optional | optional |

Where "required by runtime" applies and the digest is absent, the executor responds with `deny-structural` per §2.10. Runtime enforcement is necessary because the requirement is determined by post-classification fields (`risk-class`, `action-class`, `resource-class`) not present in the message at entry.

Schemas SHOULD encode what is statically checkable (e.g., the actor-kind+operation portion of Tier D); the rest is enforced at the runtime boundary after `data-policy-decision` is computed.

### 1.6 Actor context (`actor-context`)

| Field | Required? | Type | Notes |
|---|---|---|---|
| `actor-kind` | required | actor-kind-code | |
| `principal-id` | conditional | principal-id | Required when actor-kind = human / operator |
| `agent-id` | conditional | agent-id | Required when actor-kind = agent |
| `runtime-session-id` | conditional | runtime-session-id | Required for agent and human sessions |

### 1.7 Sensitivity and masking

**Closed enum (`sensitivity-code`):**

| Value | Meaning |
|---|---|
| `public` | No restriction |
| `normal` | Default business data |
| `personal` | PII |
| `sensitive` | Financial, health |
| `restricted` | Regulatory-restricted |
| `secret` | Never returned to LLM under any policy |

**Closed enum (`masking-code`):**

`none`, `redact`, `hash`, `tokenize`, `email-partial`, `phone-partial`, `last4`, `date-year-only`, `custom`

### 1.8 Decision codes

**Closed enum (`data-decision-code`):**

| Value | Meaning |
|---|---|
| `allowed` | Operation permitted as proposed |
| `denied` | Operation refused at policy |
| `needs-approval` | Pending external approval |
| `masked` | Allowed with field masking applied |
| `rewritten` | Allowed after Ojas Data rewrote the operation |

**Closed enum (`effective-decision-code`)** — what actually happened:

| Value | Meaning |
|---|---|
| `executed` | Action completed |
| `deny-by-policy` | Refused by policy authority |
| `deny-by-timeout` | Refused due to D-2 timeout |
| `deny-by-precondition` | Refused due to preflight failure |
| `deny-by-no-progress` | Refused due to no-progress halt |
| `deny-structural` | Refused because of structural type/constraint violation |

---

## 2. Ojas Data core messages

The data-access surface. LLM-facing input is constrained; executable construction is internal.

### 2.1 `extracted-intent` (LLM input)

The single LLM-facing input. Fields are bounded; no executable artifacts.

| Field | Required? | Type | Notes |
|---|---|---|---|
| `intent` | required | intent-code (closed enum) | What the LLM is trying to do |
| `operation` | required | data-operation-code (closed enum) | Read/insert/update/delete/export/aggregate |
| `entity-terms` | optional | list of bounded strings | Snake-case-bounded; matched against registry |
| `field-terms` | optional | list of bounded strings | Snake-case-bounded; matched against registry |
| `filters` | optional | list of `filter-candidate` | Structured, not free text |
| `user-language` | optional | bounded string | Original language for trace |
| `confidence` | optional | float in [0.0, 1.0] | LLM's confidence; advisory only |

**Constraints:**
- No SQL field. No raw query. No physical names. No policy-id. No credential-class. No operation-policy-id (LLM cannot select).
- `entity-terms` and `field-terms` resolved against compiled registry; unknown terms produce `entity-not-in-registry` / `field-not-in-registry` sanitized feedback.

### 2.2 `filter-candidate`

| Field | Required? | Type | Notes |
|---|---|---|---|
| `field-term` | required | bounded string | Logical name, matched against registry |
| `operator` | required | operator-code (closed enum) | eq / neq / gt / gte / lt / lte / in / not-in / contains / starts-with / ends-with / between / is-null / is-not-null |
| `value-ref` | required | parameter reference | Never literal SQL value; bound to parameters table (§2.5) |

### 2.3 `resolved-intent`

Output of registry resolution. Bridge between LLM input and policy decision.

| Field | Required? | Type | Notes |
|---|---|---|---|
| `intent` | required | intent-code | Carried from extracted-intent |
| `operation` | required | data-operation-code | Carried from extracted-intent |
| `entity` | required | identifier | Resolved logical entity |
| `operation-policy-id` | required | policy-id | **Computed by Ojas Data**, never LLM-supplied |
| `fields` | required | list of `resolved-field` | Logical → physical, with sensitivity |
| `scope` | required | map of identifier → `resolved-scope-dimension` | Structurally injected |
| `filters` | conditional | list of `resolved-filter` | Required when extracted-intent.filters present |
| `registry-id` | required | identifier | Which registry was used |
| `compiled-registry-digest` | required | digest | Provenance for the resolution |

### 2.4 `data-policy-decision`

Output of internal policy evaluation. Bound to the operation, the resolved fields, the actor, and the environment.

| Field | Required? | Type | Notes |
|---|---|---|---|
| `decision` | required | data-decision-code | |
| `effective-decision` | conditional | effective-decision-code | Required when decision = denied/masked/rewritten |
| `operation-policy-id` | required | policy-id | |
| `entity` | required | identifier | |
| `operation` | required | data-operation-code | |
| `action-class` | required | data-action-class-code | D-3 Axis 1 |
| `resource-class` | required | data-resource-class-code | D-3 Axis 2 |
| `risk-class` | required | data-risk-class-code | D-3 Axis 3 |
| `allowed-fields` | required | list of identifier | After policy filtering |
| `credential-class` | required | data-credential-class-code | Selected by Ojas Data, not LLM |
| `policy-version` | required | bounded string | |
| `masked-fields` | conditional | list of `masked-field` | Required when masking applied |
| `blocked-fields` | conditional | list of `blocked-field` | Required when blocking applied |
| `scope-predicates` | required | list of `scope-predicate` | Structurally injected, never LLM-supplied |
| `approval-required` | conditional | boolean | Required when decision = needs-approval |
| `approval-ref` | conditional | external-ref | Required when approval-required = true |
| `pre-execution-audit-required` | required | boolean | Per D-3 rules |
| `mutation-preflight-required` | required | boolean | True when operation is mutate/destructive |

**Critical:** `pre-execution-audit-required` is computed from action-class + resource-class + risk-class per D-3. It is not a free-toggle policy author choice; it follows the taxonomy.

### 2.5 `safe-query-plan`

The executable plan. Constructed by Ojas Data, never by the LLM. Three v0.3 deltas applied here.

| Field | Required? | Type | Notes |
|---|---|---|---|
| `dialect` | required | dialect-code | Target storage system |
| `operation` | required | query-operation-code | select / insert / update / delete / aggregate |
| `entity` | required | identifier | Bound to resolved entity |
| `operation-policy-id` | required | policy-id | Carries policy provenance |
| `compiled-registry-digest` | required | digest | **v0.3 delta:** binds plan to registry version, replaces explicit table-ref |
| `parameters` | required | map of bounded string → `query-parameter-ref` | All values referenced, never literal |
| `select` | conditional | list of bounded strings | Required when operation = select/aggregate |
| `where` | optional | list of `query-where-clause` | Parameterized |
| `set` | conditional | map of bounded string → `query-parameter-ref` | **v0.3 delta:** parameterized, never literal. Required when operation = update/insert |
| `limit` | optional | unsigned integer | Bounded by policy |
| `query-digest` | required | digest | Plan digest for audit binding |

**v0.3 deltas in §2.5:**
1. `set` uses `query-parameter-ref` like `where` does — no literal values in UPDATE/INSERT SET clauses.
2. `compiled-registry-digest` replaces standalone `table-ref` — physical table is derived from entity + registry at execution time, not stored independently. Prevents entity/table divergence.
3. `query-digest` is required, not optional — needed for audit binding (Section 3.3).

### 2.6 `query-where-clause`

| Field | Required? | Type | Notes |
|---|---|---|---|
| `column` | required | bounded string | Physical column from registry resolution |
| `operator` | required | sql-operator-code (closed enum) | |
| `param` | required | bounded string | Reference into parameters map |

### 2.7 `query-parameter-ref` (v0.3 delta)

**Closed enum (`parameter-source-code`)** — the load-bearing structural defense:

| Value | Meaning |
|---|---|
| `scope-injection` | Value from session/tenant scope binding |
| `resolved-filter` | Value from a filter-candidate in extracted-intent |
| `session-context` | Value from session context (correlation, user, etc.) |
| `policy-derived` | Value computed by policy (e.g., date ranges) |

**Critical:** there is no `llm-literal` member. The LLM cannot supply values that flow directly into queries. All values trace to one of the four bounded sources above.

| Field | Required? | Type | Notes |
|---|---|---|---|
| `source` | required | parameter-source-code (closed enum) | **v0.3 delta:** closed enum, not freeform string |
| `type` | required | bounded string | Inferred from registry field type |

### 2.8 `mutation-preflight-result` (v0.3 delta)

Required for CUD operations per `mutation-preflight-required`. Closed check enum eliminates the v0.2 free-text gap.

**v0.3.1 framing (D-F2):** `mutation-preflight-result` is a **reusable structured type**, not a standalone top-level protocol message. It appears in two reference modes:

- **Structural:** carried inline as `data-execute-response.preflight` (§2.11)
- **By digest:** referenced as `mutation-preflight-orchestration-record.preflight-result-digest` (§3.8) — the audit record stores the digest of the same logical structure

Same logical artifact, two reference modes. Validators MUST NOT expect `mutation-preflight-result` as a top-level message instance; it always appears inside one of those two contexts.

**Closed enum (`preflight-check-code`)** — **v0.3 delta:**

| Value | Meaning | Safety class |
|---|---|---|
| `scope-verification` | WHERE clause contains required scope predicates | **safety-critical** |
| `tenant-isolation` | Operation cannot cross tenant boundary | **safety-critical** |
| `row-estimate` | Estimated affected-row count from query plan | advisory |
| `explain-plan` | Database EXPLAIN output sanity | advisory |
| `soft-delete-feasibility` | Whether soft-delete is available for the entity | advisory |
| `bulk-limit-check` | Whether operation exceeds bulk threshold | safety-critical |

**Profile rule (per v0.3):** For any mutation preflight, `scope-verification` and `tenant-isolation` checks **must be present**. Their absence makes the preflight invalid regardless of other checks passing.

| Field | Required? | Type | Notes |
|---|---|---|---|
| `operation-policy-id` | required | policy-id | |
| `entity` | required | identifier | |
| `operation` | required | data-operation-code | |
| `decision` | required | preflight-decision-code (closed enum: passed / failed / requires-approval) | |
| `checks` | required | list of `preflight-check` | Must include scope-verification + tenant-isolation |
| `sanitized-feedback` | conditional | `sanitized-feedback` (§2.9) | Required when decision = failed |
| `operator-diagnostics-ref` | optional | external-ref | Full diagnostics into Evidence Store, not LLM |

### 2.9 `sanitized-feedback` (v0.3 delta)

The LLM-facing failure surface. Template-based, not free-text. Closed retry categories.

**Closed enum (`retry-category-code`):**

| Value | Meaning | Retry-eligible? |
|---|---|---|
| `extraction-malformed-dto` | LLM output didn't match DTO | yes |
| `extraction-invalid-enum` | LLM supplied invalid enum value | yes |
| `extraction-missing-field` | Required field missing in LLM output | yes |
| `extraction-ambiguous-wording` | Multiple registry matches | yes |
| `resolver-unknown-entity` | Entity-term not in registry | yes |
| `resolver-unknown-field` | Field-term not in registry | yes |
| `resolver-ambiguous` | Multiple entity/field matches | yes |
| `governance-policy-denied` | Policy refused operation | no |
| `governance-sensitive-blocked` | Sensitive field requested | no |
| `scope-dimension-missing` | Required scope dimension absent | conditional |
| `credential-class-mismatch` | Operation needs class agent lacks | no |
| `mutation-rejected` | Preflight failed (terminal) | no |
| `precheck-failed` | Generic precheck failure (terminal) | no |
| `delete-blocked` | Delete refused (terminal) | no |
| `bulk-limit-exceeded` | Operation exceeds bulk threshold | no |
| `no-progress-detected` | No-progress halt fired | no |
| `raw-diagnostic-blocked` | Underlying diagnostic would leak (terminal) | no |

| Field | Required? | Type | Notes |
|---|---|---|---|
| `category` | required | retry-category-code (closed enum) | |
| `retry-eligible` | required | boolean | Derived from category |
| `summary-template-id` | required | identifier | **v0.3 delta:** template reference, not free text |
| `template-bindings` | conditional | map of bounded string → bounded string | Required when template has variables. Variables sanitized at template render time. |
| `allowed-values` | optional | map of bounded string → list of identifier | For extraction-invalid-enum, returns valid enum members |
| `halt-execution` | optional | boolean | Terminal flag |

**v0.3 delta:** the v0.2 `abstract-summary: tstr` is **removed**. Free-text in this field was the leak surface. Templates are pre-registered, vetted, and parameter-bound; the LLM only ever sees rendered template output, never raw runtime strings.

### 2.10 `data-execute-request`

The top-level request that enters the bundle.

| Field | Required? | Type | Notes |
|---|---|---|---|
| `context` | required | request-context (§1.5) | |
| `input` | conditional | discriminated input type (§2.13) | **v0.3.1 delta:** typed reference to one of the six discriminated input types in §2.13. Not an open object. |
| `extracted-intent` | conditional | extracted-intent (§2.1) | Required for LLM-driven requests |
| `pre-execution-audit-ref` | conditional | external-ref | **v0.3 delta:** required when prior policy decision set pre-execution-audit-required = true |
| `dry-run` | optional | boolean | Skip execution, return plan only |

**v0.3 delta on `input` (preserved):** the v0.2 `input: { * tstr => any }` open surface is replaced with **discriminated per-operation input types**. For human/operator requests, the input shape is documented per operation. For LLM-driven requests, `extracted-intent` is the only path. The two paths cannot be combined in a single request.

**v0.3.1 delta on `input` (correction):** v0.3 declared the discriminated-input invariant but did not define the types. v0.3.1 introduces §2.13, which stubs the six discriminated input types (`read-input`, `insert-input`, `update-input`, `delete-input`, `export-input`, `aggregate-input`). Each carries a closed `input-kind` discriminator and the `operation` field. Full field shapes are explicitly deferred to v0.3.2 — this revision is a correction pass, not a feature pass. Until v0.3.2, request validators accept the stub shapes; downstream consumers should treat additional fields as forward-compatible payload.

**v0.3 delta on `pre-execution-audit-ref`:** the executor (Section 3.3) refuses any request whose resolved policy required pre-execution audit but does not carry this ref. This is the type-level binding of the D-1/PB-002 fail-closed semantics.

### 2.11 `data-execute-response`

| Field | Required? | Type | Notes |
|---|---|---|---|
| `correlation-id` | required | correlation-id | |
| `decision` | required | data-policy-decision | |
| `audit` | required | evidence-record wrapping `data-operation-audit` (§5.1, §5.2) | **v0.3.1 clarification:** transmitted as `evidence-record` envelope with `record-type = data-operation-audit`, not as bare payload. Always present. |
| `effective-decision` | required | effective-decision-code | What happened |
| `resolved-intent` | conditional | resolved-intent (§2.3) | Present when resolution occurred |
| `preflight` | conditional | mutation-preflight-result (§2.8) | **v0.3.1 clarification:** typed reference to the §2.8 structure; this is the only place the structured form appears (orchestration record §3.8 references it by digest). Present for CUD operations. |
| `query-plan` | conditional | safe-query-plan | Present when plan was built |
| `credential-selection` | conditional | credential-selection (§4.2) | Present when execution occurred |
| `data` | conditional | structured result shape | Present when read/aggregate succeeded |
| `sanitized-feedback` | conditional | sanitized-feedback | Present when decision != allowed |

### 2.12 `sql-review-request` and `sql-review-response`

The only path that carries raw SQL. Separate top-level message type. Requires explicit reviewer identity and elevated policy.

**`sql-review-request`:**

| Field | Required? | Type | Notes |
|---|---|---|---|
| `context` | required | request-context | |
| `sql` | required | bounded string | The raw SQL under review |
| `mode` | required | sql-review-mode-code (closed enum: review-only / rewrite-if-safe / execute-if-approved) | |
| `reviewer-principal-id` | required | principal-id | Human reviewer identity |
| `elevated-policy-ref` | required | external-ref | Reference to the elevated policy authorizing this review |

**`sql-review-response`:**

| Field | Required? | Type | Notes |
|---|---|---|---|
| `correlation-id` | required | correlation-id | |
| `decision` | required | data-decision-code | |
| `safe-query-plan` | conditional | safe-query-plan | Present when SQL was rewritten to safe plan |
| `rewritten-sql-digest` | conditional | digest | Present when mode = rewrite-if-safe and rewrite succeeded |
| `sanitized-feedback` | conditional | sanitized-feedback | Present when decision != allowed |
| `audit` | required | evidence-record wrapping `data-operation-audit` (§5.1, §5.2) | **v0.3.1 clarification:** envelope-wrapped per §5.1; not bare payload. Always present. |

### 2.13 Discriminated input types (stubs)

> **v0.3.2 freeze-safety warning:**
>
> The v0.3.2 input stubs are **not freeze-ready for production use**. Full per-operation input shapes must be defined before schema freeze.
>
> Until full shapes are defined, the open-input problem (v0.2 `input: { * tstr => any }`) can re-enter through the "forward-compatible payload" allowance below. Schema freeze MUST close `additionalProperties` on each per-type stub before the catalog is treated as freeze-ready.

**v0.3.1 delta — discriminated input types (D-C1):**

v0.3 §2.10 declared that `data-execute-request.input` is a "discriminated per-operation input type" but did not enumerate those types. v0.3.1 introduced the six stubs below. Full field models are **deferred to a future revision** — neither v0.3.1 nor v0.3.2 is a feature pass for this section. Both are correction passes; the full shapes are real design work that warrants a dedicated revision.

**Common envelope (every input type has):**

| Field | Required? | Type | Notes |
|---|---|---|---|
| `input-kind` | required | input-kind-code (closed enum, §1.x candidate) | Discriminator. One of: read-input / insert-input / update-input / delete-input / export-input / aggregate-input |
| `operation` | required | data-operation-code | Must match the input-kind (insert-input → insert, etc.); validators reject mismatches |

**Closed enum (`input-kind-code`):**

| Value | Used for |
|---|---|
| `read-input` | operation = read |
| `insert-input` | operation = insert |
| `update-input` | operation = update |
| `delete-input` | operation = delete |
| `export-input` | operation = export |
| `aggregate-input` | operation = aggregate |

**Per-type stubs (full field shapes deferred to v0.3.2):**

#### 2.13.1 `read-input` (stub)

| Field | Required? | Type | Notes |
|---|---|---|---|
| `input-kind` | required | `read-input` (constant) | Discriminator |
| `operation` | required | `read` (constant) | |

**Deferred to a future revision:** entity, fields, filter structure, pagination, projection limits, ordering. These will mirror the resolved-intent shape (§2.3) but for human/operator-authored requests rather than LLM-extracted intent.

#### 2.13.2 `insert-input` (stub)

| Field | Required? | Type | Notes |
|---|---|---|---|
| `input-kind` | required | `insert-input` (constant) | Discriminator |
| `operation` | required | `insert` (constant) | |

**Deferred to a future revision:** entity, field-value bindings per registry, batch shape, idempotency keys, association references.

#### 2.13.3 `update-input` (stub)

| Field | Required? | Type | Notes |
|---|---|---|---|
| `input-kind` | required | `update-input` (constant) | Discriminator |
| `operation` | required | `update` (constant) | |

**Deferred to a future revision:** entity, target record reference (PK or unique-key), field updates, optimistic concurrency token, expected-version pattern.

#### 2.13.4 `delete-input` (stub)

| Field | Required? | Type | Notes |
|---|---|---|---|
| `input-kind` | required | `delete-input` (constant) | Discriminator |
| `operation` | required | `delete` (constant) | |

**Deferred to a future revision:** entity, target record reference, soft-delete preference, cascade declaration (if soft-delete declines cascade).

#### 2.13.5 `export-input` (stub)

| Field | Required? | Type | Notes |
|---|---|---|---|
| `input-kind` | required | `export-input` (constant) | Discriminator |
| `operation` | required | `export` (constant) | |

**Deferred to a future revision:** entity, format declaration, destination class (file/object-store/stream), maximum row count, masking profile override (if elevated policy permits).

#### 2.13.6 `aggregate-input` (stub)

| Field | Required? | Type | Notes |
|---|---|---|---|
| `input-kind` | required | `aggregate-input` (constant) | Discriminator |
| `operation` | required | `aggregate` (constant) | |

**Deferred to a future revision:** entity, group-by axes, aggregate functions (closed enum), having-style filters, result-cap.

**Path-exclusion rule (preserved from §2.10):**

The LLM-driven path uses `extracted-intent` (§2.1). The human/operator/system path uses one of the typed inputs above. A single `data-execute-request` carries **either** `extracted-intent` **or** `input`, never both, and never an open `any`-map. Validators MUST reject requests carrying both or neither.

**Future revision (non-binding):** The stubs will be filled in. Catalog readers should treat additional fields appearing on these types as **forward-compatible** payload during this stub window only — v0.3.2 validators that allow extra fields are correct *as a transitional posture*; validators that close the input shapes via `additionalProperties: false` should defer that hardening to the revision that defines full per-operation shapes. Per the freeze-safety warning at the top of §2.13, schema freeze requires closing this surface first.

---

## 3. Runtime-data enforcement messages

The eight v1-coupled capabilities from parent §4.5. These are the Ojas-side enforcement modules that ride with the data bundle until standalone Runtime exists.

### 3.1 Context binding (`context-binding-record`)

Capability 1. Prevents forged tenant/actor/session claims by binding context to verifiable inputs at session start.

| Field | Required? | Type | Notes |
|---|---|---|---|
| `runtime-session-id` | required | runtime-session-id | |
| `bound-at-ms` | required | timestamp-ms | |
| `tenant-binding-source` | required | binding-source-code (closed enum) | Where tenant-id came from |
| `actor-binding-source` | required | binding-source-code | Where principal/agent identity came from |
| `binding-evidence-digest` | required | digest | Hash of the binding inputs (token claims, signed session start) |
| `expires-at-ms` | required | timestamp-ms | Binding lifetime |

**Closed enum (`binding-source-code`):**

| Value | Meaning |
|---|---|
| `verified-token` | OAuth/OIDC-style token validated upstream |
| `signed-session-start` | Out-of-band signed session establishment |
| `runtime-issued` | Ojas Runtime issued the session itself |
| `operator-attested` | Human operator attested the binding |

`agent-self-claim` is **not** a member. Agents cannot establish their own binding.

### 3.2 Credential-handle enforcement (`credential-handle-use-record`)

Capability 2. Records every credential handle use. The credential value is never present.

| Field | Required? | Type | Notes |
|---|---|---|---|
| `credential-handle-id` | required | credential-handle-id | Opaque reference |
| `credential-handle-digest` | required | digest | Hash of the handle identity, not the credential |
| `credential-class` | required | data-credential-class-code | |
| `scope-snapshot-digest` | required | digest | Hash of the resolved scope at use time |
| `requested-by-operation-policy-id` | required | policy-id | Which operation policy required this credential |
| `used-at-ms` | required | timestamp-ms | |
| `runtime-session-id` | required | runtime-session-id | |

### 3.3 Pre-execution audit binding (`pre-execution-audit-binding`)

Capability 3. Type-level binding of D-1 fail-closed semantics. The executor refuses any operation requiring pre-execution audit without this binding.

| Field | Required? | Type | Notes |
|---|---|---|---|
| `audit-ref` | required | external-ref | Pointer to the emitted pre-execution audit record in Evidence Store |
| `audit-digest` | required | digest | Hash of the audit record, must match Evidence Store |
| `bound-policy-decision-digest` | required | digest | Hash of the data-policy-decision this binding satisfies |
| `bound-query-digest` | required | digest | Hash of the safe-query-plan being executed |
| `emitted-at-ms` | required | timestamp-ms | When the audit was emitted |
| `policy-response-received` | required | boolean | Whether external policy authority responded within D-1 budget |
| `policy-response-decision` | conditional | effective-decision-code | Required when policy-response-received = true |
| `policy-response-latency-ms` | conditional | unsigned integer | Required when policy-response-received = true |

**Enforcement:** the executor verifies `bound-policy-decision-digest` and `bound-query-digest` match the current request. Mismatched bindings are refused as `deny-structural`. This prevents a stale audit-ref from being attached to a different operation.

**Behavior when policy-response-received = false:** the binding records the timeout. The executor treats this as `deny-by-timeout` per D-2 and does not proceed.

### 3.4 Sanitized feedback routing (`sanitized-feedback-routing-record`)

Capability 4. Records that feedback to the LLM was sanitized through the template path, not raw diagnostics.

| Field | Required? | Type | Notes |
|---|---|---|---|
| `sanitized-feedback-template-id` | required | identifier | Which template rendered |
| `raw-diagnostic-ref` | conditional | external-ref | Pointer to raw operator diagnostics in Evidence Store, NOT routed to LLM |
| `raw-diagnostic-digest` | conditional | digest | Hash binding the raw diagnostic to this feedback event |
| `bound-correlation-id` | required | correlation-id | |
| `routed-at-ms` | required | timestamp-ms | |

**Profile rule:** for every sanitized-feedback emission with a known underlying raw diagnostic, the routing record carries the digest binding. Reconciliation can verify the LLM saw the template, not the diagnostic.

### 3.5 No-progress detection (`no-progress-halt-record`)

Capability 5. Records when the runtime halted a retry/guess loop.

**Closed enum (`no-progress-reason-code`):**

| Value | Meaning |
|---|---|
| `identical-request-retry-burst` | Same operation re-issued N times in window |
| `near-identical-request-retry-burst` | Similar requests in window (variation-by-mutation) |
| `cud-failure-repair-attempt` | CUD failure followed by variation attempt |
| `retry-after-terminal-feedback` | Retry after non-retry-eligible feedback |
| `bulk-threshold-breach-burst` | Multiple bulk-threshold breaches in window |

| Field | Required? | Type | Notes |
|---|---|---|---|
| `runtime-session-id` | required | runtime-session-id | |
| `agent-id` | required | agent-id | |
| `reason` | required | no-progress-reason-code | |
| `window-seconds` | required | unsigned integer | Detection window |
| `event-count-in-window` | required | unsigned integer | How many events triggered the halt |
| `halt-at-ms` | required | timestamp-ms | |
| `terminal` | required | boolean | Whether the agent session is terminated or only this request blocked. **v0.3.2 resolution (O-2):** the boolean form is the canonical shape for v0.3.x. The alternative — separate record types for per-request vs session-terminal halts — is not adopted in v0.3.2 and is not re-opened as an ongoing concern. If that distinction becomes necessary later, it is a v0.4+ design change, not a v0.3.x revision. |

### 3.6 Field-level audit emission (`field-level-audit-record`)

Capability 6. Field-level detail required for read/export operations. This is a **discriminated** audit type per v0.3 delta.

**Envelope wrapping (v0.3.1 clarification):** `field-level-audit-record` is a **payload**, not a standalone protocol message. It travels inside `evidence-record` (§5.1) as `payload` when `record-type = field-level-audit`. Conformance validators MUST validate the envelope shape, not the bare payload. The runtime-data schema MUST NOT expose `field-level-audit-record` as a top-level message.

| Field | Required? | Type | Notes |
|---|---|---|---|
| `audit-id` | required | audit-id | **v0.3.1 delta:** typed as `audit-id` (opaque operational ID, §1.1), not `identifier`. Unique within Evidence Store. |
| `stage` | required | audit-stage-code (closed enum) | pre-execution / post-execution / denial / sanitized-failure / preflight-failure / reconciliation-gap |
| `emitter` | required | constant value `ojas-runtime-data` | **v0.3.1 correction:** v0.3 §3.6 incorrectly listed this as `ojas-data`. §5.3 and §9.3 already attributed `field-level-audit` to runtime-data; v0.3.1 aligns §3.6 with the correct owner. **v0.3 delta (preserved):** typed constant, not enum value. Cannot be spoofed across types. |
| `correlation-id` | required | correlation-id | |
| `entity` | required | identifier | |
| `operation` | required | data-operation-code | |
| `fields-returned` | conditional | list of identifier | **Required when stage = post-execution and operation = read/aggregate/export** |
| `fields-masked` | conditional | list of identifier | Required when masking applied |
| `fields-blocked` | conditional | list of identifier | Required when blocking applied |
| `result-digest` | conditional | digest | Required when stage = post-execution |
| `created-at-ms` | required | timestamp-ms | |

**v0.3 delta (preserved):** `fields-returned` is required (not optional) for post-execution read/export audits. Omission produces an invalid audit. This prevents the Replit-pattern defense from being silently weakened by missing field-level detail.

### 3.7 Reconciliation hooks (`reconciliation-hook-emit`)

Capability 7. Hooks that allow downstream reconciliation against truth sources (per D-4, deferred to integration specs).

| Field | Required? | Type | Notes |
|---|---|---|---|
| `audit-id` | required | audit-id | **v0.3.1 delta:** typed as `audit-id` (§1.1), not `identifier`. The Ojas-emitted audit this hook references. |
| `downstream-truth-source-code` | required | truth-source-code (closed enum) | What system holds the comparable truth |
| `downstream-ref-hint` | optional | external-ref | Hint for the reconciler (e.g., LSN, sequence number, log timestamp) |
| `reconciliation-priority` | required | reconciliation-priority-code (closed enum) | continuous / periodic / not-reconcilable |
| `emitted-at-ms` | required | timestamp-ms | |

**Closed enum (`truth-source-code`):**

`postgres-wal`, `mysql-binlog`, `mongo-oplog`, `cloud-provider-audit`, `none-available`

**Closed enum (`reconciliation-priority-code`):**

| Value | Meaning |
|---|---|
| `continuous` | Stream-based comparison (critical/destructive/production) |
| `periodic` | Batch reconciliation (normal operations) |
| `not-reconcilable` | No usable downstream truth — D-4 will need to address |

### 3.8 Mutation preflight orchestration (`mutation-preflight-orchestration-record`)

Capability 8. Records the runtime's orchestration of preflight ahead of mutating execution.

| Field | Required? | Type | Notes |
|---|---|---|---|
| `bound-policy-decision-digest` | required | digest | Which policy decision triggered preflight |
| `preflight-result-digest` | required | digest | Hash of the mutation-preflight-result |
| `checks-attempted` | required | list of preflight-check-code | What was run |
| `safety-critical-checks-present` | required | boolean | True only if scope-verification + tenant-isolation both ran |
| `orchestration-decision` | required | effective-decision-code | What runtime did next |
| `orchestrated-at-ms` | required | timestamp-ms | |

**Profile rule:** if `safety-critical-checks-present` is false for a mutation, `orchestration-decision` must be `deny-by-precondition`. The runtime refuses to proceed without the two safety-critical checks even if the rest of the preflight passed.

---

## 4. Credential-boundary adapter messages

Per parent §4.5 capability scope: Ojas owns the agent-facing boundary; external authority owns minting/revocation/lifecycle.

### 4.1 `credential-handle-request` (Ojas → external authority)

Outbound request from Ojas Data to the external credential authority. Ojas asks for a scoped handle.

| Field | Required? | Type | Notes |
|---|---|---|---|
| `correlation-id` | required | correlation-id | |
| `operation-policy-id` | required | policy-id | What operation will use the handle |
| `entity` | required | identifier | **v0.3.2 delta (O-1):** the data entity this handle is being requested for. Ojas Data always knows this at handle-request time; making it required gives the external authority tighter per-entity scoping leverage. |
| `operation` | required | data-operation-code | **v0.3.2 delta (O-1):** the operation the handle will enable. Pairs with `entity` so the authority can scope by (entity, operation), not only by class. |
| `requested-credential-class` | required | data-credential-class-code | What class is required |
| `requested-scope` | required | map of identifier → bounded string | The scope to bind the credential to |
| `runtime-session-id` | required | runtime-session-id | |
| `actor` | required | actor-context | |
| `requested-ttl-seconds` | optional | unsigned integer | TTL hint (authority may override) |

**v0.3.2 note (O-1):** `entity` and `operation` are required, not optional. Optional fields would weaken the tightening benefit — the authority cannot rely on per-entity scoping if half the requests omit the entity. Ojas Data always has both values at handle-request time, so requiring them imposes no Ojas-side cost.

### 4.2 `credential-selection` (authority → Ojas response, internal)

The response Ojas Data receives. Carries handle and scope, not the credential.

| Field | Required? | Type | Notes |
|---|---|---|---|
| `operation-policy-id` | required | policy-id | |
| `credential-class` | required | data-credential-class-code | |
| `credential-handle-id` | required | credential-handle-id | |
| `credential-handle-digest` | required | digest | Hash binding for audit |
| `scope` | required | map of identifier → bounded string | Resolved scope |
| `scope-snapshot-digest` | required | digest | Hash of the resolved scope |
| `ttl-seconds` | required | unsigned integer | Granted TTL |
| `approval-ref` | conditional | external-ref | Required when authority required approval |

**Profile rule:** Ojas Data never logs, stores, or transports the credential value itself. The handle and digests are sufficient for execution and audit.

### 4.3 `credential-revoke-notification` (external authority → Ojas)

Inbound notification when authority revokes a handle Ojas might still hold.

| Field | Required? | Type | Notes |
|---|---|---|---|
| `credential-handle-id` | required | credential-handle-id | |
| `revoked-at-ms` | required | timestamp-ms | |
| `reason-code` | required | revocation-reason-code (closed enum) | rotated / policy-revoked / scope-changed / lifecycle-expired |
| `signed-by-authority-digest` | required | digest | Authentication of the notification |

**Behavior:** on receipt, Ojas Data immediately stops using the handle. In-flight operations using the handle fail with `credential-class-mismatch` sanitized feedback.

---

## 5. Evidence-core messages

Append-only audit storage and stream emission. D-8 v1 architecture: PostgreSQL append-only with disjoint credentials, with digest fields for v2 forward compatibility.

### 5.1 Storage record envelope (`evidence-record`)

Every record in Evidence Store carries this envelope. **The envelope is the canonical wire shape for all audit records** — payloads (§5.2, §3.6, §3.1, §3.2, §3.3, §3.4, §3.5, §3.7, §3.8) travel inside `payload`, discriminated by `record-type` (§5.3). Bare payloads are not standalone protocol messages.

| Field | Required? | Type | Notes |
|---|---|---|---|
| `audit-id` | required | audit-id | **v0.3.1 delta:** typed as `audit-id` (§1.1, opaque operational ID), not `identifier`. Globally unique. |
| `record-type` | required | record-type-code (closed enum) | What kind of audit record (see §5.3) |
| `emitter` | required | emitter-code (closed enum) | ojas-data / ojas-runtime-data / ojas-credential-boundary-adapter / external-authority |
| `correlation-id` | required | correlation-id | |
| `tenant-id` | required | tenant-id | |
| `record-digest` | required | digest | **D-8 v1 digest field:** hash of the canonical serialization |
| `previous-record-digest` | optional | digest | **D-8 v1 digest field:** populated when chaining is enabled (v2-forward) |
| `payload-digest` | optional | digest | **D-8 v1 digest field:** hash of the payload portion |
| `created-at-ms` | required | timestamp-ms | |
| `payload` | required | record-type-specific structure | The actual audit content. Shape determined by `record-type` per §5.3 mapping. |

**v1 behavior:** `record-digest` is always populated. `previous-record-digest` is optional but, when populated, enables hash-chain verification. v1 ships with digests populated but chains not actively used. v2 activates the chain by validating `previous-record-digest` continuity.

**v0.3.1 envelope-wrapping rule (D-F3):** Audit records — including `data-operation-audit` (§5.2), `field-level-audit-record` (§3.6), `context-binding-record` (§3.1), `credential-handle-use-record` (§3.2), `pre-execution-audit-binding` (§3.3), `sanitized-feedback-routing-record` (§3.4), `no-progress-halt-record` (§3.5), `reconciliation-hook-emit` (§3.7), `mutation-preflight-orchestration-record` (§3.8) — are payloads inside `evidence-record`. Schemas and fixtures MUST validate the envelope. Schemas MUST NOT expose audit payloads as top-level protocol messages. Validators that accept a bare payload as a top-level instance are incorrect per this revision.

### 5.2 `data-operation-audit` (a record-type-specific payload)

The audit record for a complete data operation. Discriminated by stage.

**Envelope wrapping (v0.3.1 clarification):** Like all audit records per §5.1, `data-operation-audit` is a **payload**, not a standalone protocol message. It travels inside `evidence-record` as `payload` when `record-type = data-operation-audit`. Conformance validators MUST validate the envelope shape, not the bare payload.

| Field | Required? | Type | Notes |
|---|---|---|---|
| `stage` | required | audit-stage-code | |
| `actor` | required | actor-context | |
| `operation-policy-id` | required | policy-id | |
| `entity` | required | identifier | |
| `operation` | required | data-operation-code | |
| `action-class` | required | data-action-class-code | |
| `resource-class` | required | data-resource-class-code | |
| `risk-class` | required | data-risk-class-code | |
| `policy-version` | required | bounded string | |
| `query-digest` | conditional | digest | Required when operation involved a query plan |
| `effective-decision` | required | effective-decision-code | |
| `credential-class` | conditional | data-credential-class-code | Required when execution occurred |
| `credential-handle-digest` | conditional | digest | Required when execution occurred |
| `scope-snapshot-digest` | conditional | digest | Required when execution occurred |
| `result-digest` | conditional | digest | Required when stage = post-execution and operation = read/export |
| `field-level-audit-ref` | conditional | external-ref | Required when stage = post-execution; points to §3.6 record |
| `downstream-audit-ref` | optional | external-ref | If downstream system also emitted audit |
| `operator-diagnostics-ref` | optional | external-ref | Operator-only diagnostics, not LLM-visible |
| `policy-response-timeout-recorded` | conditional | boolean | Required when effective-decision = deny-by-timeout |

**Closed enum (`audit-stage-code`):**

`pre-execution`, `post-execution`, `denial`, `sanitized-failure`, `preflight-failure`, `reconciliation-gap`

### 5.3 Closed enum: `record-type-code`

Catalogs every record type written to Evidence Store. Allows discriminated parsing.

| Value | Owner module | Cross-ref |
|---|---|---|
| `data-operation-audit` | data-core | §5.2 |
| `field-level-audit` | runtime-data | §3.6 |
| `context-binding` | runtime-data | §3.1 |
| `credential-handle-use` | runtime-data | §3.2 |
| `pre-execution-audit-binding` | runtime-data | §3.3 |
| `sanitized-feedback-routing` | runtime-data | §3.4 |
| `no-progress-halt` | runtime-data | §3.5 |
| `reconciliation-hook` | runtime-data | §3.7 |
| `mutation-preflight-orchestration` | runtime-data | §3.8 |
| `credential-handle-request` | credential-boundary-adapter | §4.1 |
| `credential-selection` | credential-boundary-adapter | §4.2 |
| `credential-revoke-notification` | credential-boundary-adapter | §4.3 |
| `bulk-context-observed` | bulk/CAD signals | §6.1 |
| `create-after-destroy-observed` | bulk/CAD signals | §6.2 |
| `policy-response-timeout` | runtime-data | §3.3 + D-2 |

### 5.4 Storage constraints (informative; non-message)

Documented here for cross-reference; not part of the message schema.

- Append-only table. DELETE revoked at DB level.
- UPDATE prevented by trigger on rows older than a few seconds.
- Write credentials disjoint from any runtime or agent identity.
- Daily backup to immutable object storage (S3 Object Lock or equivalent).
- Retention reduction requires two-person out-of-band ceremony.
- `record-digest` is computed at write time using canonical serialization.

---

## 6. Bulk-context and create-after-destroy signals

D-5 and D-6 resolutions as typed messages.

### 6.1 `bulk-context-observed`

D-5: 60-second sliding window, threshold per (actor, entity), default 100.

| Field | Required? | Type | Notes |
|---|---|---|---|
| `actor` | required | actor-context | The actor whose operations crossed threshold |
| `entity` | required | identifier | The target entity |
| `tenant-id` | required | tenant-id | |
| `window-seconds` | required | unsigned integer | Per D-5: 60 |
| `threshold` | required | unsigned integer | Effective threshold (registry-declared or default) |
| `event-count-in-window` | required | unsigned integer | How many ops triggered |
| `operation-types-in-window` | required | list of data-operation-code | What operations |
| `first-event-at-ms` | required | timestamp-ms | Start of window |
| `observed-at-ms` | required | timestamp-ms | When threshold was crossed |

### 6.2 `create-after-destroy-observed`

D-6: recent-destroy index keyed by `(tenant, entity, actor, scope-dimension)`; 30-minute window.

| Field | Required? | Type | Notes |
|---|---|---|---|
| `actor` | required | actor-context | |
| `entity` | required | identifier | |
| `tenant-id` | required | tenant-id | |
| `scope-dimension` | required | map of identifier → bounded string | The scope tuple (matches recent-destroy index key) |
| `destroy-audit-ref` | required | external-ref | Points to the DELETE audit in Evidence Store |
| `destroy-at-ms` | required | timestamp-ms | When the DELETE happened |
| `create-audit-ref` | required | external-ref | Points to the INSERT audit |
| `create-at-ms` | required | timestamp-ms | When the INSERT happened |
| `window-seconds` | required | unsigned integer | Per D-6: 1800 (30 min) |
| `pattern-confidence-class` | required | pattern-confidence-class-code (closed enum) | exact-match / scope-match / actor-match |

**Closed enum (`pattern-confidence-class-code`):**

| Value | Meaning |
|---|---|
| `exact-match` | Full (tenant, entity, actor, scope) tuple matched |
| `scope-match` | (tenant, entity, scope) matched but actor differed |
| `actor-match` | (tenant, entity, actor) matched but scope differed |

**v0.3.2 resolution (O-3):** all three confidence levels are kept. `scope-match` is preserved as a **lower-confidence signal** — the same tenant/entity/scope target hit by a different actor is not the strict Replit-pattern, but it is investigation-worthy (collusion patterns, account compromise, multi-account adversary). Downstream consumers can filter by confidence-class as needed; the catalog does not collapse the enum.

**Profile rule:** detection emits the signal. Halt is downstream. Subscribers (Aegis or equivalent) consume from the stream and decide response.

---

## 7. Reconciliation hooks

Schema-level support for D-4 (deferred). The messages exist so reconciliation can be wired in per integration without re-opening the catalog.

### 7.1 `reconciliation-gap-observed`

Emitted when continuous or periodic reconciliation finds an Ojas-emitted audit with no downstream truth match, or vice versa.

| Field | Required? | Type | Notes |
|---|---|---|---|
| `gap-kind-code` | required | gap-kind-code (closed enum) | ojas-only / downstream-only / divergence |
| `ojas-audit-ref` | conditional | external-ref | Required when gap-kind = ojas-only or divergence |
| `downstream-truth-source` | required | truth-source-code | |
| `downstream-ref-hint` | conditional | external-ref | Required when gap-kind = downstream-only or divergence |
| `divergence-detail` | conditional | bounded structured object | Required when gap-kind = divergence; specific to truth source |
| `observed-at-ms` | required | timestamp-ms | |

### 7.2 `reconciliation-batch-summary`

Emitted at end of each reconciliation pass (periodic) or windowed slice (continuous).

| Field | Required? | Type | Notes |
|---|---|---|---|
| `truth-source` | required | truth-source-code | |
| `window-start-ms` | required | timestamp-ms | |
| `window-end-ms` | required | timestamp-ms | |
| `ojas-records-compared` | required | unsigned integer | |
| `downstream-records-compared` | required | unsigned integer | |
| `gaps-found` | required | unsigned integer | |
| `divergences-found` | required | unsigned integer | |
| `compared-records-digest` | optional | digest | **v0.3.2 delta (O-5):** digest of the canonical serialization of the record set the reconciler compared in this window. Enables forensic re-verification of comparison coverage at audit time. |
| `gap-records-digest` | optional | digest | **v0.3.2 delta (O-5):** digest of the canonical serialization of the subset where gaps or divergences were found. Separates comparison coverage from exception evidence so the two can be re-verified independently. |

**v0.3.2 note (O-5):** the two digests are separate, not merged. `compared-records-digest` answers "what did the reconciler look at?"; `gap-records-digest` answers "of those, which diverged?" Storing them separately enables forensic re-verification of either dimension without re-running the full comparison. Both fields are optional in v0.3.2 — deployments where reconciliation runs in-memory without retaining the compared set can omit them; deployments with persistent reconciliation pipelines should populate both.

---

## 8. Stream emission

D-9 resolution as message contracts. Two paths: synchronous gate (in-process/RPC/sidecar) and async observation (push log stream).

### 8.1 Synchronous gate path (`pre-execution-gate-event`)

Emitted by runtime-data when an action requiring pre-execution policy response is about to execute. Subject to D-1 latency budget (200ms target, 500ms ceiling).

| Field | Required? | Type | Notes |
|---|---|---|---|
| `correlation-id` | required | correlation-id | |
| `actor` | required | actor-context | |
| `entity` | required | identifier | |
| `operation` | required | data-operation-code | |
| `action-class` | required | data-action-class-code | |
| `resource-class` | required | data-resource-class-code | |
| `risk-class` | required | data-risk-class-code | |
| `policy-decision-digest` | required | digest | |
| `query-digest` | conditional | digest | Required for query-bearing operations |
| `proposed-at-ms` | required | timestamp-ms | |
| `latency-budget-ms` | required | unsigned integer | Per D-1: 500 |

**Response:** the external policy authority returns a `pre-execution-gate-response`.

### 8.2 `pre-execution-gate-response`

| Field | Required? | Type | Notes |
|---|---|---|---|
| `correlation-id` | required | correlation-id | |
| `effective-decision` | required | effective-decision-code | executed (proceed) / deny-by-policy / deny-by-timeout |
| `policy-reference` | conditional | external-ref | Required when effective-decision = executed or deny-by-policy |
| `response-at-ms` | required | timestamp-ms | |
| `decision-detail-ref` | optional | external-ref | Pointer to fuller policy reasoning |

### 8.3 Async observation path (stream-record envelope)

All audit and signal records from §5 and §6 are also fan-out to the observation stream. The stream envelope:

| Field | Required? | Type | Notes |
|---|---|---|---|
| `stream-sequence` | required | unsigned integer | Monotonic per partition |
| `partition-key` | required | bounded string | Computed per deployment-configured strategy; see resolution below |
| `record-type` | required | record-type-code | |
| `record-digest` | required | digest | Matches Evidence Store record-digest |
| `evidence-record-ref` | required | external-ref | Points back to Evidence Store |
| `payload` | required | record-type-specific structure | Same payload as Evidence Store record |
| `emitted-at-ms` | required | timestamp-ms | |

**Profile rule:** the stream is at-least-once delivery. Consumers must be idempotent on `record-digest`. Backpressure is absorbed at the topic level; emission rate is the runtime's natural rate.

**v0.3.2 resolution (O-4) — partition strategy:**

The partition key composition is a deployment-time configuration choice. The catalog defines permitted strategies; the runtime configuration selects one. The schema does not enforce the deployment-specific choice (the choice happens at config-load, not at message-validation).

| Strategy | Partition key | When to choose |
|---|---|---|
| `tenant-id` (default) | `<tenant-id>` | Most deployments. Achieves tenant-isolation in stream consumption; one tenant's backpressure does not affect another's. |
| `tenant+entity` | `<tenant-id>:<entity>` | Very large single-tenant deployments where a single tenant generates enough volume to need finer partitioning. Useful when one entity (e.g., `transaction_log`) dominates volume. |
| `tenant+entity+actor` | `<tenant-id>:<entity>:<actor-key>` | Even finer partitioning, for deployments where per-actor stream affinity matters (e.g., per-agent reconciliation pipelines). Highest partition count cost. |

**Configuration discipline:** the strategy is chosen once per deployment at runtime startup and recorded in deployment configuration. Mid-stream strategy changes require a topic rebuild and consumer-position reset; they are not hot-swappable.

**Schema posture:** the schema validates `partition-key` as a bounded string. It does not enforce strategy choice. Runtime config validates that the selected strategy is one of the three permitted; conformance tests verify the partition key matches the selected strategy.

---

## 9. Cross-cutting consistency rules

Constraints that span sections.

### 9.1 LLM-input boundary invariant

The LLM-supplied path is exclusively §2.1 (`extracted-intent`). No other message in the catalog is LLM-authored. Specifically:

- `safe-query-plan` (§2.5): constructed by data-core, never LLM
- `data-policy-decision` (§2.4): computed by data-core, never LLM
- `credential-selection` (§4.2): returned by credential authority, never LLM
- `*-audit-*`: emitted by runtime-data or data-core, never LLM
- All §6 signals: emitted by runtime-data, never LLM
- All §8 stream records: emitted by runtime-data, never LLM

This invariant is required for invariants I-1 (no advisory-only safety), I-6 (LLM authors intent not executables), and I-4 (emitter provenance is structural).

### 9.2 Digest binding chain

Several digests link records to enable verification:

```
data-policy-decision ──digest──→ pre-execution-audit-binding (§3.3)
safe-query-plan ──digest──→ pre-execution-audit-binding (§3.3)
                          ──digest──→ data-operation-audit (§5.2)
                          ──digest──→ pre-execution-gate-event (§8.1)
data-operation-audit ──ref──→ field-level-audit (§3.6)
                            ──ref──→ create-after-destroy-observed (§6.2)
                            ──ref──→ reconciliation-gap-observed (§7.1)
```

Verification: at any point, a reconciler can re-compute digests over canonical serializations and check the chain. v2 hash-chain mode adds `previous-record-digest` continuity to this.

### 9.3 Emitter provenance is typed

Per §3.6 v0.3 delta: `emitter` is a typed constant on each record type, not a free enum value. The Evidence Store rejects records claiming an emitter incompatible with the record type. Specifically:

- `data-operation-audit` records: `emitter = ojas-data` (constant)
- `field-level-audit` records: `emitter = ojas-runtime-data` (constant)
- `context-binding`, `credential-handle-use`, `pre-execution-audit-binding`, `sanitized-feedback-routing`, `no-progress-halt`, `mutation-preflight-orchestration`: `emitter = ojas-runtime-data` (constant)
- `credential-handle-request`, `credential-selection`, `credential-revoke-notification`: `emitter = ojas-credential-boundary-adapter` (constant)
- Bulk and CAD signals: `emitter = ojas-runtime-data` (constant)

Agent-supplied records cannot conform to any of these record types because the emitter would be wrong.

---

## 10. Delta lineage

This catalog is v0.3.1. The deltas accumulated by version are preserved below for lineage. §10.1 is the original v0.3 delta set, unchanged. §10.2 is the v0.3.1 review-correction deltas applied in this revision.

### 10.1 v0.3 deltas (preserved from prior session work)

The seven v0.3 deltas applied across the catalog:

| Delta | Section(s) | Effect |
|---|---|---|
| 1. Pre-execution audit binding centerpiece | §3.3, §2.10 | Required ref in execute-request; executor refuses without it for destructive |
| 2. Bulk-context block | §6.1 | Typed signal, 60s window, per (actor, entity), default 100 |
| 3. Create-after-destroy signal | §6.2 | Typed signal, (tenant, entity, actor, scope) tuple, 30-min window |
| 4. Closed preflight check enum | §2.8 | scope-verification + tenant-isolation mandatory for mutations |
| 5. Discriminated audit records by stage/emitter | §3.6, §5.2, §9.3 | Emitter is typed constant, field-level audit required for read/export post-execution |
| 6. Sanitized feedback templates | §2.9 | summary-template-id replaces abstract-summary free text |
| 7. Parameter-only query values | §2.5, §2.7 | set uses query-parameter-ref; source is closed enum (no llm-literal); compiled-registry-digest replaces table-ref |

### 10.2 v0.3.1 review-correction deltas (new in this revision)

Five corrections from the focused review report (`OJAS_DATA_RUNTIME_BUNDLE_FOCUSED_REVIEW.md`). v0.3.1 is a **correction pass**, not a feature pass. No new capabilities; no scope expansion. Each delta corresponds to one of the five governance-grade decisions in the review.

| Delta | Decision | Section(s) | Effect |
|---|---|---|---|
| 1. Audit-ID type separated from registry identifier | D-F1 | §1.1, §3.6, §3.7, §5.1, §5.2 | New `audit-id` type with regex `^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$`. Allows ULID/UUID/KSUID. All audit-record IDs use `audit-id`, not `identifier`. |
| 2. Mutation preflight as reusable type (not top-level message) | D-F2 | §2.8 (preserved), §2.11, §3.8 | `mutation-preflight-result` is a reusable structured type referenced from §2.11 (full structure) and §3.8 (digest). Not added to top-level message oneOf. |
| 3. Audit records canonically envelope-wrapped | D-F3 | §5.1, §5.2, §3.6, §2.11, §2.12 | `evidence-record` is the canonical wire shape for all audit records. Bare audit payloads are NOT standalone protocol messages. Schemas must validate the envelope. |
| 4. Tiered digest requirement (request-time optional, runtime-conditional) | D-F4 | §1.5 | `policy-state-digest` and `instruction-context-digest` are structurally optional at message entry; runtime validation makes them required for high/critical risk, destructive/irreversible actions, production mutations, and agent-driven mutate/export. Five-tier rule documented in §1.5. |
| 5. Discriminated input types stubbed (v0.3.2 full shapes deferred) | D-C1 | §2.10, §2.13 (new) | Six discriminated input types stubbed: `read-input`, `insert-input`, `update-input`, `delete-input`, `export-input`, `aggregate-input`. Common envelope (`input-kind` + `operation`) defined; per-type field bodies deferred to v0.3.2. |

Mandatory one-token correction also applied in this revision:

| Correction | Section | Fix |
|---|---|---|
| Field-level audit emitter | §3.6 | `ojas-data` → `ojas-runtime-data`. §3.6 v0.3 stated `ojas-data`; §5.3 and §9.3 already said `ojas-runtime-data`; v0.3.1 aligns §3.6 with the correct owner. |

### 10.3 What v0.3.1 explicitly did NOT do

For lineage clarity, v0.3.1 was a correction pass; the following were explicitly **not** in v0.3.1's scope:

- Full field shapes for the six §2.13 input types (deferred to a future revision)
- Schema artifacts (deferred to schema correction pass, separate work)
- Parent control model updates (separate turn per work order)
- Fixture revalidation (deferred to fixture correction pass, separate work)
- New record types, new messages, new capabilities (none in v0.3.1)
- v2/content-addressing/CDDL decisions (deferred to v2)

### 10.4 v0.3.2 open-item resolutions (new in this revision)

Five resolutions to the open items O-1 through O-5 from v0.3.1 §12, plus two small wording patches.

| Resolution | Open item | Section(s) | Effect |
|---|---|---|---|
| 1. `entity` and `operation` added to credential-handle-request as required | O-1 | §4.1 | The external credential authority can scope by (entity, operation) tuple, not only by class. Ojas Data always has both at request time, so required-ness imposes no Ojas-side cost. |
| 2. `terminal` boolean retained on no-progress-halt-record | O-2 | §3.5 | Boolean form is canonical for v0.3.x. Separate per-request vs session-terminal record types are NOT introduced and are not held open. Becomes a v0.4+ design change if revisited. |
| 3. `scope-match` confidence class retained | O-3 | §6.2 | All three confidence levels (`exact-match`, `scope-match`, `actor-match`) kept. `scope-match` is preserved as a lower-confidence signal for collusion / account-compromise investigation. Downstream consumers filter as needed. |
| 4. Stream partition strategies catalog-defined; deployment selects | O-4 | §8.3 | Three permitted strategies (`tenant-id` default, `tenant+entity`, `tenant+entity+actor`). Runtime configuration selects one at deployment time. Schema validates `partition-key` as bounded string; deployment configuration validates the selection. |
| 5. `compared-records-digest` and `gap-records-digest` added to reconciliation-batch-summary as optional | O-5 | §7.2 | Two separate digests, not merged. Enables forensic re-verification of comparison coverage and exception evidence independently. Optional because some deployments do not retain the compared set. |

Two small wording patches also applied in this revision:

| Patch | Section | Fix |
|---|---|---|
| Closing section baseline wording | Closing | "v0.3 baseline" → "v0.3.2 review-correction baseline" |
| §2.13 freeze-safety warning | §2.13 | Explicit "not freeze-ready for production use" warning placed at the top of §2.13 to prevent the open-input surface from quietly re-entering through forward-compatible payload allowance. |

### 10.5 What v0.3.2 explicitly does NOT do

To prevent scope creep — v0.3.2 is an open-item resolution pass, and the following are explicitly **not** in scope:

- Full field shapes for the six §2.13 input types (deferred to a future revision; freeze-safety warning placed in §2.13)
- Schema artifacts (deferred to schema correction pass, separate work)
- Parent control model updates (separate turn per work order)
- Fixture revalidation (deferred to fixture correction pass, separate work)
- New record types, new messages, new capabilities (none in v0.3.2 beyond the O-1/O-5 field additions)
- New enums (none added; existing enums in §6.2, §8.3 are unchanged in membership)
- Folding §10 lineage into version-history appendix (accepted as a future cleanup item, not part of v0.3.2)
- v2/content-addressing/CDDL decisions (deferred to v2)

---

## 11. What this catalog does not cover

To prevent scope creep into deferred areas:

- **D-4 reconciliation truth source per integration:** §7 messages exist but the *integration contract* between Ojas and each truth source is deferred.
- **D-7 tool provenance verification:** out of bundle scope — that's Ojas Runtime (standalone) when it ships.
- **D-10 per-product Ojas integration model:** out of scope — the catalog defines messages, not the integration mechanism (library vs sidecar vs mesh).
- **Standalone Ojas Runtime catalog:** the future artifact that absorbs Section 3 messages when the migration trigger fires (parent §4.5).
- **JSON Schema artifacts:** derived from this catalog, not present here. That's the next downstream artifact per parent §10.

---

## 12. Open items for review

All five items raised in v0.3.1 §12 are **resolved in v0.3.2** (see §10.4 for resolutions). They are retained here as a closed history; the table shows where the resolution lives.

| Item | Status | Resolution location | Summary |
|---|---|---|---|
| **O-1.** Should `credential-handle-request` (§4.1) carry the requesting `entity` field for tighter per-entity scoping by the external authority? | **Resolved (v0.3.2)** | §4.1, §10.4 | Added `entity` and `operation` as required. Ojas Data always has both at handle-request time; required gives the authority tighter scoping leverage without imposing Ojas-side cost. |
| **O-2.** Should `no-progress-halt-record` (§3.5) distinguish between *per-request* halts and *session-terminal* halts via the `terminal` boolean, or should they be separate record types? | **Resolved (v0.3.2)** | §3.5, §10.4 | `terminal` boolean retained as canonical for v0.3.x. Separate types not introduced; revisiting becomes a v0.4+ design change. |
| **O-3.** Is `pattern-confidence-class-code` (§6.2) `scope-match` a useful signal, or does it belong to a different defense (e.g., insider-threat detection)? | **Resolved (v0.3.2)** | §6.2, §10.4 | All three confidence classes kept. `scope-match` is preserved as a lower-confidence signal for collusion / account-compromise investigation. |
| **O-4.** Stream partitioning (§8.3) — `tenant-id` as default or finer-grained per very large single-tenant deployments? | **Resolved (v0.3.2)** | §8.3, §10.4 | Three permitted strategies defined in catalog (`tenant-id` default, `tenant+entity`, `tenant+entity+actor`). Runtime configuration selects one at deployment time. Schema validates `partition-key` as bounded string. |
| **O-5.** Should `reconciliation-batch-summary` (§7.2) carry digests of the records compared? | **Resolved (v0.3.2)** | §7.2, §10.4 | Added `compared-records-digest` and `gap-records-digest` as optional. Two digests, not merged — they separate comparison coverage from exception evidence so each can be re-verified independently. |

### Remaining freeze-blocking items (not v0.3.x open items, but flagged here for visibility)

- **§2.13 per-operation input shapes.** v0.3.2 stubs the six discriminated input types but does not define their full field shapes. Schema freeze requires these shapes to be closed via `additionalProperties: false`. See the §2.13 freeze-safety warning.
- **Schema correction list.** From the focused review report, schema corrections S1–S14 are pending. They apply downstream of catalog acceptance and will surface their own findings when implemented.
- **Parent control model edits.** Five small edits identified in the focused review report (§3.6 of that report) are pending in a separate turn per the work order.

No new open items raised by v0.3.2.

---

## Closing

This catalog is the v0.3.2 review-correction baseline. It supersedes v0.3.1 (which superseded v0.3, which superseded the v0.2 CDDL encoding-specific schema). It is schema-language-neutral by design.

The next downstream artifact, per parent §10, is JSON Schema generation from this catalog. That step happens after acceptance of this catalog completes.

O-1 through O-5 are resolved in this revision (see §10.4). Remaining freeze-blocking items are the per-operation input shapes for §2.13 (deferred to a future revision per the §2.13 freeze-safety warning) and any new findings from schema generation. Until those are addressed, this catalog is **review-correction draft**, not frozen.
