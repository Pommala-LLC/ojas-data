# Ojas Data — Freeze Registry (v1.0)

This document is the canonical decision log for the Ojas Data v1.0 design. It lists every freeze decision with a stable ID, a brief statement, the document that owns the full text, and the date of freeze.

This is intended as a reference index for cross-document traceability. The full freeze paragraphs live in the destination documents; this registry exists so that any freeze can be located by ID and any document section can be traced to the freezes it implements.

---

## How to read this registry

Each freeze has:

- **Stable ID** (e.g., `OD-RS-001` for Resolver Scope, `OD-QRB-001` for Query Repair Boundary, etc.)
- **Brief statement** — one-sentence summary
- **Owning document** — where the full text lives
- **Section reference** — the specific section within the owning document
- **Status** — `FROZEN` (locked) or `OPERATIONAL_DEFAULT` (deployment-configurable with documented default)

The freezes are grouped by the layer of the design they affect.

---

## Layer 1 — Resolver and registry (Resolver Scope document)

### OD-RS-001 — Closed-world resolution

**Statement:** The compiled registry is the only authority for what entities and fields exist; the resolver does not query the database for schema discovery at runtime.

**Owning document:** `OJAS_DATA_RESOLVER_SCOPE.md` §1.1

**Status:** FROZEN

---

### OD-RS-002 — Match vs execute separation

**Statement:** Matching is case-insensitive and normalized via N1–N7; execution preserves physical identifiers verbatim; case-fold collisions are compile-time errors.

**Owning document:** `OJAS_DATA_RESOLVER_SCOPE.md` §2.1

**Status:** FROZEN

---

### OD-RS-003 — N1–N7 normalization pipeline

**Statement:** Aliases and incoming terms are normalized through a seven-step pipeline (NFKC, lowercase, separator-to-space, whitespace collapse, trim, punctuation strip, diacritic strip) uniformly.

**Owning document:** `OJAS_DATA_RESOLVER_SCOPE.md` §2.2

**Status:** FROZEN (with locale-controlled N7 per §2.4)

---

### OD-RS-004 — Normalization pipeline versioning

**Statement:** The N1–N7 pipeline is versioned in every compiled registry; pipeline changes require full registry recompile, not in-place migration.

**Owning document:** `OJAS_DATA_RESOLVER_SCOPE.md` §2.5

**Status:** FROZEN

---

### OD-RS-005 — Qualified Alias Rule

**Statement:** Qualified aliases resolve normalized alias collisions; author-supplied preferred, compiler-generated allowed opt-in, runtime-generated forbidden; qualified aliases are first-class and emitted uniformly across scopes.

**Owning document:** `OJAS_DATA_RESOLVER_SCOPE.md` §3.2

**Status:** FROZEN

---

### OD-RS-006 — Scope-aware alias collision rule

**Statement:** After normalization, no LLM-visible alias may map to more than one visible registry field within the same authorized scope; collisions must fail compile unless resolved via qualifiers or auto-qualify.

**Owning document:** `OJAS_DATA_RESOLVER_SCOPE.md` §3.5

**Status:** FROZEN

---

### OD-RS-007 — First-class alias status

**Statement:** Qualified aliases are first-class registry aliases — what the LLM sees in hints or user clarification must be resolvable by the resolver later. No translation layer between emission and resolution.

**Owning document:** `OJAS_DATA_RESOLVER_SCOPE.md` §3.8

**Status:** FROZEN

---

### OD-RS-008 — Emission uniformity across scopes

**Statement:** The runtime emits the registered qualified form consistently; it must not simplify a qualified alias to an unqualified alias merely because the current scope makes the term temporarily unambiguous.

**Owning document:** `OJAS_DATA_RESOLVER_SCOPE.md` §3.9

**Status:** FROZEN

---

### OD-RS-009 — Strictest-wins still applies to qualifiers

**Statement:** Qualified aliases do not bypass visibility gates; a qualified alias may be emitted only if the underlying field passes scope, policy, sensitivity, masking, and LLM-visibility checks.

**Owning document:** `OJAS_DATA_RESOLVER_SCOPE.md` §3.10

**Status:** FROZEN

---

### OD-RS-010 — Scope dimensions are not LLM-visible

**Statement:** The LLM-facing hint surface never names scope dimension columns; scope violations produce generic messages, not predicate-specific messages.

**Owning document:** `OJAS_DATA_RESOLVER_SCOPE.md` §4.2

**Status:** FROZEN

---

### OD-RS-011 — Drift rule (no auto-include)

**Statement:** Drift detected between the live database and the compiled registry produces a drift report; the report does not modify the registry. Registry updates require re-running the compile pipeline with developer approval.

