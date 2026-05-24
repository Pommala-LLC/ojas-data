# Ojas Schema Correction Report — v0.3 → v0.3.2

| Field | Value |
|---|---|
| Status | Schema correction pass — review-ready |
| Freeze status | Not frozen |
| Date | 2026-05-23 |
| Source catalog | `OJAS_DATA_RUNTIME_BUNDLE_MESSAGE_CATALOG_V0.3.2.md` |
| Source review | `OJAS_DATA_RUNTIME_BUNDLE_FOCUSED_REVIEW.md` |
| Input schemas | `ojas-data-runtime-bundle.schema.v0.3.json`, `ojas-runtime-data.schema.v0.1.json`, `ojas-evidence-store.schema.v0.1.json` |
| Output schemas | `OJAS_DATA_RUNTIME_BUNDLE_SCHEMA_V0.3.2.json`, `OJAS_RUNTIME_DATA_SCHEMA_V0.3.2.json`, `OJAS_EVIDENCE_STORE_SCHEMA_V0.3.2.json` |
| Default rule applied | Catalog v0.3.2 wins. If catalog is silent, schema does not invent. If schema cannot enforce, runtime enforcement is documented. |
| Plan decisions | Strict envelope wrapping; cross-file `$ref` with stable `$id`; oneOf XOR; Tier D digest in schema, A/B/C in runtime; partition-key as bounded string; flag-don't-invent for S9/S10/S11 |

---

## 1. Method

Each correction below is mapped to:

- **Source** — the catalog section, review finding (S1–S14), or v0.3.2 open-item resolution that drove the change
- **Action** — applied / flag-only / out-of-scope
- **Location** — which schema and which `$defs` entry holds the change
- **Status** — what the schema now enforces and what remains for runtime

Schemas use cross-file `$ref` with stable `$id` URIs. The bundle schema is the canonical home for primitives; runtime-data and evidence-store reference primitives via cross-schema `$ref`.

## 2. Schema $id mapping

| Schema file | `$id` |
|---|---|
| `OJAS_DATA_RUNTIME_BUNDLE_SCHEMA_V0.3.2.json` | `https://schemas.ojas.dev/ojas/data-runtime-bundle/v0.3.2/schema.json` |
| `OJAS_RUNTIME_DATA_SCHEMA_V0.3.2.json` | `https://schemas.ojas.dev/ojas/runtime-data/v0.3.2/schema.json` |
| `OJAS_EVIDENCE_STORE_SCHEMA_V0.3.2.json` | `https://schemas.ojas.dev/ojas/evidence-store/v0.3.2/schema.json` |

All three `$id` values are stable. They MUST NOT be changed without a coordinated version bump.

## 3. Focused review S1–S14 corrections

