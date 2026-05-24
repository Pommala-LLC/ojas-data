# Ojas Fixture Validation Report — V0.3.2

| Field | Value |
|---|---|
| Status | Fixture corrections complete; all schemas + fixtures green |
| Date | 2026-05-23 |
| Schemas | `OJAS_DATA_RUNTIME_BUNDLE_SCHEMA_V0.3.2.json`, `OJAS_RUNTIME_DATA_SCHEMA_V0.3.2.json`, `OJAS_EVIDENCE_STORE_SCHEMA_V0.3.2.json` |
| Source catalog | `OJAS_DATA_RUNTIME_BUNDLE_MESSAGE_CATALOG_V0.3.2.md` |
| Validator | `validate.py` v0.3.2 (cross-file `$ref` registry; positive + expected-failure validation) |
| Positive fixtures | 8 scenarios, 32 files, **all OK** |
| Negative fixtures | 5 fixtures, **all fail with expected errors** |
| Parked fixtures | 3 (documented below) |
| Validator exit code | 0 (clean) |

---

## 1. Summary

```
Positive: {'OK': 32, 'FAIL': 0, 'MISSING': 0, 'BAD_JSON': 0}
Negative: {'OK_FAILS_AS_EXPECTED': 5}
```

The fixtures pass cleanly against the V0.3.2 schemas. The schema correction pass and the fixture correction pass are now mutually consistent.

## 2. Positive fixtures — 8 scenarios

Each scenario regenerated from scratch using catalog V0.3.2 as source of truth (per fixture-turn decision: regenerate rather than edit in place, because 26/31 of the old fixtures were stale relative to V0.3.2 schemas).

| Scenario | Files | What it demonstrates |
|---|---|---|
| `01_valid_read` | request, response, audit | Baseline LLM-path read by human actor; envelope-wrapped audit; no Tier D digest required (actor not agent) |
| `02_blocked_sensitive_field` | request, response, audit, sanitized_feedback | Field masking by policy; `blocked-fields` array uses empty-object placeholder per catalog-silent rule |
| `03_cud_preflight_failure` | request, response, audit, preflight_orchestration | Agent update path; Tier D digests present; preflight result embedded in response per D-F2; orchestration record envelope-wrapped |
| `04_destructive_delete_preexec_required` | request, response, audit, gate_event, gate_response, pre_execution_audit_binding | Destructive action triggering pre-execution gate (D-1 sync path); binding record envelope-wrapped; `pre-execution-audit-ref` populated |
| `05_bulk_insert_signal` | request, response, audit, bulk_context_observed | Agent bulk insert past D-5 threshold; signal as standalone payload |
| `06_create_after_destroy_signal` | destroy_audit, create_audit, create_after_destroy_observed | D-6 pattern: two envelope-wrapped audits + observation signal with `exact-match` confidence class |
| `07_policy_timeout_deny` | gate_event, gate_response_timeout, response, audit | Policy authority timeout at 500ms ceiling per D-1; `deny-by-timeout` distinct from `deny-by-policy` per D-2; `policy-response-timeout-recorded: true` per §5.2 rule |
| `08_raw_sql_rejected_policy_built` | request, response, audit, sanitized_feedback | `sql-review-request` path with operator actor; denied because raw SQL not permitted in Policy-Built Mode; this is the resolved Finding 5 from focused review |

**Key fixture patterns established (V0.3.2 baseline):**

- **Audit-id format:** Opaque ULID-style (e.g., `01HG3K9XQ8WR2VBN6QT5MZX1Y4`) per v0.3.1 D-F1
- **Audit envelope wrapping:** Every audit record uses `evidence-record` envelope with discriminated payload per v0.3.1 D-F3
- **Tier D digest enforcement:** All agent + mutate/export requests carry both `policy-state-digest` and `instruction-context-digest` per v0.3.1 D-F4
- **Discriminated input vs extracted-intent:** All requests use exactly one path; LLM path uses `extracted-intent`, operator path uses `sql-review-request` (scenario 08)
- **Catalog-silent placeholders:** `scope-predicates`, `masked-fields`, `blocked-fields`, `resolved-intent.fields/scope/filters` use empty-object `{}` placeholders. Full structures deferred to future catalog revision per flag-don't-invent rule.

## 3. Negative fixtures — 5 included, 3 parked

### Included (all pass — fail with expected errors)

