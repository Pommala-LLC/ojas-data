# Ojas Data Runtime Bundle — Focused Review Report

| Field | Value |
|---|---|
| Status | Focused review report / decision-input draft |
| Freeze status | Not frozen |
| Date | 2026-05-23 |
| Author | Claude (the same author as the artifacts under review) |
| Scope | Four core artifacts only |
| Implementation | None in this turn |

---

## 0. About this report

### 0.1 Conflict-of-interest disclosure

I generated the artifacts under review. The disclosure I made before starting the review applies throughout: this report is biased toward defending choices I made. I have tried to compensate by being deliberately harder on the artifacts than I would be reviewing someone else's work, and by treating every divergence between catalog and schema as a defect rather than a "near miss." If any section reads as defensive rather than critical, that's the bias bleeding through; flag it and I will re-do that section.

### 0.2 Decision protocol for parked findings

Per your instruction:

- Findings 1–4 (audit-id, preflight-result top-level, data-operation-audit top-level, digest optionality): **Option X — analyze, lay out trade-offs, recommend a direction, leave the decision to you.** Do not mark resolved.
- Finding 5 (raw SQL rejection): **Option Y — mark resolved.**

### 0.3 Scope boundary

Reviewed in this report:

1. `OJAS_AGENT_SAFETY_CONTROL_MODEL.md`
2. `OJAS_DATA_RUNTIME_BUNDLE_MESSAGE_CATALOG_v0.3.md`
3. `ojas-data-runtime-bundle.schema.v0.3.json`
4. Fixture validation strategy (as established in the structural cleanup pass)

**Not** reviewed: 25 supporting documents in `phase1/` through `phase5/` and `deferred/`. They are out of scope per your queue.

---

## 1. Reviewed artifacts — summary verdict

| # | Artifact | Verdict |
|---|---|---|
| 1 | Parent control model | **Accept with edits.** Five small edits; one new section needed (v1 packaging note already present, requires reference from §10 sequence); all seven resolved decisions hold. |
| 2 | Message catalog v0.3 | **Catalog needs revision before schema work.** Two internal contradictions found (one significant). Several gaps with the schema are catalog-side. |
| 3 | Bundle JSON Schema v0.3 | **Schema correction list.** Gap with catalog on several fields; schema is permissive where catalog is strict (`input` shape, audit-id type). |
| 4 | Fixture validation strategy | **Accept with one revision.** Split-fixture approach is the right permanent strategy. One mandatory addition: a negative-fixture story. |

Detailed findings below.

---

## 2. Resolved finding

### Finding 5 — Raw SQL rejected in Policy-Built Mode

**Status: RESOLVED — confirmed as intended behavior.**

The catalog and schema both align on this. Catalog §2.10 defines `data-execute-request` with no `sql` field. Catalog §2.12 confines raw SQL to `sql-review-request`, which requires:

- `reviewer-principal-id` (human reviewer)
- `elevated-policy-ref`

Schema enforces `additionalProperties: false` on `data-execute-request`. A test payload containing `sql` produces:

```
Additional properties are not allowed ('sql' was unexpected)
```

This is the **type-level** enforcement of invariant I-6 ("LLM authors intent, not executables") and the structural guarantee that the LLM path cannot author SQL. Working correctly. No edit needed.

Recommendation: include this case in the negative-fixture story (see §6.3 of this report).

---

## 3. Parent control model review

### 3.1 Scope question — "Is the Ojas-only scope still correct?"

**Yes.** Section 4 (Layer Ownership) preserves Ojas as the witness/enforcer surface with strict boundaries: external policy authority owns decisions, external credential authority owns minting/rotation/revocation, workflow authority remains external. Path B is preserved structurally, not merely asserted.

### 3.2 Path B question — "Is Path B still preserved?"

**Yes.** Three explicit references confirm:

- §4 "Ojas Credential Boundary" — Ojas owns handle-only execution; external authority owns minting/rotation/revocation
- §4.5 "Path B preserved" subsection — coupling is packaging, not architectural merger
- §9.1 D-9 — split synchronous gate (Ojas → external) from async observation; external authority decides permit/halt

No drift into Ojas-owns-everything territory. Good.

### 3.3 v1 packaging — "Does the v1 packaging section need adding?"