**Owning document:** `OJAS_DATA_RESOLVER_SCOPE.md` §5.1

**Status:** FROZEN

---

## Layer 2 — Query Repair Boundary (Query Repair Boundary document)

### OD-QRB-001 — Strictest-wins gate composition

**Statement:** A field or hint must pass every applicable visibility, policy, sensitivity, scope, masking, and LLM-visibility gate; any failed gate suppresses emission regardless of other gates passed.

**Owning document:** `OJAS_DATA_QUERY_REPAIR_BOUNDARY.md` §1.1

**Status:** FROZEN

---

### OD-QRB-002 — Discriminator-first principle

**Statement:** Failure category is decided before retry; `EXTRACTION_*` failures are retry-eligible; `RESOLVER_*`, `POLICY_*`, `SCOPE_*`, `SENSITIVE_FIELD_*`, `CREDENTIAL_*`, `MUTATION_*` are authority-terminal.

**Owning document:** `OJAS_DATA_QUERY_REPAIR_BOUNDARY.md` §1.2

**Status:** FROZEN

---

### OD-QRB-003 — Channel separation

**Statement:** The LLM-facing retry channel and the user-clarification channel are physically separate code paths — two functions, two reviewers, two audit categories.

**Owning document:** `OJAS_DATA_QUERY_REPAIR_BOUNDARY.md` §1.3

**Status:** FROZEN

---

### OD-QRB-004 — Authorized-context principle

**Statement:** LLM-facing emissions derive from already-authorized context, never from the failed input; identical scope produces identical emission shape regardless of input.

**Owning document:** `OJAS_DATA_QUERY_REPAIR_BOUNDARY.md` §1.4

**Status:** FROZEN

---

### OD-QRB-005 — Outbound filtering rule

**Statement:** Successful database responses must pass through the privileged diagnostic classifier before reaching LLM or user-facing channels; sensitive fields are removed regardless of request-side policy.

**Owning document:** `OJAS_DATA_QUERY_REPAIR_BOUNDARY.md` §2.5

**Status:** FROZEN

---

### OD-QRB-006 — Unknown References Rule (1st safety freeze)

**Statement:** Unknown physical references are never LLM-repairable; the LLM must not receive raw database errors, hints, physical identifiers, or candidate sets.

**Owning document:** `OJAS_DATA_QUERY_REPAIR_BOUNDARY.md` §3.1

**Status:** FROZEN

---

### OD-QRB-007 — Safe Business-Term Hinting Rule (2nd safety freeze)

**Statement:** Ojas Data may provide the LLM with safe business-term hints only from the compiled registry, filtered by scope, policy, sensitivity; sensitive fields are excluded entirely; emissions are a function of authorized scope, not failed input.

**Owning document:** `OJAS_DATA_QUERY_REPAIR_BOUNDARY.md` §3.2

**Status:** FROZEN

---

### OD-QRB-008 — DB HINT Replacement Rule (3rd safety freeze)

**Statement:** Raw database hints are privileged diagnostics; Ojas Data may replace them with Safe Business-Term Hinting from the registry; the LLM-facing emission must not normalize to the same form as the failed input token.

**Owning document:** `OJAS_DATA_QUERY_REPAIR_BOUNDARY.md` §3.3

**Status:** FROZEN

---

### OD-QRB-009 — CUD Mutation Visibility Rule (4th safety freeze)

**Statement:** CUD operation failures are never LLM-repairable; the LLM receives only safe business-level categories, approved display labels, required-input prompts, and approved next-action choices; raw diagnostics remain privileged.

**Owning document:** `OJAS_DATA_QUERY_REPAIR_BOUNDARY.md` §3.4

**Status:** FROZEN

---

### OD-QRB-010 — Five-channel prompt taxonomy

**Statement:** All LLM-facing emissions flow through one of five channels (extraction, extraction-repair, safe-message-generation, read-only-query-repair, mutation-repair); mutation-repair is forbidden by design and not registered.

**Owning document:** `OJAS_DATA_QUERY_REPAIR_BOUNDARY.md` §4

**Status:** FROZEN

---

### OD-QRB-011 — Three-layer prompt design (schema/profile/payload)

**Statement:** LLM interactions use a three-layer contract: prompt schema (executable validator), prompt profile (registered instructions), runtime payload (per-call structured input); plain-text prompts are not sent at runtime.

**Owning document:** `OJAS_DATA_QUERY_REPAIR_BOUNDARY.md` §5

**Status:** FROZEN

---

### OD-QRB-012 — Prompt Schema Forbidden-Field Rule

**Statement:** Prompt schemas reject forbidden fields (physical identifiers, raw DB errors, policy reasons, candidate sets) before prompt construction; schemas are executable validators, not documentation.

