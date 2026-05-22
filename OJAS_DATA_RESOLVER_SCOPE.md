# Ojas Data — Resolver Scope (v1.0)

The Resolver Scope document specifies the resolver-layer authority and the compile-time path that produces it. It covers alias normalization, qualified aliases, registry compilation, scope handling, and drift detection.

For LLM-facing safety rules (channels, prompt design, hint emission, DB error handling), see [`OJAS_DATA_QUERY_REPAIR_BOUNDARY.md`](./OJAS_DATA_QUERY_REPAIR_BOUNDARY.md). For the developer onboarding flow (scanner, review CLI, conformance testing), see [`OJAS_DATA_DEVELOPER_GUIDE.md`](./OJAS_DATA_DEVELOPER_GUIDE.md).

---

## 1. Resolver authority model

### 1.1 Closed-world principle

The resolver matches business terms to fields **only** within the compiled metadata registry. A column that exists in the database but is not in the registry is, from the resolver's perspective, nonexistent.

This principle has three direct consequences:

- **No runtime schema discovery.** The resolver never queries the database to learn what columns exist. It uses the compiled registry's snapshot of approved entries.
- **No runtime authority extension.** Drift detection may report new columns; it never adds them to the runtime registry.
- **No inference of unknown terms.** If a term doesn't normalize to a registered alias, resolution fails terminally with `RESOLVER_UNKNOWN_FIELD_TERM` or `RESOLVER_UNKNOWN_ENTITY_TERM`.

### 1.2 Three-layer authority chain

Authority for the resolver flows through three layers, separated by responsibility:

```
Scanner output → Developer review → Compiled registry
  (discovery)     (approval)        (runtime authority)
```

- **Scanner output** discovers what exists in the database. It produces draft entities with draft aliases and heuristic suggestions. The scanner has no runtime authority.
- **Developer review** approves what is exposed, classifies sensitivity, assigns scope dimensions, and authors meaningful aliases. The developer's approvals are recorded in an overlay artifact that the compiler merges with scanner output.
- **Compiled registry** is the runtime authority. It is immutable per compile, reviewable as an artifact, and the only input the runtime resolver consults.

### 1.3 The compile step

The compile step takes:
- Scanner output (the discovered structure)
- Developer overlay (the approved meaning)

and produces:
- Compiled metadata registry (immutable runtime artifact)
- Reverse-alias index (for Safe Business-Term Hinting)
- Reviewable artifacts emitted alongside the registry

Compile failures are typed:
- `DRAFT_ENTRIES_REMAIN` — registry contains entries not approved by developer review
- `VALIDATION_FAILED` — manifest validation rules violated
- `CASE_FOLD_COLLISION` — two physical identifiers normalize to the same case-folded form
- `ALIAS_COLLISION` — two aliases normalize to the same form within a scope (see §3.5)
- `BINDING_DANGLING` — a `dataBindingRef` points to no `data-binding-v1` entry
- `CONTRACT_REFERENCE_INVALID` — a referenced canonical contract is not registered or is deprecated

Each failure produces a stable exit code (see [`OJAS_DATA_DEVELOPER_GUIDE.md`](./OJAS_DATA_DEVELOPER_GUIDE.md)).

---

## 2. Alias normalization

### 2.1 Match vs execute separation

Matching against the registry is case-insensitive and normalized. Execution against the database preserves identifiers verbatim.

- **Matching:** terms are normalized through the N1–N7 pipeline, then looked up against the normalized form of registered aliases
- **Execution:** the physical identifier from the registry is emitted to the database exactly as written in the source manifest

A case-fold collision between two physical identifiers (e.g., `CustomerName` and `customername`) is a **compile-time error**. The author must resolve the collision before the registry compiles.

### 2.2 The N1–N7 normalization pipeline

Applied uniformly to author-declared aliases and to user/LLM-provided terms:

| Step | Operation | Example |
|------|-----------|---------|
| N1 | Unicode NFKC normalization | `"E\u00ADmail"` → `"Email"` |
| N2 | Lowercase | `"Email"` → `"email"` |
| N3 | Replace separators (`-`, `_`, `.`) with space | `"contact-info"` → `"contact info"` |
| N4 | Collapse whitespace | `"contact    info"` → `"contact info"` |
| N5 | Strip leading/trailing whitespace | `"  contact "` → `"contact"` |
| N6 | Strip surrounding punctuation | `"contact."` → `"contact"` |
| N7 | Strip diacritics (NFKD + drop combining marks) | `"café"` → `"cafe"` |

### 2.3 NFKC coverage notes

N1 (NFKC) normalizes full-width forms to their half-width equivalents. CJK input forms are covered through this step. Implementers should not add additional half-width-folding logic.

### 2.4 Locale-controlled diacritic stripping

N7 is destructive for languages where diacritics carry meaning (Spanish, French, German, Vietnamese). For English-first deployments this is correct. For multilingual deployments, N7 must be controllable per locale.

The compile manifest may specify:

```yaml
normalization:
  diacritic_stripping:
    enabled: true
    locales: [en, en-US, en-GB]
```

When the locale of an incoming term doesn't match the enabled list, N7 is skipped for that term. The default for v1.0 is `enabled: true` for all locales; multilingual deployments must explicitly configure exceptions.

### 2.5 Normalization pipeline versioning

The N1–N7 pipeline is versioned. Every compiled registry records:

```yaml
normalization_pipeline_version: "1.0"
```

Pipeline changes (a future N8 step, or a different N7 algorithm) require a full registry recompile. In-place alias index migration is not permitted. The compile produces a new artifact with a new version identifier.

---

## 3. Qualified aliases

### 3.1 Purpose

When two columns share a business term, the resolver cannot unambiguously map the term to one column. Qualified aliases resolve this by adding a business-meaningful disambiguator to one or both aliases.

Bad (mechanical): `customer.status`, `invoice.status`
Better (qualified): `customer status`, `invoice status`
Best (business-domain): `account status`, `payment status`

### 3.2 The Qualified Alias Rule (freeze)

> Ojas Data may use qualified aliases to resolve normalized alias collisions. Author-supplied meaningful qualifiers are preferred. Compiler-generated qualifiers may be used only as an explicit compile-time opt-in and must be deterministic, reviewable, marked as compiler-generated, and included in the compiled registry. Runtime-generated qualifiers are forbidden. Qualified aliases are first-class business aliases: they may be used in resolver matching, safe user clarification, and Safe Business-Term Hinting if they pass policy, scope, and sensitivity gates. The registered qualified form is emitted consistently across scopes; runtime must not simplify or invent qualifier forms.

### 3.3 Qualifier types

Each qualified alias in the compiled registry carries a `qualifier_type` annotation:

| Type | Example | Use when |
|---|---|---|
| `ENTITY` | `customer email`, `account email` | Same field concept across entities |
| `ROLE` | `billing contact`, `shipping contact` | Same person/contact in different business roles |
| `LIFECYCLE` | `current status`, `previous status` | Same field concept differs by time/state |
| `OWNERSHIP` | `employee address`, `company address` | Same attribute applies to different owners |
| `DOMAIN` | `visa status`, `payment status`, `academic status` | Same word has different business meanings |
| `RELATIONSHIP` | `parent customer name`, `child customer name` | Same entity participates in different relationships |

Reviewers verify that the qualifier type matches the business distinction.

### 3.4 Alias origin metadata

Each alias in the compiled registry carries an `alias_origin`:

- `AUTHOR_SUPPLIED` — written by the developer in the source manifest
- `SCANNER_SUGGESTED` — proposed by the scanner, approved by the developer
- `COMPILER_GENERATED` — synthesized by the compiler under `auto_qualify_alias_collisions` opt-in
- `IMPORTED` — brought in from a registered alias library (reserved for future use)

The two annotations (`alias_origin` and `qualifier_type`) are orthogonal — every qualified alias has both.

### 3.5 Scope-aware alias collision rule (freeze)

> After normalization, no LLM-visible alias may map to more than one visible registry field within the same authorized resolution scope. Collisions must fail compile unless explicitly resolved through approved qualified aliases or deterministic opt-in auto-qualification.

