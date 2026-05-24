# Ojas Data Runtime Bundle — V0.3.2

| Field | Value |
|---|---|
| Bundle version | V0.3.2 |
| Status | Review-correction baseline; freeze candidate with documented exceptions |
| Date | 2026-05-23 |
| Owner | SPHUTA / Ojas |
| Schema language | JSON Schema (Draft 2020-12); CDDL deferred per parent §10 |
| Validator | `validate.py` (Python 3.10+, requires `jsonschema` and `referencing` packages) |

This bundle is the V0.3.2 deliverable for the Ojas Data Runtime layer. It contains the parent safety control model, the message catalog (source of truth), three JSON Schemas derived from the catalog, eight positive fixture scenarios, five negative fixtures, a validator, and supporting design rationale.

The bundle is **self-contained.** After unzipping, `python3 validate.py` should produce a clean validation run with exit code 0.

---

## 1. Quick start

```bash
# Unzip
unzip OJAS_BUNDLE_V0.3.2.zip
cd OJAS_BUNDLE_V0.3.2

# Install validator dependencies (one-time)
pip install jsonschema referencing

# Run validation
python3 validate.py
```

Expected output:
```
Positive: {'OK': 32, 'FAIL': 0, 'MISSING': 0, 'BAD_JSON': 0}
Negative: {'OK_FAILS_AS_EXPECTED': 5}
All fixtures clean.
```

Exit code 0.

---

## 2. Contents

```
OJAS_BUNDLE_V0.3.2/
├── README.md                                              ← this file
├── OJAS_AGENT_SAFETY_CONTROL_MODEL.md                     ← parent safety model
├── OJAS_DATA_RUNTIME_BUNDLE_MESSAGE_CATALOG_V0.3.2.md     ← catalog (source of truth)
├── OJAS_DATA_RUNTIME_BUNDLE_FOCUSED_REVIEW.md             ← design rationale
├── SCHEMA_CORRECTION_REPORT.md                            ← design rationale
├── OJAS_DATA_RUNTIME_BUNDLE_SCHEMA_V0.3.2.json            ← schema (source of truth)
├── OJAS_RUNTIME_DATA_SCHEMA_V0.3.2.json                   ← schema (source of truth)
├── OJAS_EVIDENCE_STORE_SCHEMA_V0.3.2.json                 ← schema (source of truth)
├── validate.py                                            ← conformance validator
├── VALIDATION_REPORT.md                                   ← conformance evidence
└── fixtures/
    ├── 01_valid_read/                                     ← positive scenarios
    ├── 02_blocked_sensitive_field/
    ├── 03_cud_preflight_failure/
    ├── 04_destructive_delete_preexec_required/
    ├── 05_bulk_insert_signal/
    ├── 06_create_after_destroy_signal/
    ├── 07_policy_timeout_deny/
    ├── 08_raw_sql_rejected_policy_built/
    └── _negative/                                         ← negative fixtures
        ├── audit_payload_without_evidence_envelope/
        ├── input_with_both_extracted_intent_and_input/
        ├── input_with_neither_extracted_intent_nor_input/
        ├── request_with_sql_field/
        └── wrong_emitter_for_record_type/
```

---

## 3. Maturity labels

Every artifact in this bundle falls into one of five categories. Knowing which category applies to which artifact is essential for using the bundle correctly.

### 3.1 Source of truth

Authoritative contract artifacts. These define what is true. Schemas are derived from the catalog; if catalog and schema disagree, catalog wins.

| Artifact | Notes |
|---|---|
| `OJAS_DATA_RUNTIME_BUNDLE_MESSAGE_CATALOG_V0.3.2.md` | Language-neutral catalog covering all V1 bundle messages. Latest revision of catalog lineage (V0.3 → V0.3.1 → V0.3.2). |
| `OJAS_DATA_RUNTIME_BUNDLE_SCHEMA_V0.3.2.json` | Bundle schema (data-execute path, credential-boundary records, primitives). |
| `OJAS_RUNTIME_DATA_SCHEMA_V0.3.2.json` | Runtime-data schema (wire-protocol messages + envelope-wrapped payload definitions). |
| `OJAS_EVIDENCE_STORE_SCHEMA_V0.3.2.json` | Evidence-store schema (`evidence-record` envelope with discriminated payload). |

### 3.2 Freeze candidate

Stable design, freeze pending explicit deferred decisions.