**Owning document:** `OJAS_DATA_QUERY_REPAIR_BOUNDARY.md` §5.3

**Status:** FROZEN

---

### OD-QRB-013 — Output contract pinning

**Statement:** The `output_contract` field in a prompt schema must reference a canonical contract registered in the Ojas data contract registry with `versionKind: PINNED`; `RESOLVED` or `UNKNOWN` versions are not permitted.

**Owning document:** `OJAS_DATA_QUERY_REPAIR_BOUNDARY.md` §5.5

**Status:** FROZEN

---

### OD-QRB-014 — Visibility manifest as derived property

**Statement:** The visibility manifest in each envelope is derived from the profile, not authored per-call; the runtime cannot relax visibility per emission.

**Owning document:** `OJAS_DATA_QUERY_REPAIR_BOUNDARY.md` §5.6

**Status:** FROZEN

---

### OD-QRB-015 — Audit triple

**Statement:** Every LLM emission is audited with profile ID, profile version, profile fingerprint, schema ID, envelope fingerprint, and LLM response fingerprint; profile fingerprint mismatches fail closed in production.

**Owning document:** `OJAS_DATA_QUERY_REPAIR_BOUNDARY.md` §5.7

**Status:** FROZEN

---

### OD-QRB-016 — Sufficient-safe-context rule

**Statement:** If the LLM cannot fix the failure without protected context, no LLM retry is attempted; the failure routes to the appropriate non-LLM path.

**Owning document:** `OJAS_DATA_QUERY_REPAIR_BOUNDARY.md` §6

**Status:** FROZEN

---

### OD-QRB-017 — SQL comment stripping

**Statement:** SQL comments are stripped before AST extraction or policy check using a dialect-aware tokenizer; original SQL is preserved in privileged audit; comments never appear in LLM-facing channels.

**Owning document:** `OJAS_DATA_QUERY_REPAIR_BOUNDARY.md` §7

**Status:** FROZEN

---

## Layer 3 — Developer experience (Developer Guide)

### OD-DG-001 — Three-layer authority chain

**Statement:** Authority flows scanner → developer review → compiled registry; the scanner discovers, the developer approves meaning, the compiler creates runtime authority.

**Owning document:** `OJAS_DATA_DEVELOPER_GUIDE.md` §1

**Status:** FROZEN

---

### OD-DG-002 — Generated/ + overlay model

**Statement:** Scanner output writes to `generated/` (never edited by developer); developer overrides live in `registry.overrides.yaml`; the compiler merges both at compile time.

**Owning document:** `OJAS_DATA_DEVELOPER_GUIDE.md` §1.3

**Status:** FROZEN

---

### OD-DG-003 — Three-level scanner taxonomy

**Statement:** The scanner has three intelligence levels: Level 1 (structural, deterministic), Level 2 (governance heuristics with confidence), Level 3 (LLM-assisted aliasing); each level can be turned off independently.

**Owning document:** `OJAS_DATA_DEVELOPER_GUIDE.md` §2.1

**Status:** FROZEN

---

### OD-DG-004 — Strict review_status enum

**Statement:** Review status uses a strict enum (`DRAFT`, `REVIEWED_APPROVED`, `REVIEWED_REJECTED`, `REVIEWED_DEFERRED`); lowercase or alternate forms fail compile validation.

**Owning document:** `OJAS_DATA_DEVELOPER_GUIDE.md` §3.3

**Status:** FROZEN

---

### OD-DG-005 — CLI exit-code contract

**Statement:** CLI commands return stable, distinguishable exit codes for different failure types (`DRAFT_ENTRIES_REMAIN=10`, `VALIDATION_FAILED=11`, `CASE_FOLD_COLLISION=12`, `ALIAS_COLLISION=13`, etc.); JSON output available via `--output-format json`.

**Owning document:** `OJAS_DATA_DEVELOPER_GUIDE.md` §4.3

**Status:** FROZEN

---

### OD-DG-006 — Two-tier CLI structure

**Statement:** The CLI mirrors the document split: `ojas-data <verb>` for resolver/registry tooling, `ojas-data sql <verb>` for query-repair diagnostics, `ojas-data prompts <verb>` for prompt schema/profile tooling.

**Owning document:** `OJAS_DATA_DEVELOPER_GUIDE.md` §9

**Status:** FROZEN

---

### OD-DG-007 — Safe-hint as falsifiability surface

**Statement:** `ojas-data sql safe-hint` is the reference implementation of the Safe Business-Term Hinting freeze; `--explain` mode shows applied gates and selected aliases for auditor review.

**Owning document:** `OJAS_DATA_DEVELOPER_GUIDE.md` §6.2

**Status:** FROZEN

---