| Fixture | Target | What schema correctly rejects |
|---|---|---|
| `request_with_sql_field` | `bundle/data-execute-request` | `sql` field on data-execute-request (forbidden by `additionalProperties: false`). Locks invariant I-6 (LLM authors intent, not executables) and the resolved Finding 5. Expected substring: `'sql' was unexpected`. |
| `audit_payload_without_evidence_envelope` | `evidence-store/evidence-record` | Bare audit payload missing the envelope's required fields (`record-type`, `record-digest`, `tenant-id`, etc.). Locks v0.3.1 D-F3 strict envelope wrapping. |
| `wrong_emitter_for_record_type` | `evidence-store/evidence-record` | `record-type=field-level-audit` with `emitter=ojas-data` — discriminator requires `ojas-runtime-data`. Locks catalog §5.3/§9.3 emitter discipline and the v0.3.1 §3.6 emitter correction. |
| `input_with_both_extracted_intent_and_input` | `bundle/data-execute-request` | Both `extracted-intent` AND `input` present — XOR rule rejects via oneOf. Locks v0.3.1 D-C1 path exclusivity. |
| `input_with_neither_extracted_intent_nor_input` | `bundle/data-execute-request` | Neither field present — same XOR oneOf rejection. Locks v0.3.1 D-C1 requirement that one path must be chosen. |

### Parked

The following were considered but not added in V0.3.2:

| Parked fixture | Reason |
|---|---|
| `unsafe_open_input_extra_fields` | Schema deliberately does NOT close `additionalProperties` on §2.13 input stubs per catalog freeze-safety allowance. This negative test would currently PASS (schema accepts extra fields), which would be misleading. Will become valid once full per-operation input shapes are defined and `additionalProperties: false` is added. |
| `preflight_missing_scope_verification` | Catalog §2.8 profile rule "scope-verification MUST be present in checks" is **runtime-enforced**, not schema-enforced. Bundle schema's `mutation-preflight-result` description explicitly notes this gap. JSON Schema CAN encode it via `contains` constraint, but that would be a schema change beyond the v0.3.2 correction scope. Adding this negative fixture would require either (a) extending the schema or (b) testing against a non-existent rule. Parked pending schema scope decision. |
| `preflight_missing_tenant_isolation` | Same reason as above. Both checks are part of the catalog's profile rule; both are runtime-only in v0.3.2 schemas. |

**Recommendation for future:** when the schema is next opened for changes, consider adding `contains` constraints to `mutation-preflight-result.checks` so both `scope-verification` and `tenant-isolation` are statically required. At that point the two parked preflight fixtures become valid and should be added.

## 4. Validator architecture

**`validate.py` highlights:**

- Loads all three V0.3.2 schemas into a `referencing.Registry` so cross-file `$ref` URIs resolve (bundle → evidence-store → runtime-data via stable `$id` URIs).
- Each positive fixture file is validated against **one specific `$defs` entry**, not against a schema's top-level oneOf (the "split fixture" approach from the focused review).
- Each negative fixture is structured as a folder with three files:
  - `instance.json` — the malformed instance to validate
  - `target.txt` — `schema-label/defs-name` (e.g., `bundle/data-execute-request`)
  - `expected_error.txt` — error substrings the schema MUST produce (one per line, `#` comments ignored)
- Validator reports `OK_FAILS_AS_EXPECTED` only if the schema rejected the negative instance AND every expected error substring appeared in the produced errors.
- Exit code 0 when all positive fixtures pass AND all negative fixtures fail with expected errors. Non-zero otherwise.

## 5. What this turn did NOT do

Per scope:

- **No schema changes.** Schemas from the schema-correction turn are used as-is.
- **No catalog changes.** Catalog V0.3.2 remains source of truth.
- **No parent edits.** Parent already updated to V0.3.2 in earlier turn.
- **No supporting doc regeneration.** Out of scope per work order.
- **No CDDL work.**
- **No bundle packaging.** Packaging is the next turn (separate turn per scope decision Q0).

## 6. Findings surfaced by this fixture turn

Items that emerged during fixture work and are worth flagging (not blocking):

1. **`mutation-preflight-result.checks` schema gap.** The catalog §2.8 profile rule requires `scope-verification` and `tenant-isolation` checks. Currently runtime-only. Could be schema-enforced with `contains` constraints. Parked from this turn but identified.

2. **Catalog §3.5 `no-progress-halt-record`** has no fixture coverage. Scenario set inherited from earlier work didn't include a no-progress halt scenario. Not blocking — but if a future fixture pass adds coverage, this is the gap.

3. **Catalog §4.x credential-handle records** also have no positive fixture coverage. Same observation as above — the catalog defines them, the schema models them, but no scenario exercises them yet.

No findings rise to "freeze blocker" or "schema bug." All three are coverage gaps that could be addressed in a future fixture-extension turn.

## 7. Acceptance signal

This report constitutes the V0.3.2 fixture-and-schema conformance evidence. The next turn (bundle packaging, per work order) can proceed.

Schemas + fixtures + validator are mutually consistent and pass cleanly.
