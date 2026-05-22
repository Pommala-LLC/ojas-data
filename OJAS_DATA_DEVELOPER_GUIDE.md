# Ojas Data — Developer Guide and CLI Reference (v1.0)

This document is the operational manual for Ojas Data. It covers the scanner pipeline, the generated/ + overlay model, CLI reference, conformance testing, and the operational defaults that deployments may configure.

For resolver authority and alias rules, see [`OJAS_DATA_RESOLVER_SCOPE.md`](./OJAS_DATA_RESOLVER_SCOPE.md). For LLM-facing safety rules, see [`OJAS_DATA_QUERY_REPAIR_BOUNDARY.md`](./OJAS_DATA_QUERY_REPAIR_BOUNDARY.md). For product positioning and the developer-experience headline, see [`OJAS_DATA_POSITIONING.md`](./OJAS_DATA_POSITIONING.md).

---

## 1. Developer journey

### 1.1 The end-to-end flow

```
Database schema
  ↓
ojas-data scan
  ↓
Generated entity classes + draft annotations
  ↓
Developer reviews via ojas-data review
  ↓
Overlay file (registry.overrides.yaml) captures decisions
  ↓
ojas-data compile (merges generated + overlay)
  ↓
Immutable compiled registry
  ↓
Application uses compiled registry through resolver
```

Six steps. Most of the work is in step 3 (review); steps 1, 2, 4 are automated; step 5 produces the runtime artifact; step 6 is the integration target.

### 1.2 What the developer authors

The scanner discovers structure; the developer authors meaning. Specifically, the developer's review provides:

1. Business aliases (the LLM-facing vocabulary)
2. Sensitive/non-sensitive classification
3. Scope dimensions and bindings
4. Access classes and policy tags
5. Safe display labels for user clarification
6. Relationship hints if query builder needs joins
7. CUD mutation rules if mutations are supported

Everything else — physical structure, types, constraints, alias normalization, collision detection, compilation, drift detection — is generated, validated, or enforced by Ojas Data.

### 1.3 The generated/ + overlay model

The scanner writes generated entities into a `generated/` directory that the developer never edits. Developer overrides live in a separate overlay file (`registry.overrides.yaml`) that the compiler merges with the generated definitions.

```
project/
├── generated/                    # scanner-generated, never edit
│   ├── entities/
│   │   ├── customer.yaml
│   │   ├── invoice.yaml
│   │   └── ...
│   └── schema_profile.json
├── registry.overrides.yaml       # developer-authored, version-controlled
├── ojas-data.config.yaml         # compile options, profile registry, etc.
└── compiled/                     # compile output (gitignored or artifact-stored)
    ├── registry.ojas
    └── reverse_alias_index.json
```

Re-running the scanner regenerates the `generated/` directory without touching the overlay. The compiled registry reflects both layers; the overlay is the developer's authority surface, the generated directory is the scanner's discovery surface.

---

## 2. The scanner

### 2.1 Three intelligence levels

The scanner has three optional intelligence levels. Each level can be turned off independently for regulated deployments that refuse certain capabilities.

#### Level 1 — Structural scanner

Pure database metadata discovery: tables, columns, types, nullability, PK/FK/unique constraints, indexes, likely relationships. Deterministic and safe to run unattended in CI.

#### Level 2 — Governance profiler

Heuristic suggestions for PII candidates, scope columns, masking candidates, relationship inference. Each suggestion carries a confidence level:

- `HIGH` — matches a named-entity dictionary (`ssn`, `tax_id`, `dob`, `password`)
- `MEDIUM` — matches a pattern heuristic (`*_id` column referencing another table)
- `LOW` — general suggestion based on column comments or naming convention

Default review policy: explicit approval required at all confidence levels for sensitivity, masking, and scope flags. Deployments may relax for `HIGH` confidence non-sensitive defaults, but `HIGH` confidence sensitivity flags always require review.

#### Level 3 — LLM-assisted aliasing

Optional LLM-assisted draft alias generation. Constrained:

- The LLM never sees production data, never sees data values, never sees query traffic, never sees the compiled registry
- The LLM sees only physical schema names and proposes business-language aliases
- Output is marked `source: llm_suggested` and requires explicit developer approval

This level is structurally identical to a junior engineer suggesting aliases — the LLM is an authoring assistant, not an authority source.

### 2.2 Collision pre-check

When the scanner generates aliases that would collide under N1–N7 normalization, it flags the future collision in the draft and suggests qualifier candidates. The developer sees the collision warning during the initial review, not after a failed compile.

### 2.3 Scanner CLI

