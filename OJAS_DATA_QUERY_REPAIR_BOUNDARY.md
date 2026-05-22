# Ojas Data — Query Repair Boundary (v1.0)

The Query Repair Boundary spec defines the LLM-facing safety surface of Ojas Data. It specifies which content crosses the boundary to the LLM, through which channel, with what shape, under which constraints, and which content remains privileged. This document is the canonical statement of what the LLM may and may not see.

For resolver authority and alias normalization, see [`OJAS_DATA_RESOLVER_SCOPE.md`](./OJAS_DATA_RESOLVER_SCOPE.md). For the developer-facing tooling that exercises these rules, see [`OJAS_DATA_DEVELOPER_GUIDE.md`](./OJAS_DATA_DEVELOPER_GUIDE.md).

---

## 1. Foundational principles

### 1.1 Strictest-wins gate composition (freeze)

> A field or hint must pass every applicable visibility, policy, sensitivity, scope, masking, and LLM-visibility gate. Any failed gate suppresses emission, regardless of how many other gates the field passes.

Gates compose by suppression. There is no override or exception that lets a field pass a strict gate because it passed others. The strictest gate wins.

This rule resolves multi-gate composition for the entire system:

- Approved scope + sensitive field → suppress
- Approved alias + policy denial → suppress
- Safe display label + LLM channel + sensitive classification → suppress
- Registered field + unapproved use case → suppress

### 1.2 The discriminator-first principle (freeze)

> The failure category is decided before the retry decision. Extraction-repairable failures (`EXTRACTION_*` enum values) may be retried by the LLM. Authority-terminal failures (`RESOLVER_*`, `POLICY_*`, `SCOPE_*`, `SENSITIVE_FIELD_*`, `CREDENTIAL_*`, `MUTATION_*`) are never LLM-retried.

The failure enum encodes retry eligibility per value. The retry cell consults the enum before constructing any LLM-facing payload.

### 1.3 Channel separation (freeze)

> The LLM-facing retry channel and the user-clarification channel are physically separate code paths. Not "the same function with a flag." Two functions, two reviewers, two audit categories.

Each channel has its own allowed-content set, its own audit category, and its own implementing code. A safety property that holds in one channel does not automatically hold in the other; each channel must be reviewed independently.

### 1.4 Authorized-context, not failed-input (freeze)

> LLM-facing emissions derive from already-authorized context, never from the failed input. Identical scope produces identical emission shape regardless of what input triggered the emission.

This rule prevents the LLM from probing the authorization surface by varying input. Whether the LLM submitted `CustomerEmail`, `customer_email_address`, `email_of_customer`, or nothing at all, the available terms in a given scope are the same.

---

## 2. The privileged diagnostic classifier

### 2.1 Role

The privileged diagnostic classifier is the boundary component that separates raw runtime artifacts from sanitized LLM-facing or user-facing emissions. It is the only component that reads both the raw runtime output (DB errors, response payloads, exception traces) and the compiled registry.

### 2.2 Inputs

- Raw database diagnostics (errors, hints, constraint names, table names, column names)
- Successful database response payloads
- Runtime exception traces
- Compiled metadata registry
- Current request scope and policy bindings
- Failure category from the discriminator

### 2.3 Outputs

For each incoming raw artifact, the classifier emits one of three outcomes:

- **Safe business-term emission** — if the artifact resolves to an authorized non-sensitive alias within the current scope, emit the registry-derived business form
- **Generic suppression message** — if the artifact resolves but is sensitive, out of scope, or policy-blocked
- **No emission at all** — if the artifact does not resolve to any registered entity

The classifier never echoes raw output to any LLM-facing or user-facing channel.

### 2.4 The classifier as both runtime and CLI surface

The classifier is enforced at runtime (before any LLM-facing or user-facing emission) and is exercisable via CLI (`ojas-data sql classify-error`, `ojas-data sql safe-hint`) for review and conformance testing. Both surfaces must produce identical outputs for identical inputs.

### 2.5 Outbound filtering (freeze)

> Successful database responses must pass through privileged filtering before reaching LLM or user-facing channels. The classifier identifies sensitive fields in the response payload and removes them, regardless of policy on the request side.

This extends the classifier's role from inbound (filtering errors) to outbound (filtering successful responses). The same classifier sees both directions.

---

## 3. The four LLM-facing safety freezes

These four rules together specify what the LLM may and may not see across all surfaces. They are stated as freezes because they are the load-bearing safety properties of the design.

### 3.1 Unknown References Rule

