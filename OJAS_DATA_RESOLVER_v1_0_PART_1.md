# Ojas Data Resolver Specification v1.0 — Part 1

**Version:** v1.0
**Status:** Final — complete resolver authority specification
**Scope:** ojas-data resolver (Core), including the two-tier registry, error model, approval workflow, full Pydantic boundary schemas, and the complete sanitized-feedback framework
**Companion spec referenced:** Ojas Data Query Repair Boundary Specification (separate document; not absorbed)

**This is Part 1 of 4.** Sections 1 through 8 — the core resolver specification.

- Part 1 (this file): §1 Purpose and boundary, §2 Core invariants, §3 Runtime modes, §4 Type and contract model, §5 Metadata authority, §6 Scope enforcement, §7 Stage 1 matching, §8 Retry boundary
- Part 2: §10–§16 — closed specification items
- Part 3: §17 — previously deferred sections now closed
- Part 4: Appendices A/B/C and freeze statement

**Changes from v0.4** are summarized in Part 4.

---

## 1. Purpose and boundary

In this document, **must**, **must not**, **should**, and **may** are normative when used in resolver rules. Other prose is descriptive.

The Ojas Data resolver is the component that turns an extracted user intent — already produced by the LLM extraction layer — into a deterministically-resolved set of governed metadata references that the policy engine, scope injector, credential selector, and query builder can act on. It is the load-bearing component for closed-world enforcement: every column, table, alias, and scope dimension that downstream layers operate on must have passed through the resolver.

The resolver owns the following responsibilities:

- Mapping extracted intent fields onto registered metadata entries — tables, columns, aliases, and declared scope dimensions
- Detecting and surfacing ambiguity as a terminal condition rather than guessing
- Producing an immutable resolved-intent structure that downstream layers consume as authoritative
- Refusing to resolve any reference that is not present in the compiled metadata registry
- Emitting structured resolution failures that the audit trail and (where permitted) the extraction-retry cell can consume

The resolver explicitly does not own:

- LLM extraction or candidate generation (upstream)
- Policy decisions about who may read which fields (downstream, owned by the policy engine)
- Sensitive-field blocking, row-scope predicate injection, or credential selection (downstream, owned by governance gates)
- Query construction, AST validation, dry-run execution, or result masking (downstream, owned by query builder and execution layers)
- Raw database diagnostic classification, read-only abstract-plan repair, or CUD mutation preflight (downstream, owned by the privileged query diagnostic classifier and mutation planner; see Ojas Data Query Repair Boundary Specification companion document)
- Audit ledger formatting or persistence (orthogonal, owned by audit)

**Non-goals.** The resolver is not a SQL generator, not a policy engine, not a schema discovery service, not a semantic search engine, and not an LLM reasoning component. Any feature request that requires the resolver to take on one of these roles is out of scope and belongs to a different component.

### Two API surfaces

The resolver exposes two distinct API surfaces, with different audiences and different error semantics. The full error-model specification is in §17.2.

**The pure core function.** A pure function that takes an extracted intent and a compiled registry and returns either a resolved intent or a typed failure value. The function is referentially transparent: same inputs produce same outputs, with no exceptions except for programmer-error conditions (invalid input types, contract violations). The pure core is the surface the test corpus exercises and the determinism suite asserts byte-identity against.

**The runtime entry-point wrapper.** The wrapper invokes the pure core, performs the approval check (§3, §17.3), and either returns the resolved intent or raises a typed exception derived from the failure value. This is the surface most application code consumes.

Both surfaces are part of v1.0. They are not alternatives — they are layered.

### Layer relationships

The resolver sits between LLM extraction and the governance gates. Its outputs are consumed by every downstream component, but it consults no downstream component during resolution.

| Layer | Owns | Consumes from resolver |
|---|---|---|
| LLM extraction | Intent extraction, candidate generation, schema repair | — |
| **Resolver pure core** (this document) | **Metadata resolution, ambiguity detection, closed-world enforcement** | **—** |
| **Resolver runtime entry-point wrapper** (this document) | **Approval check, exception translation, audit emission** | **Pure-core output** |
| Policy engine | Access decisions, sensitive-field rules | Resolved metadata references |
| Scope injector | Row-scope predicate construction | Resolved scope dimensions |
| Credential selector | Least-privilege credential mapping | Resolved entity access classes |
| Query builder | SQL/DSL generation, AST validation | Resolved metadata + governance decisions |
| Execution | Query execution, masking, result shape | Approved, scoped query |
| Privileged query diagnostic classifier *(companion spec: Query Repair Boundary)* | Classification of raw DB errors into sanitized repair categories | Resolved metadata (read-only context) |
| Mutation planner / preflight *(companion spec: Query Repair Boundary)* | CUD preflight checks, mutation policy, transaction rules | Resolved metadata + governance decisions |
| Audit | Evidence ledger | Every resolution outcome |