| # | Issue | Action | Location | Status |
|---|---|---|---|---|
| **S1** | `audit-id` typed inconsistently across schemas | **Applied** | Bundle `$defs.audit-id`: new regex `^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$`. Runtime-data and evidence-store reference via cross-schema `$ref`. | Resolved. All four audit-id locations (field-level-audit, reconciliation-hook, pre-execution-audit-binding, evidence-record envelope) now use canonical `audit-id` type. |
| **S2** | `mutation-preflight-result` missing top-level schema | **Applied per D-F2** | Bundle `$defs.mutation-preflight-result`. NOT in oneOf — reusable type only. | Resolved. Referenced from `data-execute-response.preflight` (structural) and `mutation-preflight-orchestration-record.preflight-result-digest` (by digest). |
| **S3** | `data-operation-audit` missing top-level schema | **Applied per D-F3** | Runtime-data `$defs.data-operation-audit`. NOT in oneOf — payload only. | Resolved. Appears as `evidence-record.payload` when `record-type=data-operation-audit`. |
| **S4** | `data-execute-request.input` unconstrained | **Applied per D-C1** | Bundle `$defs.discriminated-input` (oneOf over six input types in `$defs.read-input`...`$defs.aggregate-input`). | Resolved structurally. Per-operation field shapes are **catalog-silent stubs** per §2.13; full shapes deferred to a future revision. Schema does not yet close `additionalProperties` on the stubs (per catalog §2.13 freeze-safety warning). |
| **S5** | Digest optionality vague | **Applied per D-F4** | Bundle `data-execute-request.allOf` with `if/then` for Tier D: `actor-kind=agent` AND `operation` in (insert/update/delete/export) → both digests required. | Resolved for Tier D (schema-enforced). Tiers A/B/C documented as runtime-only. |
| **S6** | `pre-execution-audit-ref` optional in schema; required when policy mandated audit | **Documented as runtime-enforced** | Bundle `data-execute-request.properties.pre-execution-audit-ref`: optional at schema level. Description notes runtime enforces per D-1/PB-002. | Schema correct as-is (cannot know policy mandate at request validation). Runtime enforces. |
| **S7** | `data-execute-response.audit` unconstrained | **Applied per D-F3** | Bundle `data-execute-response.properties.audit`: cross-schema `$ref` to evidence-store `evidence-record`. | Resolved. Envelope-wrapped audit on the response. |
| **S8** | `data-execute-response.preflight` unconstrained | **Applied per D-F2** | Bundle `data-execute-response.properties.preflight`: `$ref` to `$defs.mutation-preflight-result`. | Resolved. |
| **S9** | `data-execute-response.resolved-intent` unconstrained | **Partially applied** | Bundle `$defs.resolved-intent` defined with fields from catalog §2.3. Internal sub-structures (`resolved-field`, `resolved-scope-dimension`, `resolved-filter`) are **catalog-silent**: schema uses `type: object` with `SCHEMA-REVIEW: flag-don't-invent` notes. | Top-level structure resolved. Sub-structures flagged; catalog v0.3.3 or v0.4 should define them. |
| **S10** | `data-policy-decision.scope-predicates` items unconstrained | **Partially applied** | Bundle `$defs.data-policy-decision.properties.scope-predicates.items`: `type: object` with `SCHEMA-REVIEW: flag-don't-invent` note. | Catalog references `scope-predicate` but does not define its shape. Flagged; per catalog §2.4 it is "structurally injected, never LLM-supplied" — internal schema only. |
| **S11** | `data-policy-decision.masked-fields/blocked-fields` items unconstrained | **Partially applied** | Bundle `$defs.data-policy-decision.properties.masked-fields.items` and `.blocked-fields.items`: `type: object` with `SCHEMA-REVIEW: flag-don't-invent` notes. | Catalog references `masked-field` and `blocked-field` but does not define their shapes. Flagged. |
| **S12** | `data-execute-response.credential-selection` unconstrained | **Applied** | Bundle `$defs.credential-selection` defined per catalog §4.2. `data-execute-response.properties.credential-selection`: `$ref` to it. | Resolved. |
| **S13** | `record-type-code` not in bundle schema | **Applied** | Bundle `$defs.record-type-code` added (canonical enum). Evidence-store cross-references via `$ref`. | Resolved. |
| **S14** | `deny-by-no-progress` in schema but missing from catalog | **N/A** | Catalog v0.3.2 §1.8 has `deny-by-no-progress`. Already aligned in v0.3. | No-op. |

## 4. Catalog v0.3.1 corrections — schema impact

| Catalog v0.3.1 delta | Action | Location | Status |
|---|---|---|---|
| D-F1 audit-id opaque type | **Applied** | See S1 above. | Resolved across all three schemas. |
| D-F2 mutation-preflight-result as reusable $defs (not top-level) | **Applied** | See S2 above. | Resolved. |
| D-F3 strict envelope wrapping | **Applied** | Runtime-data: 8 audit records removed from top-level oneOf, kept as `$defs`. Evidence-store: `evidence-record` is the canonical wire shape with discriminated payload. | Resolved. Runtime-data top-level oneOf now contains ONLY `pre-execution-gate-event`, `pre-execution-gate-response`, `policy-response-timeout` (wire-protocol messages, not stored audit records). |
| D-F4 tiered digest requirement | **Applied per plan decision 4** | Bundle `data-execute-request.allOf` enforces Tier D. Description documents Tier A/B/C as runtime-only. | Resolved at schema layer. Tier A/B/C in runtime. |
| D-C1 discriminated input types stubbed | **Applied** | See S4 above. | Stubbed (catalog-honored, freeze-blocking marker preserved). |
| §3.6 emitter correction (`ojas-data` → `ojas-runtime-data`) | **Applied** | Runtime-data `$defs.field-level-audit-record.properties.emitter`: `const: ojas-runtime-data`. | Resolved. |