## Operational defaults (deployment-configurable)

### OD-OD-001 — No-progress detection default

**Statement:** Same failure category counts as no progress regardless of value variation (strict interpretation).

**Owning document:** `OJAS_DATA_DEVELOPER_GUIDE.md` §7.1

**Status:** OPERATIONAL_DEFAULT

---

### OD-OD-002 — Profile fingerprint mismatch default

**Statement:** Fail closed in production; warn in non-production.

**Owning document:** `OJAS_DATA_DEVELOPER_GUIDE.md` §7.2

**Status:** OPERATIONAL_DEFAULT

---

### OD-OD-003 — Unregistered column reports default

**Statement:** Enabled, weekly cadence to the data steward.

**Owning document:** `OJAS_DATA_DEVELOPER_GUIDE.md` §7.3

**Status:** OPERATIONAL_DEFAULT

---

### OD-OD-004 — Runtime drift verification default

**Statement:** Disabled; compiled registry is the runtime authority; periodic drift checks are the trust verification.

**Owning document:** `OJAS_DATA_DEVELOPER_GUIDE.md` §7.4

**Status:** OPERATIONAL_DEFAULT

---

### OD-OD-005 — Partial response preservation default

**Statement:** Preserved in privileged audit only.

**Owning document:** `OJAS_DATA_DEVELOPER_GUIDE.md` §7.5

**Status:** OPERATIONAL_DEFAULT

---

### OD-OD-006 — Degraded-mode default

**Statement:** Fail closed on all degraded states (model unavailable, registry load failure, classifier exception, audit unavailable).

**Owning document:** `OJAS_DATA_DEVELOPER_GUIDE.md` §7.6

**Status:** OPERATIONAL_DEFAULT (full design deferred — see `OJAS_DATA_DEFERRED_DESIGN_TOPICS.md`)

---

## Cross-cutting principles (referenced from multiple documents)

These are not new freezes; they are statements of cross-cutting properties that follow from the freezes above.

### OD-CC-001 — Closed-world authority across all layers

The compiled registry is the only runtime authority. Scanner outputs, drift reports, LLM responses, and database introspection results are not authority. This property holds in the resolver (OD-RS-001), the alias system (OD-RS-005, OD-RS-007), the drift detection (OD-RS-011), the prompt schemas (OD-QRB-012), and the audit (OD-QRB-015).

### OD-CC-002 — Authoring/runtime separation across all layers

Annotations, scanner outputs, and overlay files are authoring artifacts. The compiled registry, the prompt profile registry, and the audit log are runtime artifacts. The compile step is the boundary. This property holds in the developer flow (OD-DG-001), the registry compilation (OD-RS-001), the prompt design (OD-QRB-011), and the qualifier rule (OD-RS-005).

### OD-CC-003 — Channel separation as a primary safety mechanism

The LLM-facing and user-clarification channels are separate at the code level, not just the policy level. This property holds in the channel taxonomy (OD-QRB-010), the unknown references rule (OD-QRB-006), the safe business-term hinting rule (OD-QRB-007), and the qualifier rule (OD-RS-009).

### OD-CC-004 — Strictest-wins as the gate composition rule

All gates compose by suppression. This property holds in every freeze that involves visibility, policy, or sensitivity gating: OD-QRB-001 (foundational), OD-QRB-007, OD-RS-009 (qualifier-specific application).

---

## Total counts

- **Resolver Scope freezes:** 11 (OD-RS-001 through OD-RS-011)
- **Query Repair Boundary freezes:** 17 (OD-QRB-001 through OD-QRB-017)
- **Developer Guide freezes:** 7 (OD-DG-001 through OD-DG-007)
- **Operational defaults:** 6 (OD-OD-001 through OD-OD-006)
- **Cross-cutting principles:** 4 (OD-CC-001 through OD-CC-004)

**Total v1.0 frozen elements: 41** (35 freezes + 6 operational defaults)

---

## Change protocol

Once frozen, a freeze decision cannot be changed in place. Updating a freeze requires:

1. A short rationale describing why the change is needed
2. Identification of which other freezes or documents the change affects
3. A revised freeze paragraph in the owning document
4. A new ID variant (e.g., `OD-RS-005a`) if the change is incompatible with the original
5. A cross-reference back to the original freeze for traceability

Freezes are not changed silently. Every modification is auditable.

---

## Relationship to deferred topics

The freezes in this registry are the closed surface of the v1.0 design. Topics deferred for future design phases are documented separately in `OJAS_DATA_DEFERRED_DESIGN_TOPICS.md` with holding positions that the freezes in this registry support.

The deferred topics do not have freeze IDs because they are not yet frozen. When a deferred topic is taken up and frozen, it will receive a new ID in this registry.