**Multi-entity resolution.** The resolved-intent structure is a collection of entity-level resolutions. Each entity is resolved independently using the same logic; the ordering and joining of entities is downstream work (query builder). The per-entity resolution logic described in this document applies uniformly regardless of how many entities appear in a single request. The structure and a worked example are in §15.

**Compile-step ownership.** The compile step that transforms Platform and Tenant Pydantic manifests into a single frozen-dataclass compiled index is owned by the resolver's deployment pipeline. The resolver at runtime receives only the already-compiled, immutable index. The compile step does not run at request time and is not accessible via the resolver's runtime API. The compile-step signature is in §11; two-tier merge rules are in §17.1.

---

## 2. Core invariants

The resolver enforces five invariants. These are not configuration; they are architectural commitments and are not made optional by any runtime mode.

**Closed-world metadata.** A reference resolves only if it exists in the compiled metadata registry. The registry is the resolver's view of the schema, not the database. A column that exists in the database but not in the registry **must** be treated identically to a column that does not exist at all. Introspection of the live database **must** be used to validate and reconcile the registry against reality, never to extend it.

**Terminal ambiguity.** When an extracted reference matches more than one registry entry — by alias, canonical name, or case-fold equivalence — resolution **must not** pick one. It **must** emit an ambiguity failure. The caller's options are clarification, registry disambiguation, or abandonment. There is no silent selection, no "most likely" candidate, and no positional fallback.

**Candidate exposure split.** The full ambiguity candidate set **must** be recorded in the internal failure object and in the audit ledger. The LLM-facing retry feedback (when `GOVERNED_EXTRACTION_RETRY` is active) **must not** receive the candidate set. User-facing clarification, when allowed by the calling layer, **must** use only registry-approved display labels or safe aliases, never physical table or column identifiers. The split — full detail to audit, sanitized form to LLM, safe labels to user — is what keeps terminal ambiguity both useful and safe. The complete visibility split is specified in §8.

**Deterministic authority.** Given a fixed compiled registry (which encodes a specific Platform-manifest version, Tenant-manifest version, and introspection snapshot per §11) and a fixed extracted intent, resolution **must** produce a fixed result. There **must not** be randomness, no LLM call, and no retrieval-augmented disambiguation inside the resolver. Two callers with the same inputs receive the same outputs.

**Retry never changes authority.** The extraction-retry cell may re-ask the LLM and produce a new extracted intent. That new intent **must** be resolved from zero against the same registry. The resolver **must not** retain partial resolution state across retry attempts, **must not** relax matching rules on subsequent attempts, and **must not** learn from prior failures within a request. Authority is recomputed every time.

| Invariant | What it forbids | Where it is enforced |
|---|---|---|
| Closed world | LLM-invented columns; introspection auto-include | Registry lookup step |
| Terminal ambiguity | Silent candidate selection; positional fallback | Match-set evaluation step |
| Candidate exposure split | Leaking candidate identifiers to LLM or end user | Failure-object serialization boundary |
| Deterministic authority | LLM-in-the-loop disambiguation; randomized tiebreak | Whole resolver |
| Retry never changes authority | Cross-attempt state; relaxed rules on retry | Resolver entry point |

---

## 3. Runtime modes

The resolver supports two runtime modes. The mode is recorded in the audit trail for every request. There are no other modes, and there will not be a Lite mode.

**`STRICT_DETERMINISTIC`** is the default mode. The resolver receives an extracted intent, performs resolution against the registry, and returns either a resolved-intent structure or a structured resolution failure. The LLM is not consulted during resolution. Failures are terminal for the request unless the caller is the extraction-retry cell operating under `GOVERNED_EXTRACTION_RETRY`.