The collision check operates on the **merged final alias set**, regardless of how each alias was authored or what role it plays. A natural alias on one entity and a qualified alias on another that normalize to the same form within the same scope is a collision and must fail compile.

### 3.6 Compile-time collision behavior

Default: fail with structured output.

```
ALIAS_COLLISION:
  normalized_alias: "status"
  entries:
    - invoice.status
    - visa_case.status
Suggested qualified aliases:
  - invoice status
  - visa case status
Action:
  Add meaningful qualifiers or enable auto_qualify_alias_collisions.
```

Machine-parseable JSON output via `--output-format json`.

### 3.7 Auto-qualify opt-in

```yaml
compile_options:
  auto_qualify_alias_collisions: true
  qualifier_strategy: ENTITY_CANONICAL_PREFIX_V1
```

Compiler-generated qualifiers are marked:
- `alias_origin: COMPILER_GENERATED`
- `review_required: true`
- `qualifier_type: ENTITY` (default for entity-prefix strategy)

The qualifier strategy is named and versioned. Future strategies (`ENTITY_CANONICAL_PREFIX_V2`, `BUSINESS_DOMAIN_PREFIX_V1`) are introduced as additional named strategies; existing registries continue to use their pinned strategy.

### 3.8 First-class alias status (freeze)

> A qualified alias is not a hint-only string. It is a first-class registry alias. If Ojas emits it in Safe Business-Term Hinting or user clarification, the resolver must be able to resolve that exact alias later.

This is the round-trip stability rule: what the LLM sees is what the resolver matches against. No translation layer between hint emission and resolver matching.

### 3.9 Emission uniformity across scopes (freeze)

> The runtime emits the registered qualified form consistently. It must not simplify a qualified alias to an unqualified alias merely because the current scope makes the term temporarily unambiguous.

The same field has the same alias surface in every scope where it appears. Scope-dependent simplification would break round-trip stability and create LLM-facing inconsistency.

### 3.10 Strictest-wins still applies (freeze)

> Qualified aliases do not bypass visibility gates. A qualified alias may be emitted only if the underlying field passes scope, policy, sensitivity, masking, and LLM-visibility checks.

A qualified alias on a sensitive field is suppressed from the LLM-facing hint channel, regardless of how natural the alias text looks.

### 3.11 Suppression of unqualified base alias on collision

If a base alias collides and qualified aliases are registered:

- `payment status` (registered, qualified)
- `visa status` (registered, qualified)
- `status` (the base term, ambiguous in this scope)

The LLM-facing hint surface emits only the qualified forms. The unqualified `status` is suppressed in any scope where the collision exists.

---

## 4. Scope handling

### 4.1 Scope dimensions

Scope is a multi-dimensional filter applied at resolution time. Each entity in the registry declares its scope dimensions:

```yaml
scope_dimensions:
  tenant: tenant_id
  region: region_code
  business_unit: bu_id
```

Each dimension maps a logical scope name to a physical column. Scope filtering is enforced at query construction time; the LLM never sees the scope columns.

### 4.2 Scope dimensions are not LLM-visible

The LLM-facing hint surface never names scope dimension columns. A scope violation produces a generic "this query is not authorized in the current scope" message, not a "the tenant_id predicate did not match" message. Scope filtering is silent.

### 4.3 Scope-aware alias visibility

An alias is LLM-visible in a scope only if:
- The entity is in scope
- The field is in scope
- The field is not policy-blocked in the current scope
- The field is not classified as sensitive (sensitive fields suppress from the LLM channel; see [`OJAS_DATA_QUERY_REPAIR_BOUNDARY.md`](./OJAS_DATA_QUERY_REPAIR_BOUNDARY.md))

The visibility computation runs at hint-emission time, derived from the compiled registry and the current scope.

---

## 5. Drift detection

### 5.1 The drift rule (freeze)

> Drift detected between the live database and the compiled registry produces a drift report. The drift report does not modify the registry. The registry is updated only by re-running the annotation-to-compile pipeline against an updated manifest and approving the result.

Drift detection is an observation mechanism, not an authority mechanism. It alerts; it does not auto-include.