```bash
# Level 1 only — structural discovery
ojas-data scan --db postgres://app --schema public --out generated/

# Level 1 + 2 — structural + governance heuristics
ojas-data scan --db postgres://app --schema public --out generated/ --profile

# Level 1 + 2 + 3 — full intelligence
ojas-data scan --db postgres://app --schema public --out generated/ --profile --suggest-aliases

# Drift detection against existing compiled registry
ojas-data scan --db postgres://app --schema public --compare-to compiled/registry.ojas --out drift_report.json
```

### 2.4 Generated entity example

```yaml
entity: customer
physical_name: Customer
canonical: customer
review_status: DRAFT
aliases:
  - source: scanner_suggested
    alias: customer
    review_status: DRAFT
columns:
  - canonical: email
    physical_name: Email
    type: string
    aliases:
      - source: scanner_suggested
        alias: email
        review_status: DRAFT
      - source: scanner_suggested
        alias: customer email
        review_status: DRAFT
    sensitive: false
    masked: false
    exposure: allowed
  - canonical: ssn
    physical_name: SSN
    type: string
    aliases:
      - source: scanner_suggested
        alias: tax identifier
        review_status: DRAFT
    sensitive: true        # HIGH confidence Level 2 suggestion
    masked: true
    exposure: restricted
    review_required: true  # sensitive flag must be confirmed
scope_dimensions:
  tenant: TenantId
  region: RegionCode
access_class: CUSTOMER_READ  # template/default
review_status: DRAFT
```

---

## 3. The review CLI

### 3.1 Interactive review

```bash
ojas-data review generated/ --overlay registry.overrides.yaml
```

The review CLI walks each draft entry that requires approval. For each entry:

- Defaults-to-accept: physical names, canonical names, type inferences
- Prompts for review-with-default-decline: any `review_required: true` flag, any sensitive classification, any scope dimension assignment
- Asymmetric defaults: false positives on sensitivity classifications are safer than false negatives, so the review UX biases toward "confirm carefully" for sensitivity

### 3.2 Approval and the overlay file

Each approved entry produces an entry in the overlay:

```yaml
# registry.overrides.yaml
customer:
  email:
    review_status: REVIEWED_APPROVED
    reviewer: alice@pommala.com
    reviewed_at: "2026-05-21T14:00:00Z"
    aliases:
      - alias: customer email
        qualifier_type: ENTITY
        alias_origin: SCANNER_SUGGESTED
      - alias: contact email
        qualifier_type: ROLE
        alias_origin: AUTHOR_SUPPLIED
  ssn:
    review_status: REVIEWED_APPROVED
    reviewer: alice@pommala.com
    reviewed_at: "2026-05-21T14:05:00Z"
    sensitive: true       # confirmed
    masked: true
    exposure: restricted
    aliases:
      - alias: tax identifier
        qualifier_type: DOMAIN
        alias_origin: AUTHOR_SUPPLIED
        # surfaceable in user-clarification channel only, never LLM
```

### 3.3 The review_status enum

Strict enum, validated at compile:

- `DRAFT` — generated, not yet reviewed
- `REVIEWED_APPROVED` — explicitly approved, ready for compile
- `REVIEWED_REJECTED` — explicitly rejected, excluded from registry
- `REVIEWED_DEFERRED` — review postponed, treated as `DRAFT` for compile

Lowercase or alternate forms fail validation. The compiler rejects any overlay with non-conforming `review_status` values.

### 3.4 CI-friendly batch review

```bash
# Show all draft entries
ojas-data review --list-draft

# Approve specific entries
ojas-data review --approve customer.email --reviewer alice@pommala.com

# Approve based on an approvals file
ojas-data review --apply approvals.yaml
```

---

## 4. The compiler

### 4.1 Compile command

```bash
ojas-data compile \
  --generated generated/ \
  --overlay registry.overrides.yaml \
  --config ojas-data.config.yaml \
  --out compiled/
```

### 4.2 Compile output

- `compiled/registry.ojas` — immutable runtime registry
- `compiled/reverse_alias_index.json` — for Safe Business-Term Hinting
- `compiled/manifest.json` — compile metadata (versions, dependencies, reviewer trail)
- `compiled/audit/` — reviewable artifacts (alias index, policy bindings, scope mappings)

### 4.3 Compile exit codes

CLI exit codes are part of the contract:

| Exit code | Meaning |
|---|---|
| 0 | Compile succeeded |
| 10 | `DRAFT_ENTRIES_REMAIN` — registry contains unapproved drafts |
| 11 | `VALIDATION_FAILED` — manifest validation rules violated |
| 12 | `CASE_FOLD_COLLISION` — physical identifier case-fold collision |
| 13 | `ALIAS_COLLISION` — alias collision unresolved by qualifiers |
| 14 | `BINDING_DANGLING` — `dataBindingRef` resolution failure |
| 15 | `CONTRACT_REFERENCE_INVALID` — referenced contract not registered or deprecated |
| 16 | `DRIFT_DETECTED` — compilation context shows drift from database |
| 17 | `COMPILE_INTERNAL_ERROR` — unexpected error, not a developer-actionable failure |

Each exit code corresponds to machine-parseable JSON output via `--output-format json`.

### 4.4 Auto-qualify opt-in

```yaml
# ojas-data.config.yaml
compile_options:
  auto_qualify_alias_collisions: true
  qualifier_strategy: ENTITY_CANONICAL_PREFIX_V1
```

Auto-generated qualifiers are marked `alias_origin: COMPILER_GENERATED` and `review_required: true`. The developer can confirm or correct them in the next review pass.

---

## 5. Drift detection

### 5.1 Drift CLI

```bash
ojas-data drift \
  --registry compiled/registry.ojas \
  --db postgres://app \
  --output-format json
```

Exit codes: `0` for no drift, non-zero for drift detected.

### 5.2 Drift report

```json
{
  "drift_detected": true,
  "registry_version": "abc123...",
  "scanned_at": "2026-05-21T15:00:00Z",
  "items": [
    {
      "category": "NEW_FROM_INTROSPECTION",
      "entity": "customer",
      "column": "loyalty_tier",
      "severity": "MEDIUM",
      "suggestion": "Add to registry if business-relevant"
    },
    {
      "category": "REMOVED_FROM_INTROSPECTION",
      "entity": "customer",
      "column": "legacy_id",
      "severity": "HIGH",
      "suggestion": "Remove from registry or restore in DB"
    }
  ]
}
```

### 5.3 Drift workflow

When drift is detected:

1. Review the drift report
2. Decide per-item: add to registry, remove from registry, or accept as out-of-scope
3. Update the source manifest and overlay accordingly
4. Re-run scanner → review → compile
5. Verify drift is resolved with a follow-up `ojas-data drift` run

The compiler never auto-includes drift-detected items.

---

## 6. Conformance testing

### 6.1 Conformance suite

```bash
ojas-data test \
  --registry compiled/registry.ojas \
  --suite conformance
```

The conformance suite exercises the freezes from [`OJAS_DATA_QUERY_REPAIR_BOUNDARY.md`](./OJAS_DATA_QUERY_REPAIR_BOUNDARY.md):

- Safe Business-Term Hinting emits only registry-derived aliases
- Sensitive fields are suppressed from the LLM-facing channel
- Forbidden fields in prompt payloads are rejected
- DB HINT replacement produces no raw schema content
- Privileged diagnostic classifier produces identical outputs for identical inputs (CLI vs runtime)
- Scope-aware alias collisions are detected
- CUD failure paths route to safe message-generation, not extraction-repair

Exit code: `0` for pass, `18` for `CONFORMANCE_FAILED`.

### 6.2 The safe-hint CLI as falsifiability surface

```bash
ojas-data sql safe-hint \
  --registry compiled/registry.ojas \
  --entity customer_order \
  --term CustomerEmail \
  --scope tenant:acme \
  --explain
```

Without `--explain`: produces what the LLM would see.

With `--explain`: produces what the auditor sees — which gates were applied, which scope filter ran, which sensitivity check fired, which alias was selected or suppressed.

This is the reference implementation of the Safe Business-Term Hinting freeze. A security reviewer can build a test harness around this command to verify the freeze rules produce the claimed outputs.

### 6.3 Other CLI debug commands

```bash
# Strip SQL comments and show before/after
ojas-data sql strip-comments --dialect postgres --input query.sql

# Classify a raw DB error
ojas-data sql classify-error --error "ERROR: column ... does not exist"

# Inspect SQL with dialect awareness
ojas-data sql inspect --dialect postgres --input query.sql

# Validate a prompt payload without invoking the LLM
ojas-data prompts validate --schema OD_EXTRACT_REPAIR_SCHEMA --payload payload.json

# List registered prompt profiles
ojas-data prompts list

# Inspect a profile (text, version, fingerprint)
ojas-data prompts inspect --profile OD_SAFE_MESSAGE_V1

# Normalize a string through N1-N7
ojas-data normalize " Customer--Email "
# Output: customer email
```

---

## 7. Operational defaults