**`GOVERNED_EXTRACTION_RETRY`** is the approved γ-only exception mode. It does not change resolver behavior — resolution itself remains deterministic, closed-world, and ambiguity-terminal. What it changes is the *envelope* around resolution: failures of certain categories may be returned to a bounded retry cell that re-asks the LLM with sanitized feedback (§8). Authority-category failures remain terminal regardless of mode. Use of this mode **must** be approval-gated via the `ApprovalRecord` mechanism specified in §17.3.

### Activation rule

A caller **may** request `GOVERNED_EXTRACTION_RETRY`, but the runtime entry-point wrapper **must** call the approval check before honoring it:

```
check_mode_authorization(
    agent_id: str,
    requested_mode: RuntimeMode,
    approval_registry: ApprovalRegistry,
    now: datetime
) -> ModeAuthorizationResult
```

The function returns one of three values:

- `AUTHORIZED` — a current, unrevoked, unexpired `ApprovalRecord` exists for `(agent_id, requested_mode)`. The requested mode is honored.
- `DOWNGRADED_TO_STRICT_DETERMINISTIC` — no valid approval exists, and runtime policy is configured to downgrade silently. The request proceeds in `STRICT_DETERMINISTIC` mode with an audit event recording the downgrade.
- `REJECTED` — no valid approval exists, and runtime policy is configured to reject. The request terminates with failure code `RUNTIME_MODE_NOT_AUTHORIZED` (§10).

The choice between `DOWNGRADED_TO_STRICT_DETERMINISTIC` and `REJECTED` is runtime-policy configuration, not per-request. Both behaviors are auditable. The activation rule closes the path where a prompt, an LLM output, or an untrusted tool configuration could self-select retry mode.

| Mode | Resolver behavior | Failure routing |
|---|---|---|
| `STRICT_DETERMINISTIC` | Deterministic, closed-world, ambiguity-terminal | All failures terminal |
| `GOVERNED_EXTRACTION_RETRY` | Deterministic, closed-world, ambiguity-terminal | Extraction-category failures → retry cell; authority-category failures → terminal |

---

## 4. Type and contract model

The resolver uses Pydantic v2 at every boundary and frozen dataclasses internally. This split is load-bearing for two reasons: Pydantic enforces validation and produces JSON Schema at the points where contracts cross trust boundaries, and frozen dataclasses give the hot path the immutability and performance the resolver needs.

The Pydantic boundary covers: the registry manifest schemas (Platform and Tenant); the extracted-intent DTO; the resolved-intent DTO; the structured resolution-failure types; the authoring-validation errors; and the `ApprovalRecord` artifact.

The frozen-dataclass internal layer covers: the compiled registry index that resolution consults at runtime; intermediate match-set representations during resolution; and the case-fold canonical-name index.

The compile step is the bridge between the two layers. Two Pydantic-validated manifests (Platform + Tenant) plus an introspection snapshot become a single frozen-dataclass compiled index by way of an explicit compile function (§11). The compiled index is the resolver's runtime authority; the manifests are the authoring authority. They are not interchangeable, and the compile step is the only path from one to the other.

| Surface | Form | Crosses trust boundary? |
|---|---|---|
| Platform registry manifest | Pydantic v2 BaseModel | Yes — authored by Platform owners, signed and approved |
| Tenant registry manifest | Pydantic v2 BaseModel | Yes — authored by Tenant owners, approved per tenant |
| Extracted intent DTO | Pydantic v2 BaseModel | Yes — produced by LLM layer |
| Resolved intent DTO | Pydantic v2 BaseModel | Yes — consumed by downstream layers |
| Resolution failure | Pydantic v2 BaseModel | Yes — consumed by audit, retry, and caller |
| Authoring validation error | Pydantic v2 BaseModel | Yes — surfaced to manifest author |
| `ApprovalRecord` | Pydantic v2 BaseModel | Yes — consumed by runtime check |
| Compiled registry index | Frozen dataclass + immutable maps | No — resolver-internal |
| Case-fold canonical index | Frozen dataclass | No — resolver-internal |
| Match-set intermediate | Frozen dataclass | No — resolver-internal |

The compiled index is treated as immutable for the lifetime of a registry version. Loading a new registry version produces a new compiled index; the old one is not mutated. This means concurrent resolution against a registry version is lock-free.