**Already present** as §4.5. However, §10 ("Schemas, APIs, and contract artifacts — sequenced downstream work") references the bundle implicitly but should explicitly cite §4.5 as the packaging authority. One-line edit.

### 3.4 Deferred decisions — "Are D-4, D-7, D-10 still deferred?"

**Yes, correctly.**

- D-4 (reconciliation truth source per integration): correctly per-integration concern; one truth source per integration; cannot be decided at parent level
- D-7 (tool-provenance verification): belongs to standalone Ojas Runtime, not the data bundle
- D-10 (per-product Ojas integration model): correctly per-product (sidecar vs library vs service mesh); cannot be decided generically

### 3.5 Resolved decisions — "Are D-1, D-2, D-3, D-5, D-6, D-8, D-9 acceptable?"

Reviewed each individually.

| Decision | Verdict | Notes |
|---|---|---|
| D-1 (latency 500ms/200ms) | **Accept** | Standard for human-reaction-window arguments; matches catalog §8.1 |
| D-2 (deny-by-timeout distinct from deny-by-policy) | **Accept** | Forensic distinction is correct; reflected in catalog §8.2 effective-decision-code |
| D-3 (3-axis taxonomy) | **Accept** | Axis 3 "scope of effect" composes well; rules in §9.1 D-3 trigger correctly |
| D-5 (60s window, default 100, per-(actor, entity)) | **Accept** | Matches catalog §6.1 bulk-context-observed |
| D-6 (recent-destroy index, 30-min, scoped tuple) | **Accept** | Matches catalog §6.2; pattern-confidence-class distinguishes match strength |
| D-8 (Postgres append-only v1 + digest fields) | **Accept** | Schema language consequence is correctly stated; CDDL deferral aligns |
| D-9 (split sync gate from async stream) | **Accept** | Matches catalog §8.1/8.2/8.3; broker not on critical path for destructive |

### 3.6 Verdict

**Accept with edits.**

Required edits (small):

1. **§10 referent.** Add explicit pointer "see §4.5 for v1 packaging that the catalog covers" — currently §10 talks about "bundle catalog" without citing the packaging section.
2. **§9.3 emitter table.** Should be added to parent (currently lives only in catalog §9.3). Parent §4 mentions "Emitter provenance is a typed field" but doesn't enumerate. Adding the constants here makes them parent-level invariants, not catalog-level.
3. **Invariant I-3 wording.** Says "Emission failure means execution failure" — true but doesn't bind it to a specific mechanism. Suggest: "Emission failure for pre-execution audit means the execution request will fail with `deny-structural` per catalog §3.3."
4. **§5 invariant ordering.** I-10 (append-only on disjoint domain) should be I-3 or earlier; it underpins I-3, I-4, I-8. Currently last makes it feel like an addendum.
5. **§9.2 D-4 wording.** "behavior for those needs to be specified (likely: emit reconciliation-not-possible warning at integration registration time)" — the "likely" is uncertain; either commit or remove the parenthetical.

None of these edits change resolved decisions or the architecture.

---

## 4. Message catalog review

### 4.1 Coverage check — "Does the catalog represent the eleven required surfaces?"

| Surface | Section | Coverage |
|---|---|---|
| LLM boundary | §2.1 + §9.1 | Complete |
| Safe query plan | §2.5 + §2.6 + §2.7 | Complete |
| Mutation preflight | §2.8 | Complete |
| Sanitized feedback | §2.9 + §3.4 | Complete |
| Credential handle flow | §3.2 + §4.1 + §4.2 + §4.3 | Complete |
| Pre-execution audit binding | §3.3 + §8.1 + §8.2 | Complete |
| Field-level audit | §3.6 | **Has internal contradiction (see §4.3 below)** |
| Bulk-context signal | §6.1 | Complete |
| Create-after-destroy signal | §6.2 | Complete |
| Reconciliation hooks | §3.7 + §7.1 + §7.2 | Complete |
| Stream/gate split | §8.1 + §8.2 + §8.3 | Complete |

Coverage is structurally complete. One internal contradiction (next subsection).

### 4.2 Internal contradiction A — field-level-audit emitter

**The bug:** Catalog §3.6 says `emitter` for `field-level-audit-record` is the typed constant **`ojas-data`**.