| Artifact | Notes |
|---|---|
| `OJAS_AGENT_SAFETY_CONTROL_MODEL.md` | Parent safety model. D-1, D-2, D-3, D-5, D-6, D-8, D-9 resolved. D-4 (reconciliation truth source per integration), D-7 (tool-provenance verification), D-10 (per-product Ojas integration model) remain deferred per parent §9.2. |

### 3.3 Conformance evidence

Tests and reports demonstrating that the source-of-truth artifacts are mutually consistent. Recreatable from the contracts; not themselves contracts.

| Artifact | Notes |
|---|---|
| `fixtures/` | 8 positive scenarios, 5 negative fixtures. All pass against current schemas. |
| `validate.py` | Cross-file `$ref` registry validator; positive + expected-failure validation. |
| `VALIDATION_REPORT.md` | Detailed conformance report; lists coverage and gaps. |

### 3.4 Design rationale

Why-documents. Travel with the deliverable for audit trail; not contract material; superseded artifacts.

| Artifact | Notes |
|---|---|
| `OJAS_DATA_RUNTIME_BUNDLE_FOCUSED_REVIEW.md` | Focused review of the V0.3 catalog and schemas (S1–S14 findings). Drove V0.3.1 and V0.3.2 corrections. |
| `SCHEMA_CORRECTION_REPORT.md` | Maps each focused review finding (S1–S14) plus each catalog correction to the resulting schema change. |

### 3.5 Not freeze-ready (explicit gaps)

Specific elements deliberately left unsealed because the underlying design work is incomplete. Calling these out so they are not mistaken for accidental gaps.

| Element | Reason | Where addressed |
|---|---|---|
| §2.13 input stubs | Per-operation input shapes (`read-input`, `insert-input`, etc.) are catalog stubs only. Full field shapes deferred to a future catalog revision. Schema currently does NOT close `additionalProperties` on these types — closing must precede schema freeze. | Catalog §2.13 freeze-safety warning |
| Catalog-silent sub-structures (`resolved-field`, `resolved-scope-dimension`, `resolved-filter`, `scope-predicate`, `masked-field`, `blocked-field`, `data-execute-response.data`) | Catalog references these but does not define their internal shapes. Schemas use `type: object` with `SCHEMA-REVIEW` notes per the flag-don't-invent rule. | Schema correction report §7; fixtures use empty-object `{}` placeholders |
| Mutation preflight check presence rules | Catalog §2.8 says `scope-verification` and `tenant-isolation` MUST be in checks. Currently enforced at runtime, not in schema. Could be schema-encoded with `contains` constraints. | Validation report §6 finding 1 |

---

## 4. Document map

### Where to find what

| Question | Where to look |
|---|---|
| What are the safety invariants? | Parent §3, §5 (invariant I-1 through I-10) |
| What capabilities does Ojas v1 provide? | Parent §4 (Layer Ownership), §4.5 (V1 packaging) |
| Which messages exist? | Catalog §2 (data-execute path), §3 (runtime-data), §4 (credential-boundary), §5 (evidence-core), §6 (signals), §7 (reconciliation), §8 (gate paths) |
| Why does the schema have feature X? | Schema correction report §3 (S1–S14 mapping), §4 (V0.3.1 corrections), §5 (V0.3.2 open-item resolutions) |
| What's the lineage of catalog corrections? | Catalog §10.1 (V0.3 deltas), §10.2 (V0.3.1 corrections), §10.4 (V0.3.2 open-item resolutions) |
| What are the cross-cutting consistency rules? | Catalog §9 |
| Which decisions remain deferred? | Parent §9.2 (D-4, D-7, D-10) |
| Where are the known gaps that block freeze? | This README §3.5; VALIDATION_REPORT.md §6 |

### Reading order (recommended for first-time readers)

1. **Parent safety model** (`OJAS_AGENT_SAFETY_CONTROL_MODEL.md`) — establishes the architecture, layer ownership, and invariants
2. **Catalog** (`OJAS_DATA_RUNTIME_BUNDLE_MESSAGE_CATALOG_V0.3.2.md`) — read §1 (primitives), §2 (data-execute path), then skim §3–§8 as needed
3. **One schema** (`OJAS_DATA_RUNTIME_BUNDLE_SCHEMA_V0.3.2.json`) — shows how the catalog turns into machine-checkable contracts
4. **One fixture scenario** (`fixtures/01_valid_read/`) — concrete instance plus README explaining what it demonstrates
5. **Validation report** — what the bundle proves and what it explicitly does not
6. **Focused review** (optional, design rationale) — why the catalog and schemas look the way they do

---

## 5. Status summary

### Resolved in V0.3.2