Full Pydantic schemas for every boundary type are in §16.

---

## 5. Metadata authority

The compiled metadata registry is the resolver's source of truth about what exists, what it is called, what aliases refer to it, and what governance attributes apply. The registry is constructed from two manifests — Platform and Tenant — authored by their respective owners and approved through the manifest-approval workflow.

### Two-tier authoring

**Platform manifest** declares the base layer. It is authored by Platform owners and changes only through the Platform manifest-approval workflow. Entries in the Platform manifest may carry governance flags (sensitivity, access class, scope-dimension columns) that are Platform-locked: a Tenant cannot override them. See §17.1 for the merge rules.

**Tenant manifest** declares the per-tenant overlay. It is authored by Tenant owners and changes through the Tenant manifest-approval workflow (which may be lighter-weight than the Platform workflow, depending on deployment governance). The Tenant manifest may:

- Add entirely new entities, columns, aliases, and scope dimensions not present in Platform
- Override non-sensitive properties on Platform entries (display labels, additional aliases, non-Platform-locked attributes)
- Never override Platform-locked properties (see §17.1 for the complete locked-property list)

The Tenant manifest is optional. A registry version compiled from a Platform manifest alone is valid.

### Authoring-to-runtime lifecycle

```
  Platform manifest (Pydantic v2)
        │
        ├──────────────┐
        │              │
        ▼              ▼
  Pydantic validation  Tenant manifest (Pydantic v2)
                         │
                         ▼
                   Pydantic validation
        │              │
        └──────┬───────┘
               ▼
   Introspection reconciliation
    (live DB ←→ merged manifest, drift surfaced)
               │
               ▼
   Compile
    (two manifests + snapshot → frozen-dataclass compiled index;
     merge rules in §17.1)
               │
               ▼
   Approval
    (manifest-approval workflow gates the compiled version)
               │
               ▼
   Immutable compiled index
               │
               ▼
   Runtime resolution
    (pure function of intent + compiled index)
```

The diagram is the spec. A registry version that has not passed every stage above **must not** be reachable by runtime resolution.

### Introspection role

Database introspection plays a specific and narrow role. It is run against the live database at registry compile time and at scheduled intervals afterward. Its job is to confirm that everything the merged manifest declares actually exists in the database with compatible types, and to surface drift. Introspection findings **must** be reported to the registry authors of both manifests. They **must not** silently extend the registry. A column that exists in the database but not in either manifest **must** be reported as drift and treated by the resolver as if it did not exist. The drift-report shape is specified in §12.

| Source | Authority | Resolver behavior |
|---|---|---|
| Platform manifest entry | Yes, after compile and approval | Resolves; Platform-locked properties cannot be Tenant-overridden |
| Tenant manifest entry (additive) | Yes, after compile and approval | Resolves; available for matching |
| Tenant manifest entry (override of non-sensitive Platform property) | Yes, after compile and approval | Resolves; Tenant value shadows Platform value; recorded as `TENANT_OVERRIDE` in layer provenance |
| Tenant manifest entry attempting override of Platform-locked property | No (rejected at compile) | Compile-time error `TENANT_OVERRIDE_REJECTED_PLATFORM_LOCKED` |
| Database column not in either manifest | No | Treated as nonexistent; reported as drift |
| Manifest entry not in database | No (broken) | Compile-time error `MANIFEST_DB_REFERENCE_BROKEN` |
| Introspection-only discovery | No | Logged as drift; never resolves |
| Runtime LLM suggestion | No | Closed-world refusal |

---

## 6. Scope enforcement

Scope dimensions — the dimensions that carry tenant identifiers, organization identifiers, region identifiers, or other dimensions that scope what rows a query may return — are declared in the metadata registry at the entity/table access-policy level. Scope is a property of the table, not a property of any individual column on it, and it is a property of the registry, not a property of any tool or use case that consults the registry.

A registry entry for a table declares which scope dimensions apply to it. Each dimension names the column on that table that carries the dimension value at runtime. The mapping from dimension name (e.g., `tenant_id`) to column (e.g., `customer_tenant`) is registry-owned. Tools and use cases may declare which scope dimensions they require, but they declare the dimension, not the column. The resolver consults the registry to determine which column on each resolved entity carries each declared dimension.