Catalog §5.3 (record-type table) and §9.3 (Emitter provenance table) both say `field-level-audit` is owned/emitted by **`ojas-runtime-data`**.

The two are inconsistent. One of them must change.

**Which is right?**

Looking at parent §4 "Ojas Runtime" responsibilities: "Emits pre-execution events..." and capability 6 in §4.5 "Field-level audit emission" is explicitly listed under the runtime-data module. So the runtime-data attribution is correct.

§3.6 contains the bug. The fix is to change §3.6's `emitter` line from `ojas-data` to `ojas-runtime-data`.

**Why it matters:** The emitter is a typed constant. Anything generated from the catalog (including the schema, which I derived from the catalog) inherits the inconsistency. The runtime-data schema correctly uses `ojas-runtime-data` for field-level-audit-record. Fixtures use `ojas-runtime-data`. So the schema and fixtures matched §5.3/§9.3, not §3.6. Catalog §3.6 is the lone wrong location.

**Impact on existing artifacts:** The fixtures and schemas are already consistent with the corrected catalog. No fixture changes required after the catalog edit.

### 4.3 Internal contradiction B — `input` shape

**The bug (smaller):** Catalog §2.10 says "the v0.2 `input: { * tstr => any }` open surface is replaced with **discriminated per-operation input types**." But §2.10 then defines `input` only as "conditional / structured input shape per operation" without specifying what those discriminated types are, where they're defined, or how `data-execute-request` carries discriminator metadata.

This is more of a gap than a contradiction: the catalog declares an invariant but does not define the mechanism. The schema reads it as `type: object` (unconstrained), which is permissive — the v0.2 gap that v0.3 claimed to close is still open in practice.

**Two ways to close it:**

A. **Discriminated per-operation `input` types in the catalog.** Each operation has a documented input shape. The catalog references it; the schema uses a discriminator on `operation` to pick the correct sub-schema. This is the right answer but requires defining several new types (one per operation).

B. **Restrict to LLM path only.** Remove `input` from `data-execute-request`. All requests use `extracted-intent`. Human/operator paths use `sql-review-request` (already specified) or future request types per actor-kind. This is simpler but eliminates a path the catalog seems to want.

**Recommendation in this report:** A is the better answer because the catalog says "for human/operator requests, the input shape is documented per operation." But A requires actual work (defining per-operation input shapes), so this is a real open item, not a small edit.

### 4.4 Other catalog observations

**O-2 (no-progress halt — boolean vs separate record types).** This is in the catalog's own open items. The current `terminal: boolean` approach is simpler. Separate types would help downstream consumers filter, but they can also filter on `terminal == true`. Keep current.

**§3.6 fields-returned wording.** "Required when stage = post-execution and operation = read/aggregate/export" — this is good, but the schema's conditional rule only checks read/export/aggregate. Same semantic; the schema is consistent. Worth verifying the operation-code enum keeps "aggregate" in both.

**§5.2 `data-operation-audit` as "record-type-specific payload".** Catalog's framing is explicit: this is a payload that lives inside `evidence-record` (§5.1), not a standalone top-level message. This framing has implications for the schema (see finding 3 below).

**§4.2 `credential-selection` direction.** Listed as "authority → Ojas response, internal". This is fine, but the field set listed in §4.2 doesn't match the recommendation in §3.2 (which references handle-id, scope-snapshot-digest). Quick verification needed that all fields used downstream are present in §4.2's table.

**§2.4 `pre-execution-audit-required` computed.** The catalog correctly notes this is "computed from action-class + resource-class + risk-class per D-3," not a free-toggle. Good. The schema correctly marks both `pre-execution-audit-required` and `mutation-preflight-required` as `required: true`.

### 4.5 Verdict

**Catalog needs revision before schema work.**

Required revisions:

1. **§3.6 emitter fix** (`ojas-data` → `ojas-runtime-data`). Mandatory. One-token change.
2. **§2.10 `input` shape clarification.** Either define discriminated per-operation types (A) or remove `input` from `data-execute-request` (B). Open decision.
3. **Optional: §4.2 verification.** Cross-check credential-selection field set against downstream uses.

After these, the catalog can be considered ready for schema correction work.

---

## 5. JSON Schema review