> Unknown physical references are never LLM-repairable. If a query or extracted term cannot be resolved to the compiled registry, the LLM must not receive raw database errors, hints, physical identifiers, or candidate sets. The repair path is registry update, safe user clarification, or privileged developer/operator correction. Ambiguity may be clarified only through approved display labels or safe aliases, never through physical schema details.

### 3.2 Safe Business-Term Hinting Rule

> In SQL Review or approved read-only abstract query-repair flows, Ojas Data may provide the LLM with safe business-term hints only from the compiled metadata registry. Hinting is enabled by deterministic normalization — whitespace normalization, Unicode case-folding, alias normalization, and (where the input is raw SQL) SQL comment stripping — but is authorized only through a reverse-alias index and safe-hint policy. The reverse-alias index maps approved physical registry entries to registry-approved business aliases; it is built at compile time from the same approved manifest as the resolver index, emitted as a reviewable artifact, and subject to the same change-review process. A hint may be emitted only when the referenced field is registered, visible in the current approved entity/use-case scope, not policy-blocked, and not classified as sensitive — sensitive fields are excluded from the LLM-facing hint channel entirely, even when a safe display label exists. The emitted list of approved business terms is a function of the request's authorized scope, not of the failed input token; identical scope produces identical list shape regardless of the input that triggered the hint. The LLM-facing message must not echo the failed physical token, raw SQL error, table name, column name, database hint, constraint name, or any other physical schema detail. If no safe alias is available — whether because the field is unregistered, out of scope, sensitive, or policy-blocked — no hint is emitted, the LLM-facing message in the no-hint case is identical regardless of which gate suppressed the hint, and the failure remains terminal or routes to privileged diagnostics.

> **Hinting is not schema repair.** Safe Business-Term Hinting does not allow the LLM to discover hidden schema or repair database-side failures. It only reminds the LLM of approved business terms that were already visible under the current registry, policy, and scope context.

### 3.3 DB HINT Replacement Rule

> Raw database hints are privileged diagnostics and must not appear in any LLM-facing or user-facing channel that derives from runtime error text. Ojas Data may replace them with Safe Business-Term Hinting in the LLM-facing retry channel only when the hint can be derived from the compiled registry's approved aliases, filtered by request scope, policy visibility, and sensitivity classification. The LLM-facing emission must contain no string that normalizes (under the resolver's N1–N7 normalization pipeline) to the same form as the failed input token. Safe Business-Term Hinting applies only in read-only SQL Review or approved read-only abstract query-repair flows; CUD operation failures are excluded entirely and route through the CUD Mutation Visibility path. If no safe business alias is available — whether because the field is unregistered, out of scope, sensitive, or policy-blocked — no hint is emitted and the failure remains terminal or routes to privileged diagnostics.

### 3.4 CUD Mutation Visibility Rule

> CUD (create, update, delete) operation failures are never LLM-repairable. The LLM receives only safe business-level error categories, approved display labels, required-input prompts, and approved next-action choices. Raw database diagnostics, constraint names, foreign key names, policy reasons, and SQL fragments remain privileged. CUD failures are repaired through deterministic preflight checks, mutation policies, transaction rules, user clarification, or operator action — never through LLM SQL repair.

---

## 4. The five-channel prompt taxonomy

Every LLM-facing emission flows through one of five channels. The taxonomy is closed; channels not in this list are forbidden by design.

| Channel | Purpose | Allowed in Ojas Data | Used for |
|---|---|---|---|
| Extraction prompt | Convert user request into structured DTO | Yes | Normal NL → ExtractedIntent |
| Extraction-repair prompt | Fix malformed/invalid DTO | Yes, bounded | `EXTRACTION_*` retry only |
| Safe message-generation prompt | Explain safe result/failure to user | Yes, sanitized | CUD generic messages, clarification text |
| Read-only query-repair prompt | Repair abstract read-only query plan | Optional future companion | Query Repair Boundary only |
| Mutation-repair prompt | Repair CUD SQL/mutation failure | **Forbidden** | Not registered, by design |

The forbidden mutation-repair channel is named in the taxonomy precisely so its non-existence is a reviewable property. A reviewer searching for `OD_MUTATION_REPAIR` in the profile registry must find nothing.

---

## 5. Three-layer prompt design

### 5.1 The schema-first contract

Plain-text prompts are not sent at runtime. Each LLM-facing emission uses a three-layer contract:

- **Prompt schema** — defines the field surface (`allowed_input_fields`, `forbidden_input_fields`, `allowed_failure_categories`, `output_contract`)
- **Prompt profile** — registered instruction text bound to a schema, versioned and reviewable
- **Runtime payload** — per-call structured input conforming to the schema, sent alongside the profile reference