Field-level refinement is permitted as a special case but does not override the entity-level rule. A registry author may, on a specific column, indicate that the column itself participates in a scope dimension. The refinement points back to the entity-level dimension declaration; it does not introduce a new dimension or a new authority.

**Scope-dimension declarations are Platform-locked.** A Tenant manifest may not override the column-to-dimension mapping for an entity declared in the Platform manifest. A Tenant manifest may add scope-dimension declarations on entities the Tenant adds to the registry, but cannot redirect Platform-declared dimensions to different columns. This is enforced as a compile-time check (§17.1).

The resolver's output to the scope injector is a deterministic mapping from each resolved entity to the set of scope dimensions that apply to it and the columns that carry them. The scope injector is responsible for constructing the actual predicates; the resolver is responsible for telling it which columns to inject against.

**Terminology note.** "Scope dimensions" refer to the named dimensions declared at the entity level. "Scope columns" refer to the physical columns that implement those dimensions. Use cases declare required dimensions, not column names. The column-to-dimension mapping is never exposed to the LLM or the tool author.

### Worked example — scope dimensions at entity level

```
entity: customer
  columns: id, name, email, tenant_id, region
  scope_dimensions:
    tenant: tenant_id
    region: region

entity: customer_order
  columns: id, customer_id, total, tenant_ref, ord_region
  scope_dimensions:
    tenant: tenant_ref
    region: ord_region
```

A use case declares it requires `tenant` and `region` scope. The LLM extracts an intent to "show recent orders for active customers." The resolver maps this to the `customer` and `customer_order` entities and emits the following to the scope injector:

```
resolved_scope:
  customer:
    tenant -> tenant_id
    region -> region
  customer_order:
    tenant -> tenant_ref
    region -> ord_region
```

The LLM has not seen `tenant_id`, `tenant_ref`, `region`, or `ord_region`. The tool author has not picked them. The use case declared the dimensions. The registry declared the columns. The resolver produced the mapping.

### Worked example — what scope enforcement is not

If a use case declared `scope_columns = ["tenant_id"]` directly, the resolver **must** refuse the declaration. Column selection is registry authority, not use-case authority.

---

## 7. Stage 1 matching

Stage 1 of resolution is the alias-and-canonical-name match. It is the only stage at which natural-language vocabulary from the LLM meets the registry. Subsequent stages operate on resolved canonical entities.

Stage 1 matching **must** be case-insensitive. The case-fold operation **must** be Unicode case-folding — specifically, NFKC normalization followed by `casefold()` — not ASCII `lower()`. This matters for non-English schemas and for any future internationalization: Turkish dotted `İ`, German `ß`, ligatures, and combining marks all need to match consistently. ASCII `lower()` would silently mishandle these.

Aliases and canonical names are folded at compile time, not at match time. The compiled registry index carries a case-fold index that maps each folded form to its canonical entry. Match-time lookup is a single map access against the folded query term.

Physical database identifiers **must not** be case-folded. They are preserved exactly as declared in the manifest and used verbatim in generated SQL or DSL.

Case-fold collisions **must** be compile-time errors. The compile error names the colliding entries and the folded form. The registry author resolves the collision either by removing one alias, by scoping the aliases to different entities, or by declaring an explicit disambiguation as specified in §13.

### Worked example — case-insensitive match, case-preserved execution

```
entity: customer
  physical_name: "Customer"
  canonical: customer
  aliases: ["customers", "client", "clients"]
  columns:
    - canonical: full_name
      physical_name: "FullName"
      aliases: ["name", "customer name", "client name"]
```

An LLM extracts the intent term `Customer Name`. The resolver folds it to `customer name`, looks up the folded form in the case-fold index, and returns the resolved reference: entity `customer`, column `full_name`. The query builder later receives the resolved reference and generates SQL using the physical identifiers: `SELECT "Customer"."FullName" FROM "Customer"`.

### Worked example — collision detected at compile

```
entity: account
  columns:
    - canonical: account_number
      aliases: ["acct no", "account #"]
    - canonical: acct_no
      aliases: ["acct no"]
```

The alias `acct no` appears on two different columns of the same entity. Both fold to the same form. The manifest fails compile with `CASE_FOLD_COLLISION`. See §13 for disambiguation resolution.

---

## 8. Retry boundary