This section compares the bundle JSON Schema to the catalog. Per scope, I am identifying gaps, not fixing them.

### 5.1 Method

I checked each catalog message against its schema definition for:

- Field presence
- Required vs optional alignment
- Type alignment
- Closed-enum membership alignment
- Discriminator and conditional rules

### 5.2 Schema correction list (gaps and divergences)

| # | Issue | Catalog § | Schema location | Impact |
|---|---|---|---|---|
| S1 | `audit-id` typed inconsistently across the three schemas (covered in finding 1 below) | §1.1 + §5.1 | runtime-data + evidence-store + bundle | Medium |
| S2 | `mutation-preflight-result` has no top-level $defs entry, but its existence as a structured message in §2.8 suggests it should be addressable (covered in finding 2 below) | §2.8 | bundle.$defs (missing) | Medium |
| S3 | `data-operation-audit` has no top-level $defs entry; catalog frames it as a payload-not-message, schema follows that (covered in finding 3 below) | §5.2 | runtime-data + evidence-store (none expose) | Medium |
| S4 | `data-execute-request.input` is `type: object` (unconstrained); catalog claims v0.3 closes this with discriminated types | §2.10 | bundle.$defs.data-execute-request.properties.input | High (the v0.3 delta is not enforced at schema layer) |
| S5 | `policy-state-digest` and `instruction-context-digest` optional in schema; catalog also marks them optional but their purpose (I-1 enforcement evidence) suggests they should sometimes be required (covered in finding 4 below) | §1.5 | bundle.$defs.request-context | Medium |
| S6 | `pre-execution-audit-ref` optional in schema; catalog requires it when policy mandated pre-execution audit; runtime enforces, schema does not | §2.10 | bundle.$defs.data-execute-request | Low (runtime enforcement is the right layer) |
| S7 | `data-execute-response.audit` typed only as `type: object` (unconstrained); catalog says it carries `data-operation-audit` per §2.11 | §2.11 | bundle.$defs.data-execute-response | Medium |
| S8 | `data-execute-response.preflight` typed only as `type: object`; catalog says it carries `mutation-preflight-result` | §2.11 | bundle.$defs.data-execute-response | Medium (related to S2) |
| S9 | `data-execute-response.resolved-intent` typed only as `type: object`; catalog says it carries `resolved-intent` (§2.3) | §2.11 | bundle.$defs.data-execute-response | Low |
| S10 | `data-policy-decision.scope-predicates` typed as `array` (unconstrained items); catalog says items are `scope-predicate` structures | §2.4 | bundle.$defs.data-policy-decision | Medium |
| S11 | `data-policy-decision.masked-fields` / `blocked-fields` typed as unconstrained `array`; catalog says items are `masked-field` / `blocked-field` structures | §2.4 | bundle.$defs.data-policy-decision | Medium |
| S12 | `data-execute-response.credential-selection` typed only as `type: object`; catalog says it carries `credential-selection` (§4.2) | §2.11 | bundle.$defs.data-execute-response | Low |
| S13 | `record-type-code` exists in evidence-store schema but not in the bundle schema's `record-type` references | §5.3 | bundle (missing); evidence-store (present) | Low |
| S14 | `effective-decision-code` enum in schema includes `deny-by-no-progress`; not in catalog §1.8 explicitly | §1.8 | bundle.$defs.effective-decision-code | Low (the value is semantically reasonable; catalog should add it) |

### 5.3 Schema correction list — common pattern

Most issues (S4, S7, S8, S9, S10, S11, S12) are the same kind: **the schema declares `type: object` or `type: array` where the catalog has a typed structure**. This is the kind of regression that's invisible during basic validation (everything passes) but defeats the schema's purpose for catching contract violations. Worth fixing as a batch.

### 5.4 Verdict

**Schema correction list produced (S1–S14).** No improvements applied. The list should be worked through after catalog revision (because S2, S3, S7, S8, S10, S11 depend on catalog decisions).

---

## 6. Fixture validation strategy review

### 6.1 Is the split-fixture approach the permanent strategy?

**Yes, recommended.** Two reasons:

1. **Each fixture validates against exactly one $defs entry.** This is what makes fixtures useful: a fixture's status (OK/FAIL) precisely indicates whether one message shape conforms. The wrapper approach we initially used hid validation problems behind a "data-execute-request and response together" shape that no real protocol message would ever take.