## 5. Catalog v0.3.2 open-item resolutions — schema impact

| Open item | Resolution | Location | Status |
|---|---|---|---|
| **O-1** `credential-handle-request` adds `entity` and `operation` as required | **Applied** | Bundle `$defs.credential-handle-request.required` includes both. | Resolved. Referenced as evidence-record payload when `record-type=credential-handle-request`. |
| **O-2** `terminal` boolean retained | **Applied** | Runtime-data `$defs.no-progress-halt-record.properties.terminal` (required boolean). Description records O-2 resolution. | Resolved. |
| **O-3** `scope-match` confidence class retained | **Applied** | Evidence-store `$defs.pattern-confidence-class-code` enum keeps all three values. | Resolved. |
| **O-4** Three permitted partition strategies; deployment selects | **Applied per plan decision 5** | Evidence-store `$defs.stream-record.properties.partition-key`: bounded string with description documenting three strategies (`tenant-id` default, `tenant+entity`, `tenant+entity+actor`). Schema does not enforce strategy choice. | Resolved. Runtime config validates strategy selection. |
| **O-5** `compared-records-digest` and `gap-records-digest` added as optional | **Applied** | Evidence-store `$defs.reconciliation-batch-summary.properties`: both added as optional with descriptions. | Resolved. |

## 6. Cross-schema $ref dependencies

Cross-file references introduced in this correction pass:

| Source | Target | Purpose |
|---|---|---|
| Runtime-data `$defs.*` (most primitives) | Bundle schema primitives | Single canonical primitive definitions |
| Evidence-store `$defs.*` (most primitives) | Bundle schema primitives | Same as above |
| Bundle `data-execute-response.properties.audit` | Evidence-store `evidence-record` | Envelope-wrapped audit on responses (S7) |
| Bundle `sql-review-response.properties.audit` | Evidence-store `evidence-record` | Same as above |
| Evidence-store `evidence-record.payload` (via discriminated conditionals) | Bundle `credential-handle-request`, `credential-selection`, `credential-revoke-notification` | Credential-boundary records as payloads |
| Evidence-store `evidence-record.payload` (via discriminated conditionals) | Runtime-data audit records (8 record types) | Runtime-emitted records as payloads |

**Validator integration requirement:** the validator MUST load all three schemas as a referencing registry. Loading any single schema without the other two yields unresolvable `$ref`s. The `validate.py` update implements this.

## 7. SCHEMA-REVIEW flagged locations (catalog-silent, not invented)

These are sub-structures that the catalog references but does not define. Schema uses `type: object` with explicit SCHEMA-REVIEW notes:

| Location | Catalog reference | Recommendation |
|---|---|---|
| Bundle `resolved-intent.properties.fields.items` | §2.3 mentions `resolved-field` | Catalog v0.4 should define `resolved-field` (likely: logical name, physical name, sensitivity-code, masking-code) |
| Bundle `resolved-intent.properties.scope.additionalProperties` | §2.3 mentions `resolved-scope-dimension` | Catalog v0.4 should define `resolved-scope-dimension` |
| Bundle `resolved-intent.properties.filters.items` | §2.3 mentions `resolved-filter` | Catalog v0.4 should define `resolved-filter` |
| Bundle `data-policy-decision.properties.scope-predicates.items` | §2.4 mentions `scope-predicate` | Catalog v0.4 should define |
| Bundle `data-policy-decision.properties.masked-fields.items` | §2.4 mentions `masked-field` | Catalog v0.4 should define |
| Bundle `data-policy-decision.properties.blocked-fields.items` | §2.4 mentions `blocked-field` | Catalog v0.4 should define |
| Bundle `data-execute-response.properties.data` | §2.11 says "structured result shape" but per-operation shape not catalog-specified | Catalog v0.4 may define per-operation result shapes |
| Bundle `input-base` and six input stubs | §2.13 stubs only; full shapes deferred per freeze-safety warning | Per §2.13 — must be defined before schema freeze |