The resolver does not retry. The extraction layer does. The retry boundary is γ-only: the LLM **may** be re-asked to repair its extraction, but no retry attempt **may** change the resolver's authority decision. Every retry attempt produces a new extracted intent that is resolved from zero against the same registry.

### Failure classification by source layer

Failures during a `GOVERNED_EXTRACTION_RETRY` request originate from four source layers within the resolver's authority surface. The retry-routing decision depends on the source.

| Source layer | Example failures | Retry status |
|---|---|---|
| Extraction / DTO layer | Malformed intent DTO, missing required intent field, invalid enum value, malformed or under-specified extraction that has not yet reached the resolver | Retry-eligible |
| Resolver | Unknown table or column, terminal ambiguity (multiple registry candidates), unresolved alias, case-fold disambiguation required | Terminal |
| Governance gates (downstream of resolver) | Policy denial, sensitive-field block, scope-dimension missing, credential class mismatch, row-scope failure | Terminal |
| Runtime envelope | Mode authorization missing or revoked | Terminal |

Once a term has reached resolver matching and produced multiple registry candidates, it is **resolver ambiguity** and **must** be treated as terminal. Pre-resolution extraction repair is a different category and is the only category in which retry is allowed to affect the authority decision (by producing a different extracted intent on re-ask).

The boundary between source layers **must** be enforced in code, not by convention. The exhaustive failure enum is in §10.

### Repair information vs. authority information

The sanitized-feedback rule has a load-bearing principle: **the LLM may receive repair information, never authority information**. Repair information is what the LLM needs to fix its own output shape. Authority information is what the resolver and downstream governance gates know about the data model.

Two kinds of "field names" exist, with opposite visibility rules:

- **DTO/schema field names** (e.g., `entities`, `fields`, `role`, `term`, `disambiguator`) — safe to surface in LLM-facing feedback because they describe the extraction contract the LLM must produce against
- **Business/database/registry field names** (e.g., `ssn`, `salary`, `tenant_id`, `employee_internal_notes`) — never surfaced in LLM-facing feedback when the field is denied, ambiguous, unknown, sensitive, or policy-blocked

The distinction is enforced at the retry-cell template function's type signature: the template accepts only DTO-typed inputs and the approved-set of DTO enum values. It cannot accept registry types. This makes the rule a compile-time property, not a convention.

### Channel-specific visibility

Privileged diagnostic information exists and must be preserved for legitimate consumers (audit, operator, registry author). The constraint is on the LLM-facing channel, not on the existence of the information.

| Information | LLM retry prompt | User-facing message | Internal audit | Operator/developer diagnostics |
|---|---|---|---|---|
| Failure category | Yes | Maybe | Yes | Yes |
| Allowed DTO enum values | Yes | Usually no | Yes | Yes |
| DTO field names (`role`, `entities`, `fields`) | Yes | No | Yes | Yes |
| Physical table name | No | No | Yes | Yes, RBAC-gated |
| Physical column name | No | No | Yes | Yes, RBAC-gated |
| Constraint name | No | No | Yes | Yes, RBAC-gated |
| Raw SQL error text | No | No | Maybe, redacted | Yes, secure diagnostic channel |
| Registry candidate set | No | Safe labels only if clarification allowed | Yes | Yes |
| Policy reason | No | Generic or approved message | Yes | Yes, RBAC-gated |
| Missing row-scope predicate | No | No | Yes | Yes, RBAC-gated |
| Credential class hint | No | No | Yes | Yes, RBAC-gated |
| Layer provenance (Platform / Tenant) | No | No | Yes | Yes |

### Sanitized retry feedback rule

When an extraction-repairable failure is routed to the retry cell, the feedback message that reaches the LLM **must** be constructed from a fixed template that takes only DTO-level inputs (failure category, allowed-set of DTO enum values, DTO field names). The template **must not** accept registry-typed inputs of any kind.

The following information **must not** appear in the LLM-facing retry channel: registry/business field names, denied values, denial reasons, missing row-scope predicates, credential-class hints, raw SQL errors, physical table and column names, constraint names, query plans, database engine messages, layer provenance, approval-status detail. Each of these may be recorded in the internal audit ledger and in operator/developer diagnostics under access control, subject to redaction policy.

**Worked example — sensitive-field block.**

User asks: *"Show employee tax identifier."*

LLM extracts:

```yaml
field_term: "ssn"
role: "PROJECT"
```