2. **Per-scenario folders preserve scenario coherence.** Each fixture folder is a complete narrative (request, response, audit, signal, README). The README explains the flow; the JSON files are individually checkable. This combines documentation value with conformance value.

The cost is: more files. Trade-off accepted.

### 6.2 Should the skipped fixture become valid after schema fix?

**Depends on resolution of finding 2.**

- If `mutation-preflight-result` gets a top-level $defs entry → fixture validates → SKIP becomes OK
- If `mutation-preflight-result` stays embedded-only → fixture is moved/removed → SKIP becomes N/A (replaced by a fixture of `data-execute-response` with `preflight` populated)

Either way, the eventual state is no SKIPs. Current SKIP is a marker for "decision pending on finding 2."

### 6.3 Should each scenario have request/response/audit/signal fixtures?

**Yes — and one addition: negative fixtures.**

The 8 fixtures are all positive (this is what a valid <thing> looks like). Negative fixtures (this is what an invalid <thing> looks like, and validation correctly catches it) are equally important for:

- Confirming schema rejection works (finding 5 is exactly this)
- Documenting what the schema is supposed to refuse
- Regression-catching when a schema is loosened by mistake

I recommend adding a `fixtures/_negative/` folder with:

- `request_with_sql_field/` — shows the rejected shape; documents the expected error message
- `audit_with_wrong_emitter/` — shows the emitter-spoofing attempt; documents rejection
- `preflight_without_safety_critical/` — shows preflight with only advisory checks; documents rejection
- (Others as natural)

Negative fixtures are NOT validated by the current validator (which expects OK). They should be validated by a **second** validator script that expects FAIL with a specific error message.

### 6.4 Should the validation report become mandatory in every release bundle?

**Yes.** Three reasons:

1. **Regression detection.** A bundle that ships without rerun validation may have silently regressed. The report is the proof that the current bundle's fixtures still pass.

2. **Schema change discipline.** When schemas change, fixtures may break. The validation report makes the breakage visible.

3. **Findings tracking.** The report documents the SKIP and any known schema gaps. It is the running record of the schema's debt.

Operationally, the validation step should be:

```
run validate.py → produce VALIDATION_REPORT.md → bundle is shippable
```

If validation fails, the bundle does not ship.

### 6.5 Verdict

**Fixture strategy accepted with one revision.**

Revision: add a negative-fixtures section to the strategy, with its own validator expecting controlled failures.

---

## 7. Findings — analysis and recommendations (Option X)

### Finding 1 — `audit-id` typed inconsistently across schemas

**Where it shows up:**

- Catalog §1.1: `identifier` defined as "lowercase-snake-case string, max 128 chars" for "logical names from the registry"
- Catalog §5.1: `audit-id` typed as `identifier`
- Catalog §3.6: `audit-id` typed as `identifier`
- Runtime-data schema: `audit-id` → `$ref: identifier` (strict pattern `^[a-z][a-z0-9_]{0,127}$`)
- Evidence-store schema: `audit-id` → own type `{type: string, minLength: 1, maxLength: 128}` (free-form)
- Bundle schema: no explicit audit-id type; appears inside `audit` object as unconstrained

**The conceptual problem:** The catalog treats `audit-id` as a registry-style identifier. But `audit-id` is operationally a **globally unique opaque ID** generated per-record, not a logical registry slug. The catalog's `identifier` type fits entity names ("student_profile"), credential handle IDs ("vault_token_acme_001"), and tenant names — registry slugs. It does not fit ULIDs, UUIDs, snowflake IDs, or any high-throughput ID generator's output.

**The schemas split because the catalog's framing is wrong.** The runtime-data schema followed catalog §5.1 literally. The evidence-store schema defined a looser type because the author (me) noticed the operational mismatch and quietly relaxed it.

**Trade-offs:**