Deployments may configure these behaviors. The v1.0 defaults are conservative; deployments override based on risk tolerance.

### 7.1 No-progress detection

Default: same failure category counts as no progress regardless of value variation (strict interpretation).

```yaml
runtime:
  no_progress_detection: STRICT  # default
  # alternative: PERMISSIVE
```

### 7.2 Profile fingerprint mismatch

Default: fail closed in production, warn in non-production.

```yaml
runtime:
  profile_fingerprint_mismatch:
    production: FAIL_CLOSED  # default
    non_production: WARN     # default
```

### 7.3 Unregistered column patterns

Default: enabled, weekly cadence to the data steward.

```yaml
operations:
  unregistered_column_reports:
    enabled: true            # default
    cadence: weekly          # default
    recipient: data_steward
```

### 7.4 Runtime drift verification per request

Default: disabled. The compiled registry is the runtime authority.

```yaml
runtime:
  per_request_drift_check: false  # default
```

### 7.5 Partial LLM response preservation

Default: preserved in privileged audit only.

```yaml
audit:
  partial_response_preservation: PRIVILEGED_ONLY  # default
```

### 7.6 Degraded-mode behavior

Default: fail closed on all degraded states.

```yaml
runtime:
  degraded_mode:
    model_unavailable: FAIL_CLOSED
    registry_load_failure: FAIL_CLOSED
    classifier_exception: FAIL_CLOSED
    audit_unavailable: FAIL_CLOSED
    db_unavailable: GENERIC_ERROR
```

These defaults are deliberate and conservative. See [`OJAS_DATA_DEFERRED_DESIGN_TOPICS.md`](./OJAS_DATA_DEFERRED_DESIGN_TOPICS.md) for the design-level discussion of degraded-mode behavior, which is deferred for full specification.

---

## 8. CI integration

### 8.1 Pre-commit hook

```bash
#!/bin/bash
# .git/hooks/pre-commit
set -e

ojas-data validate --overlay registry.overrides.yaml --output-format json
ojas-data compile --output-format json
ojas-data test --suite conformance --output-format json
```

### 8.2 CI pipeline

```yaml
# .github/workflows/ojas-data.yml (example)
jobs:
  ojas-data-validate:
    steps:
      - run: ojas-data scan --db ${{ secrets.STAGING_DB }} --compare-to compiled/registry.ojas
      - run: ojas-data compile
      - run: ojas-data test --suite conformance
      - run: ojas-data drift --registry compiled/registry.ojas --db ${{ secrets.STAGING_DB }}
```

### 8.3 Drift check on production schedule

```bash
# Cron job — daily drift check against production DB
ojas-data drift \
  --registry /production/registry.ojas \
  --db $PRODUCTION_DB \
  --output-format json \
  --alert-on-drift
```

---

## 9. Two-tier CLI structure

The CLI mirrors the document split:

| Namespace | Owns | Examples |
|---|---|---|
| `ojas-data <verb>` | Resolver/registry tooling | `scan`, `generate`, `normalize`, `review`, `compile`, `validate`, `drift`, `test` |
| `ojas-data sql <verb>` | Query repair / SQL diagnostics | `safe-hint`, `strip-comments`, `classify-error`, `inspect`, `scan-secrets` (future) |
| `ojas-data prompts <verb>` | Prompt schema/profile tooling | `list`, `inspect`, `validate` |

A developer reading the Resolver Scope document finds every resolver-layer command in `ojas-data <verb>` form. A developer reading the Query Repair Boundary spec finds every repair-layer command in `ojas-data sql <verb>` form. The CLI namespace is the index into the documentation.

---

## 10. Open documentation items

These items are known refinements for the v1.1 documentation pass:

- Full conformance corpus structure and reference suites
- Per-dialect tokenizer configuration reference
- Deployment configuration template repository
- IDE integrations (VS Code extension, JetBrains plugin) — future
- Telemetry and observability integration patterns

---

## Appendix A — Developer guide frozen principles

1. The scanner discovers structure; the developer approves meaning; the compiler creates authority
2. Generated entities are never edited; developer changes live in the overlay file
3. The review CLI uses asymmetric defaults — sensitivity flags require explicit confirmation
4. The compile step is the boundary between authoring artifacts and runtime authority
5. CLI exit codes are stable and machine-parseable
6. The two-tier CLI structure mirrors the document split
7. The safe-hint CLI is the falsifiability surface for the LLM-facing freezes
8. Drift detection alerts but never auto-includes
9. Operational defaults are conservative; deployments override based on risk tolerance
10. CI integration is first-class — every key command supports JSON output and stable exit codes