The resolver resolves `ssn` to a sensitive column. The downstream governance gate emits `GOVERNANCE_SENSITIVE_FIELD_BLOCKED`. This is authority-terminal.

**Unsafe feedback** (must not be emitted):

```text
Field "ssn" is sensitive and blocked by policy HR_PII_DENY.
Try another field.
```

This teaches the LLM that `ssn` exists, that it is sensitive, the name of the blocking policy, and that other nearby fields might work. Each of these is a separate leak.

**Safe outcome** (terminal, no retry):

```text
Request cannot be completed under current data access policy.
```

The audit ledger receives the full failure record including the physical field name, the sensitivity flag, the policy reference, and the layer provenance. The LLM channel receives nothing further.

**Worked example — DTO enum repair.**

LLM extracts:

```yaml
field_term: "employee name"
role: "show"
```

The DTO validator emits `EXTRACTION_ENUM_INVALID`. This is retry-eligible.

**Safe retry feedback** (emitted to LLM):

```text
EXTRACTION_ENUM_INVALID. Allowed values for role: [PROJECT, FILTER, GROUP, ORDER].
Return corrected extraction only.
```

The LLM has enough information to fix `role: "show"` to `role: "PROJECT"`. It has not learned any registry field name.

**Footnote on alias sensitivity.** Registry authors should avoid using raw database column names as aliases when those names are themselves sensitive (e.g., a column named `ssn` with alias `ssn`). Best practice is to use business-friendly aliases ("tax identifier").

### Sufficient-safe-context rule

A failure is retry-eligible only if the retry cell can provide enough non-sensitive context for the LLM to repair the output. If meaningful repair would require exposing denied fields, physical identifiers, resolver candidates, raw database errors, policy reasons, row-scope predicates, credential classes, or hidden registry structure, the failure **must not** be retry-eligible. It **must** terminate or route to a non-LLM repair path.

The non-LLM repair paths are:

| Path | Destinations |
|---|---|
| Registry author | `RESOLVER_UNKNOWN_*`, `RESOLVER_DISAMBIGUATION_REQUIRED`, compile-time drift findings |
| User clarification (safe labels only, per §2 candidate-exposure split) | `RESOLVER_AMBIGUOUS` |
| Policy / access management | `GOVERNANCE_POLICY_DENIED`, `GOVERNANCE_SENSITIVE_FIELD_BLOCKED`, `GOVERNANCE_CREDENTIAL_MISMATCH` |
| Operator / developer diagnostics (privileged channel) | `RUNTIME_MODE_NOT_AUTHORIZED`, downstream query-builder / execution failures (companion spec) |

### Runtime caps outside retry count

The retry cell **must** operate inside an envelope that enforces, independently of retry count: a maximum wall-clock duration per request; a maximum LLM token budget per request; a maximum tool-call count per request; no-progress detection; and circuit-breaker behavior on shared dependencies.

A request that exhausts wall-clock, tokens, or tool-call budget **must** terminate regardless of how many retries it has left. A no-progress signal **must** terminate regardless of budget.

### No-progress detection

"No-progress" is defined as two consecutive retry attempts that produce the same resolution-failure signature, where the signature is the tuple `(failure_category, failed_field_term)` for field-level failures, and the tuple `(failure_category, entity_name)` for entity-level failures.

### Audit

Every retry attempt **must** be logged with attempt number, the resolution-failure category that triggered the retry, the sanitized feedback emitted to the LLM, and the cap state.

### Forward-looking note — Query Repair Boundary companion spec

The retry boundary specified in this section governs resolver-layer and governance-layer failures only. Downstream layers — query builder, execution, raw database diagnostics, read-only abstract-plan repair, and CUD mutation preflight — are covered by a separate companion specification: **Ojas Data Query Repair Boundary Specification**.

The companion spec extends the same channel-routing principles to additional source layers (query builder, execution, mutation planner) and additional failure categories. The sufficient-safe-context rule, the visibility-split table, and the two-kinds-of-field-names distinction apply identically in the companion spec. The companion spec also covers the privileged query diagnostic classifier and the rule that CUD failures are never LLM-repairable.

**Part 1 ends here. Part 2 begins with §10 (failure category discriminator). §9 is reserved as a numbering placeholder so cross-references from prior versions remain stable.**