| Option | Pros | Cons |
|---|---|---|
| Keep as `identifier` (snake-case) | Single canonical type, consistent with catalog §1.1, human-readable | Forces ID generators to produce snake-case; rules out ULID/UUID; sortability requires extra work |
| Define new `audit-id` type as opaque ID | Matches operational reality; allows ULID/UUID; lexicographically sortable IDs are common pattern | Two ID types in the catalog (`identifier` for registry, `audit-id` for records); slightly more vocabulary |
| Loosen `identifier` to accept opaque IDs | One type; flexible | `identifier` now means two things; catalog §1.1 wording becomes vague |

**Recommendation (left to you):** Define a new `audit-id` type as an opaque ID. Specifically:

```
audit-id = string matching ^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$
```

This allows ULIDs (e.g., `01HG3K9XQ8WR2VBN6QT5MZX1Y4`), UUIDs (with or without hyphens), snowflake IDs, and KSUID. It excludes whitespace and control characters. It does not require lowercase.

This is the most operationally honest answer. But the trade-off is real: it introduces a second ID type. Other answers (keep snake-case; loosen `identifier`) are defensible.

**Status: open. Decision needed.**

### Finding 2 — `mutation-preflight-result` missing top-level schema

**Catalog framing:** §2.8 describes `mutation-preflight-result` as a structured message with required fields. §2.11 references it as `data-execute-response.preflight`. §3.8 describes `mutation-preflight-orchestration-record` as the **audit emission** that references the preflight result via a digest field (`preflight-result-digest`).

So the catalog already distinguishes two things:

- The **payload** that travels inside `data-execute-response.preflight` (§2.8)
- The **audit record** that records the orchestration of that preflight (§3.8)

**The question:** Does the payload (§2.8) ever appear standalone?

**Trade-offs:**

| Option | Effect |
|---|---|
| A. Add `mutation-preflight-result` to bundle schema $defs and oneOf | Standalone fixture validates; preflight payload addressable independently; consistent with §3.8's reference-by-digest model |
| B. Keep it embedded inside `data-execute-response.preflight` only | Catalog's payload framing preserved; no need for a top-level fixture; one fewer message in the protocol surface |

**The decision pivots on:** Does any consumer ever need to consume a preflight result independent of the full execute response? Examples:

- An orchestration consumer that watches preflight results separately? Probably not — §3.8 covers this via the orchestration record.
- An archive consumer? §3.8's orchestration record + reference is enough.
- A debugger or developer tool? Maybe — but that's a tooling concern, not a protocol concern.

**Recommendation (left to you):** **Option B — keep embedded.** The catalog's §3.8 already provides the audit-visible form of the preflight result via the orchestration record. The standalone payload doesn't need its own protocol surface.

Implementation if B is chosen:
- Fixture 03's `preflight_result.json` is removed
- A new fixture file `preflight_in_response.json` shows the full `data-execute-response` with `preflight` populated
- Validator no longer SKIPs anything

**Status: open. Decision needed.**

### Finding 3 — `data-operation-audit` missing top-level schema

**Catalog framing:** §5.2's section title explicitly calls it "a record-type-specific payload." §5.1 defines `evidence-record` as the envelope. §5.3 lists `data-operation-audit` as one record-type-code value owned by data-core.

**So the catalog already treats `data-operation-audit` as a payload, not a top-level message.** The schema correctly does not expose it at top-level.

**But there's an inconsistency:** the runtime-data schema exposes `field-level-audit-record` directly as a top-level $defs entry, not wrapped in evidence-record. So the schema treats `field-level-audit-record` differently from `data-operation-audit` even though both are described as "audit records" in the catalog.

**Trade-offs:**

| Option | Effect |
|---|---|
| A. Expose `data-operation-audit` as top-level entry, like field-level-audit-record | Both record types addressable for fixtures; symmetry; allows direct schema validation; matches what runtime-data already does |
| B. Wrap field-level-audit-record in evidence-record at the schema level too, drop standalone exposure | Consistent with catalog's "payload, not message" framing; one canonical wrapping pattern |
| C. Keep current asymmetric exposure | Status quo; field-level audits validate standalone, data-operation-audits validate only inside evidence-envelope |

**The catalog is the issue.** The catalog's §5.1 envelope is described as "every record in Evidence Store carries this envelope." If that's true, then BOTH should be wrapped. The runtime-data schema's standalone exposure of `field-level-audit-record` is a schema-level choice that catalog §5.1 doesn't sanction.