- All five v0.3.1 review-correction deltas (D-F1 through D-F4 + the §3.6 emitter correction)
- All five v0.3.2 open-item resolutions (O-1 through O-5)
- All 14 focused review findings (S1–S14): 8 fully resolved, 6 flagged-don't-invent where catalog is silent
- Cross-file `$ref` registry working; schemas mutually consistent
- 8 positive scenarios + 5 negative fixtures all green

### Deferred (deliberate, documented)

- D-4 (reconciliation truth source per integration) — per-integration concern
- D-7 (tool-provenance verification) — for standalone Ojas Runtime, not data bundle
- D-10 (per-product Ojas integration model) — per-product concern
- §2.13 full per-operation input shapes — future catalog revision
- Catalog v0.4 work on the 7 catalog-silent sub-structures listed in §3.5 above
- CDDL — reconsidered only if v2 introduces content-addressed evidence chains

### Not in this bundle (explicit out-of-scope)

- Supporting documentation regenerations (other phase docs in earlier work were not refreshed for V0.3.2 — they retain their previous baselines until a separate refresh turn)
- Superseded catalog files (V0.3, V0.3.1) — their content is captured in V0.3.2 §10 lineage
- Implementation code, integration adapters, deployment configuration

---

## 6. Validation reproduction

```bash
$ cd OJAS_BUNDLE_V0.3.2
$ python3 validate.py
================================================================
Ojas Fixture Validator v0.3.2
================================================================
Loaded 3 schemas with cross-file $ref registry

Fixtures: <path>/fixtures

----------------------------------------------------------------
POSITIVE FIXTURES (must pass)
----------------------------------------------------------------
[ ... 32 OK lines ...]

----------------------------------------------------------------
NEGATIVE FIXTURES (must fail with expected errors)
----------------------------------------------------------------
[ ... 5 PASS lines ...]

================================================================
Positive: {'OK': 32, 'FAIL': 0, 'MISSING': 0, 'BAD_JSON': 0}
Negative: {'OK_FAILS_AS_EXPECTED': 5}
================================================================
All fixtures clean.
```

Exit code 0.

If validation does not produce these results, the bundle has been modified or its dependencies are incomplete.

---

## 7. Next steps (beyond this bundle)

The work order anticipated and executed across multiple disciplined turns. After V0.3.2 acceptance, candidate next steps:

1. **Parent freeze** — resolve D-4, D-7, D-10 (likely per-integration / per-product work) before declaring parent frozen
2. **Catalog v0.3.3 or v0.4** — define the eight catalog-silent sub-structures from §3.5 of this README; close §2.13 input stubs with full per-operation shapes; possibly extend §2.8 preflight rules to be schema-enforceable
3. **Schema v0.3.3 / v0.4** — track catalog as it evolves
4. **Supporting docs refresh** — phase docs and supporting Markdown that were not regenerated for V0.3.2
5. **Implementation integration** — actual Ojas Data v1 implementation against this contract

None of these are blockers for **using** V0.3.2 as a design baseline; they are paths toward eventual freeze.

---

## 8. Bundle integrity

| File | Approximate size |
|---|---|
| `OJAS_AGENT_SAFETY_CONTROL_MODEL.md` | ~34 KB |
| `OJAS_DATA_RUNTIME_BUNDLE_MESSAGE_CATALOG_V0.3.2.md` | ~75 KB |
| `OJAS_DATA_RUNTIME_BUNDLE_FOCUSED_REVIEW.md` | ~36 KB |
| `SCHEMA_CORRECTION_REPORT.md` | ~16 KB |
| `OJAS_DATA_RUNTIME_BUNDLE_SCHEMA_V0.3.2.json` | ~30 KB |
| `OJAS_RUNTIME_DATA_SCHEMA_V0.3.2.json` | ~20 KB |
| `OJAS_EVIDENCE_STORE_SCHEMA_V0.3.2.json` | ~20 KB |
| `validate.py` | ~12 KB |
| `VALIDATION_REPORT.md` | ~10 KB |
| `fixtures/` (37 JSON files + 10 README files) | ~50 KB |

---

## Closing

This bundle represents the V0.3.2 review-correction baseline of the Ojas Data Runtime contracts. It is internally consistent, validator-tested, and self-contained.

It is **not** a freeze. Three parent decisions are deferred. The catalog explicitly marks §2.13 as not freeze-ready. Seven catalog-silent sub-structures remain placeholder-only.

Use the bundle as a design baseline. Implementation against V0.3.2 is reasonable provided the not-freeze-ready elements above are understood and accepted.