### 5.2 Why three layers

The schema is the **executable validator** — it runs before prompt construction. A payload with a forbidden field is rejected before any LLM call. This is the first enforcement boundary.

The profile is the **standing instructions** — registered once, versioned, fingerprinted. The profile fingerprint is part of the audit triple.

The payload is the **per-call data** — small, structured, conforming to the schema. It carries only what changes per request.

### 5.3 The Prompt Schema Forbidden-Field Rule (freeze)

> Prompt schema validation must reject forbidden fields such as physical identifiers, raw DB errors, policy reasons, and candidate sets before prompt construction. Schemas are not reference documents; they are executable validators invoked on every payload. Schema validation failures are terminal — they do not produce a corrected payload, they produce an internal error logged to the privileged diagnostic channel.

### 5.4 Schema-to-profile binding

A schema may be bound by one or more profiles. A profile binds to exactly one schema.

Example:
- `OD_SAFE_MESSAGE_SCHEMA` may be bound by:
  - `OD_SAFE_MESSAGE_GENERIC_V1`
  - `OD_SAFE_MESSAGE_CUD_V1` (constrained sub-case)
  - `OD_SAFE_MESSAGE_SENSITIVE_V1` (sensitive-field-redirect case)

All three profiles share the same field surface (the schema) but apply different instructions. Schema changes require re-review of every bound profile.

### 5.5 Output contract pinning

The `output_contract` field in a prompt schema must reference a canonical contract registered in the Ojas data contract registry. Contract versions referenced from schemas must be `PINNED` (per the broader Ojas freeze on model identity). `RESOLVED` or `UNKNOWN` versions are not permitted in prompt schemas.

### 5.6 Visibility manifest

Each envelope carries a visibility manifest derived from the profile, not authored per-call:

```yaml
visibility:
  physical_identifiers: false
  raw_db_errors: false
  policy_reasons: false
  candidate_sets: false
```

The visibility manifest is a derived property of the profile, not a runtime knob. The runtime cannot relax visibility per emission.

### 5.7 Profile fingerprint and audit triple

Every emission is recorded with:

```yaml
audit_entry:
  profile_id: "OD_SAFE_MESSAGE_V1"
  profile_version: "1.0"
  profile_fingerprint: <hash of instruction text>
  schema_id: "OD_SAFE_MESSAGE_SCHEMA"
  envelope_fingerprint: <hash of the structured envelope>
  llm_response_fingerprint: <hash of the LLM output>
```

A profile whose fingerprint doesn't match the registered fingerprint fails closed in production. (Non-production behavior is configurable — see [`OJAS_DATA_DEVELOPER_GUIDE.md`](./OJAS_DATA_DEVELOPER_GUIDE.md) for defaults.)

### 5.8 The four prompt profile examples

#### Extraction prompt

```yaml
profile_id: OD_EXTRACT_V1
schema_id: OD_EXTRACT_SCHEMA
instructions:
  - Extract the user's request into the required DTO only.
  - Use only business terms from the user request.
  - Do not invent physical table names or physical column names.
  - Do not infer policy, scope, or credentials.
  - Do not generate SQL.
  - Return only valid JSON matching the schema.
output_contract: ExtractedIntent.v1
```

#### Extraction-repair prompt

```yaml
profile_id: OD_EXTRACT_REPAIR_V1
schema_id: OD_EXTRACT_REPAIR_SCHEMA
instructions:
  - Repair only the extraction DTO.
  - Do not generate SQL.
  - Do not infer database table or column names.
  - Do not add fields not present in the user request.
  - Return only valid ExtractedIntent.v1 JSON.
output_contract: ExtractedIntent.v1
allowed_failure_categories:
  - EXTRACTION_DTO_MALFORMED
  - EXTRACTION_FIELD_MISSING
  - EXTRACTION_ENUM_INVALID
  - EXTRACTION_UNDERSPECIFIED
```

#### Safe message-generation prompt

```yaml
profile_id: OD_SAFE_MESSAGE_V1
schema_id: OD_SAFE_MESSAGE_SCHEMA
instructions:
  - Generate a safe user-facing message.
  - Do not mention internal policy names.
  - Do not mention database tables, columns, constraints, SQL, IDs, or stack traces.
  - Use only the approved display terms provided.
  - Do not suggest workarounds.
  - Keep the message concise and actionable.
output_contract: SafeUserMessage
```

#### Forbidden mutation-repair (not registered)

```yaml
# OD_MUTATION_REPAIR
# Status: FORBIDDEN_BY_DESIGN
# This profile is not registered. Its non-existence is a reviewable property.
```