**Recommendation (left to you):** **Option B — wrap consistently, drop standalone field-level audit exposure.** The catalog §5.1 envelope is the canonical record shape. The schema should reflect this. Fixtures should provide an `audit.json` that's a full `evidence-record` with the payload populated, not a bare payload.

This is a bigger change for fixtures (every audit fixture needs to be re-wrapped) but it removes the conceptual asymmetry. It also means the schema would have just one place that audit records live (inside `evidence-record.payload`), which is more honest about the storage architecture.

**Status: open. Decision needed.**

### Finding 4 — `policy-state-digest` and `instruction-context-digest` optionality

**Catalog framing:** §1.5 marks both as optional on `request-context`. Catalog says `instruction-context-digest` is "for I-1 enforcement evidence" — i.e., evidence that the agent received specific instructions, used for invariant I-1 ("no advisory-only safety").

**The question:** Are these meaningful when omitted?

**Three cases:**

1. **Read-only operations on non-production data:** the digests are observability nice-to-haves; absence is fine.
2. **Mutate operations on production data:** the digests link the operation to the policy/instruction state when the agent's intent was formed. Their absence means audit cannot reconstruct "what did the agent know at decision time?" — which weakens I-1's forensic value.
3. **Destructive/irreversible operations:** absence breaks the chain entirely. If pre-execution audit cannot link to the active policy/instruction state, the audit itself is structurally weaker.

**Trade-offs:**

| Option | Effect |
|---|---|
| A. Keep optional everywhere | Minimal protocol burden; agents that don't compute digests still send valid requests |
| B. Require both for destructive/irreversible actions | Stronger forensic chain for the cases where it matters most; agents must compute digests for those paths |
| C. Require both always | Strongest invariant; but adds protocol surface for low-risk operations where the digests are observability noise |
| D. Tiered — required by risk-class | Most defensible structurally; complicates validation (now risk-class-aware) |

**Recommendation (left to you):** **Option D — tiered by risk-class.** Specifically:

- Risk class `critical` or `high` → both required
- Risk class `medium` → required for `policy-state-digest`; optional for `instruction-context-digest`
- Risk class `low` → both optional

This matches the operational pattern: forensic strength scales with what's at stake. The schema can enforce this via conditional `if/then` rules driven by risk-class on the policy-decision.

The complication: at request-time (when the digests are sent), the risk-class hasn't been computed yet — that's the policy decision. So either:

1. The schema checks at response-time (data-execute-response references both the digests from request-context and the resolved risk-class), or
2. The schema requires both digests at request-time **whenever** the actor-kind is agent and operation is mutate/destructive/insert/update/delete (a heuristic that's almost always right and is checkable at request-time)

Approach (2) is simpler. Approach (1) is purer.

**Status: open. Decision needed.**

---

## 8. Schema correction list (summary)

From §5.2 of this report, in priority order:

### Must-fix before schema rework

| # | Item |
|---|---|
| S1 | Resolve `audit-id` type per finding 1 decision |
| S2 | Resolve `mutation-preflight-result` exposure per finding 2 decision |
| S3 | Resolve `data-operation-audit` exposure per finding 3 decision |
| S5 | Resolve digest optionality per finding 4 decision |

### High-priority schema corrections (apply after must-fix decisions)

| # | Item |
|---|---|
| S4 | Define discriminated `input` types or remove `input` from `data-execute-request` |
| S7 | Reference `data-operation-audit` (or evidence-record) for `data-execute-response.audit` |
| S10 | Define `scope-predicate` $defs entry and reference it |
| S11 | Define `masked-field` and `blocked-field` $defs entries and reference them |

### Medium-priority schema corrections

| # | Item |
|---|---|
| S8 | Reference `mutation-preflight-result` (or remove if Option B in finding 2) |
| S9 | Reference `resolved-intent` for `data-execute-response.resolved-intent` |
| S12 | Reference `credential-selection` for `data-execute-response.credential-selection` |

### Low-priority schema corrections

| # | Item |
|---|---|
| S6 | Document that `pre-execution-audit-ref` is runtime-enforced, not schema-enforced (already correct, just document) |
| S13 | Add `record-type-code` to bundle schema (for cross-reference) |
| S14 | Add `deny-by-no-progress` to catalog §1.8 effective-decision-code (catalog gap; schema already has it) |

---

## 9. Fixture correction list (summary)

| # | Item | Trigger |
|---|---|---|
| F1 | Replace `preflight_result.json` (currently SKIP) | After finding 2 decision |
| F2 | Re-wrap audit fixtures inside `evidence-record` envelope | After finding 3 Option B decision (if chosen) |
| F3 | Add negative-fixtures folder under `fixtures/_negative/` | After fixture strategy revision §6.5 |
| F4 | Add second validator (`validate_negative.py`) expecting controlled failures | With F3 |
| F5 | Make validation report mandatory in release bundle | With F3 (general policy) |
| F6 | Update fixture audit-id formats to comply with new `audit-id` type | After finding 1 decision |

---

## 10. Freeze readiness

### Parent control model

**Pending freeze.** Five small edits (§3.6 of this report). Once applied, the parent reaches freeze-candidate state with three remaining deferred decisions (D-4, D-7, D-10) at integration-time, exactly as the parent document already states.

### Message catalog v0.3

**Not freeze-ready.** Must revise before schema work:

- Mandatory: §3.6 emitter contradiction (one-token fix)
- Strongly recommended: §2.10 `input` shape clarification (depends on Finding A vs B choice)
- Verification: §4.2 credential-selection field set against downstream uses
- Add: `deny-by-no-progress` to §1.8 effective-decision-code

After these, the catalog reaches review-candidate state and can drive schema correction work.

### Bundle JSON Schema v0.3

**Not freeze-ready.** Cannot freeze before catalog revision, because S2/S3/S5/S7/S8/S10/S11 all depend on catalog decisions (findings 1–4 and the §2.10 `input` resolution).

After catalog revisions, work through Schema correction list (S1–S14 in §8 of this report).

### Fixture strategy

**Freeze-ready as a strategy** (split fixtures, per-scenario folders, validation report mandatory).

Implementation (the actual fixture files) is not freeze-ready because:

- F1 depends on finding 2
- F2 depends on finding 3
- F6 depends on finding 1
- F3 and F4 are net-new work

---

## 11. Recommended order of work after this report

This report does not implement anything. When implementation starts:

1. **Decide findings 1–4** (the four open decisions).
2. **Apply parent control model edits** (§3.6 of this report).
3. **Apply catalog edits** based on the decisions:
   - §3.6 emitter fix (mandatory)
   - §2.10 input resolution
   - §4.2 verification
   - §1.8 add `deny-by-no-progress`
4. **Apply schema corrections** per §8 of this report.
5. **Update fixtures** per §9 of this report.
6. **Re-run validation** and produce a new VALIDATION_REPORT.md.
7. **Produce a corrected bundle** with updated README reflecting freeze state of each artifact.

The order matters: catalog before schema before fixtures, because the upstream artifacts define what the downstream ones validate against.

---

## 12. Open decisions queue (for your action)

| Decision | Question | Where decided |
|---|---|---|
| D-F1 | `audit-id` type — keep as identifier, define new opaque-id type, or loosen identifier? | Recommendation: define new `audit-id` type |
| D-F2 | `mutation-preflight-result` exposure — top-level $defs entry or embedded only? | Recommendation: embedded only (Option B) |
| D-F3 | Audit record exposure — standalone payload or wrapped in evidence-record uniformly? | Recommendation: wrap uniformly (Option B) |
| D-F4 | Digest optionality — flat optional, flat required, or tiered by risk-class? | Recommendation: tiered (Option D) |
| D-C1 | Catalog §2.10 `input` shape — discriminated per-operation types or remove `input` entirely? | Recommendation: discriminated types (A) |

All five are open. None are urgent in the sense that v1 cannot ship without them, but all five are needed before schema and fixtures reach freeze.

---

## Closing

This report is the review. No artifact has been modified in this turn. The next turn — when you direct it — will be the catalog revision, then schema corrections, then fixture updates, then revalidation. The order matters because the upstream artifacts define the downstream ones' shape.

The most important finding in this report is **the §3.6 emitter contradiction** in the catalog. It is a one-token fix that resolves an internal inconsistency. Everything else is decision work or correction work that depends on decisions.

The five open decisions (D-F1 through D-F4 plus D-C1) are governance-grade. Your call, not mine.