These flagged locations are **catalog gaps**, not schema bugs. Schema cannot enforce structure where catalog is silent (default rule: do not invent).

## 8. Self-validation results

Inline tests run during generation (each ran against built schemas with cross-file registry):

| Test | What it validates | Result |
|---|---|---|
| 1 | Valid `evidence-record` wrapping `data-operation-audit` | PASS |
| 2 | Wrong emitter for record-type (data-operation-audit + ojas-runtime-data) | PASS — rejected |
| 3 | XOR violation: both `extracted-intent` and `input` present | PASS — rejected |
| 4 | XOR violation: neither field present | PASS — rejected |
| 5 | Valid LLM-path `data-execute-request` | PASS |
| 6 | Tier D digest requirement: agent + mutate operation, digests missing | PASS — rejected (both digest fields flagged) |
| 7 | Same as 6 but with both digests present | PASS — accepted |
| 8 | `audit-id` with mixed-case ULID-style format | PASS — accepted |
| 8b | `audit-id` with whitespace | PASS — rejected |

All cross-file `$ref` resolutions worked; meta-schema validation passed for all three schemas.

## 9. What this turn did NOT do

Per scope:

- **No fixture changes.** Fixtures will be revalidated and updated in the next turn (including the eight negative fixtures called out in the catalog/review).
- **No parent edits.** Parent was already updated in the prior turn to point at catalog v0.3.2.
- **No supporting doc regeneration.** Out of scope per work order.
- **No CDDL work.** Deferred per parent §10.
- **No catalog edits.** Schema follows catalog; catalog is the source of truth.

## 10. Version-bump rationale

The new schemas are versioned `V0.3.2` (matching catalog) because:

- **They are not backward-compatible.** Removing top-level audit records from runtime-data's oneOf is a breaking change. Adding required fields to `credential-handle-request` is a breaking change. Adding `additionalProperties: false` to message types where it was previously absent is a breaking change.
- **The catalog version is the contract version.** Per parent §10, the catalog is the source of truth; schemas are derived. Schema version matches catalog version to preserve the lineage.
- **Old fixtures will need updating.** Fixtures bound to the v0.1/v0.3 schemas will not validate against V0.3.2 without re-wrapping audit records in `evidence-record` envelopes. This is the next-turn work.

## 11. Recommended next steps

In order:

1. **Fixture corrections.** Update all 8 positive fixtures to:
   - Use new audit-id format
   - Wrap audit payloads inside `evidence-record` envelope
   - Use discriminated input types where applicable
2. **Add 8 negative fixtures.** Per catalog/review:
   - `request_with_sql_field`
   - `audit_payload_without_evidence_envelope`
   - `wrong_emitter_for_record_type`
   - `preflight_missing_scope_verification`
   - `preflight_missing_tenant_isolation`
   - `input_with_both_extracted_intent_and_input`
   - `input_with_neither_extracted_intent_nor_input`
   - `unsafe_open_input_extra_fields` (parked — catalog §2.13 currently allows extra fields)
3. **Update validator** (`validate.py`) to load all three schemas as registry and resolve cross-file `$ref`. Add negative fixture validation (expecting controlled failures with specific error messages).
4. **Run validation, produce VALIDATION_REPORT.md.**
5. **Package corrected bundle.**

Each of these is a separate turn per the work order discipline.

---

## Closing

This correction pass resolves all 14 focused-review items (8 fully, 6 by flagged-don't-invent where catalog is silent), all 5 v0.3.1 corrections, all 5 v0.3.2 open-item resolutions, and the mandatory `field-level-audit` emitter fix. Self-validation confirmed that the strict envelope-wrapping, cross-file `$ref`, XOR rule, Tier D digest enforcement, and emitter-record-type discrimination all function correctly.

Catalog v0.3.2 remains the source of truth. The schemas now reflect it with the documented `flag-don't-invent` exceptions where catalog is silent. Those exceptions are catalog work, not schema work.