---

## 6. Sufficient-safe-context rule (freeze)

> If the LLM cannot fix the failure without protected context (raw DB errors, physical identifiers, policy reasons, candidate sets), no LLM retry is attempted. The failure is classified as authority-terminal and routes to the appropriate non-LLM path (registry update, user clarification, operator action).

This rule names the constraint behind every authority-terminal classification. It is the foundational reason for the discriminator-first principle and the channel separation.

---

## 7. SQL comment stripping

### 7.1 Purpose

When the LLM submits raw SQL (in SQL Review Mode or approved query-repair flows), the SQL may contain comments that could leak hints, credentials, or prompt-injection text into downstream analysis or audit. Comments are stripped before AST extraction or policy check.

### 7.2 Dialect-aware tokenizer

Comment stripping requires a dialect-aware tokenizer. Specifically:

- A `/* ... */` inside a string literal must not be stripped
- An unterminated block comment is a tokenization error, classified as a terminal failure category
- The tokenizer is dialect-specific (PostgreSQL, MySQL, SQL Server, etc.); the dialect must be specified per registry

### 7.3 Original SQL audit preservation

The original SQL is preserved verbatim in the privileged audit ledger. The stripped form is used only for AST and policy analysis. A reviewer investigating a credential leak via comment needs to see what was actually submitted.

### 7.4 Credential pattern detection (deferred)

Credential patterns in comments (API keys, passwords, connection strings) are subject to further classification by a future credential-scrubbing layer. v1.0 strips comments uniformly without distinguishing credential content.

---

## 8. Runtime caps and no-progress detection

### 8.1 Runtime caps

Every request runs inside a runtime envelope with budget caps:

- Wall-clock budget
- LLM token budget (input + output + total)
- Tool-call count
- Validator call count
- Model cost
- Tool cost

Exceeding any cap terminates the request and routes to safe message-generation.

### 8.2 No-progress detection

Two identical failure signatures within a single request terminate the retry cycle with `EXTRACTION_NO_PROGRESS`. The default treats identical failure category as no progress regardless of value variation (a strict interpretation). Deployments may configure a relaxed interpretation; see [`OJAS_DATA_DEVELOPER_GUIDE.md`](./OJAS_DATA_DEVELOPER_GUIDE.md).

### 8.3 Circuit breaker

If a single channel or profile produces persistent failures across multiple requests, the channel is temporarily disabled and routed to the safe message-generation fallback. The circuit breaker is per-deployment policy; defaults are conservative.

---

## 9. Compose flow

The full LLM-facing emission flow:

```
Request arrives
  ↓
Discriminator classifies any incoming failure category
  ↓
Channel selected from taxonomy
  ↓
Profile selected, schema looked up
  ↓
Payload constructed (only with allowed fields)
  ↓
Schema validator runs (reject forbidden fields → terminal)
  ↓
Privileged diagnostic classifier runs (for any DB-derived content)
  ↓
Gate composition applied (strictest-wins)
  ↓
LLM prompt constructed from profile + payload
  ↓
LLM called
  ↓
Response validated against output contract
  ↓
Audit triple recorded
  ↓
Emission returned to caller
```

Each step has a freeze rule that constrains it. Failures at any step route to the safe message-generation channel.

---

## 10. Open documentation items

These items are known refinements for the v1.1 documentation pass. They do not block v1.0 freeze:

- Concrete `SafeUserMessage` schema specification
- Per-dialect tokenizer reference list
- Credential pattern detection companion spec
- Channel-to-profile reference catalog (the full list of registered profiles)
- Exit conditions specification for each channel (what happens when the channel itself fails)

---

## Appendix A — Query Repair Boundary frozen principles

1. Strictest-wins gate composition applies across all gates
2. The discriminator-first principle classifies failures before retry decisions
3. The LLM-facing retry channel and the user-clarification channel are physically separate
4. Emissions derive from authorized context, not from failed input
5. The privileged diagnostic classifier is the boundary between raw and sanitized
6. Outbound responses pass through the classifier, not just inbound errors
7. The four LLM-facing safety freezes (Unknown References, Safe Business-Term Hinting, DB HINT Replacement, CUD Mutation Visibility)
8. The five-channel prompt taxonomy with one forbidden channel
9. The three-layer prompt design (schema / profile / payload) with executable schema validation
10. The sufficient-safe-context rule grounds all authority-terminal decisions
11. Profile fingerprints fail closed in production
12. SQL comment stripping is dialect-aware and preserves original SQL in audit