### 5.2 Drift categories

| Category | Meaning | Severity |
|---|---|---|
| `NEW_FROM_INTROSPECTION` | Column exists in DB, not in registry | Medium — coverage opportunity |
| `REMOVED_FROM_INTROSPECTION` | Column in registry, not in DB | High — runtime errors imminent |
| `TYPE_CHANGED` | Column type changed | High — silent type coercion risk |
| `CONSTRAINT_CHANGED` | FK/unique/PK changed | Medium — semantic risk |
| `NEW_INDEX` | New index detected | Low — performance signal only |

### 5.3 Drift CLI output

```bash
ojas-data drift --registry compiled.ojas --db postgres://app
```

Exit codes:
- `0` — no drift
- non-zero — drift detected, severity in stdout

Machine-parseable output via `--output-format json` for CI integration.

### 5.4 Runtime drift behavior

The runtime trusts the compiled registry. It does not re-check drift on every query. A query that resolves to a registry-known field but fails at the database boundary (because the field was dropped) produces a `SCHEMA_DRIFT_SUSPECTED` operational alert in the privileged audit channel.

Deployments that require fresh drift verification per request must configure this explicitly. The default is "trust the compiled registry, alert on suspected drift."

---

## 6. Tenant boundary

### 6.1 v1.0 tenant model

The v1.0 design supports single-tenant deployments and multi-tenant deployments where the platform owns the entire registry. Tenant-authored overrides are deferred — see [`OJAS_DATA_DEFERRED_DESIGN_TOPICS.md`](./OJAS_DATA_DEFERRED_DESIGN_TOPICS.md).

### 6.2 Per-tenant compiled registries

Deployments needing tenant-specific aliases or classifications produce per-tenant compiled registries through the same compile pipeline. Per-tenant overrides at runtime are not supported in v1.0.

---

## 7. Resolver failure categories

The resolver emits failures through a closed enum. The discriminator-first principle (see [`OJAS_DATA_QUERY_REPAIR_BOUNDARY.md`](./OJAS_DATA_QUERY_REPAIR_BOUNDARY.md)) classifies these as authority-terminal.

| Category | Meaning | Retry-eligible? |
|---|---|---|
| `RESOLVER_UNKNOWN_ENTITY_TERM` | Term doesn't map to any registered entity | No (terminal) |
| `RESOLVER_UNKNOWN_FIELD_TERM` | Term doesn't map to any registered field | No (terminal) |
| `RESOLVER_AMBIGUOUS_TERM` | Term maps to multiple entries in current scope | No (terminal); may route to user clarification |
| `RESOLVER_SCOPE_VIOLATION` | Entity/field exists but not in current scope | No (terminal) |
| `RESOLVER_POLICY_DENIED` | Entity/field exists in scope but policy denies | No (terminal) |
| `RESOLVER_SENSITIVE_FIELD` | Entity/field exists but classified sensitive | No (terminal) |

These failures must never produce LLM-facing retry. See the Sufficient-Safe-Context rule in `OJAS_DATA_QUERY_REPAIR_BOUNDARY.md`.

---

## 8. Open documentation items

These items are known refinements for the v1.1 documentation pass. They do not block v1.0 freeze:

- Sensitive fields profile schema (referenced but not fully specified)
- Calibration methodology per agent/task/output/domain
- Locale-locale interaction matrix for N7
- Conformance corpus structure for scope-aware collision testing

---

## Appendix A — Resolver frozen principles

1. The compiled registry is the only authority for what entities and fields exist
2. Matching is case-insensitive and normalized; execution preserves identifiers verbatim
3. Case-fold collisions are compile-time errors
4. The N1–N7 normalization pipeline applies uniformly to authored aliases and incoming terms
5. The normalization pipeline is versioned; pipeline changes require full recompile
6. Qualified aliases resolve collisions; runtime cannot invent or simplify qualifiers
7. Qualified aliases are first-class — emitted forms must be resolvable
8. Scope dimensions are silent — never emitted to the LLM channel
9. Drift detection alerts; it never extends runtime authority
10. Resolver failures are authority-terminal — never LLM-retried
