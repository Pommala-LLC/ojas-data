# Ojas Data Resolver Specification v1.0 — Part 4

**Version:** v1.0
**Status:** Final — complete resolver authority specification

**This is Part 4 of 4.** Appendices A, B, C and the final freeze statement.

- Part 1: §1 Purpose and boundary, §2 Core invariants, §3 Runtime modes, §4 Type and contract model, §5 Metadata authority, §6 Scope enforcement, §7 Stage 1 matching, §8 Retry boundary
- Part 2: §10 Failure category discriminator, §11 Compile-step signature, §12 Drift-report shape, §13 Disambiguation syntax, §14 Test corpus shape, §15 Multi-entity resolved-intent structure, §16 Full Pydantic schemas
- Part 3: §17.1 Two-tier registry, §17.2 Error model, §17.3 Approval workflow
- Part 4 (this file): Appendix A (frozen principles), Appendix B (versioning history reserved), Appendix C (conformance assertions), Appendix D (companion-spec references), Final v1.0 freeze statement

---

## Appendix A — Resolver frozen principles (v1.0)

The principles below are the v1.0 canonical list. Each one is enforced by code at the location named in its corresponding specification section. Adding, removing, or modifying a principle is a versioned change to this document.

1. **Pure function.** The resolver core is a pure function of extracted intent and compiled registry. Same inputs produce same outputs.

2. **Closed world.** No resolution outside the registry, ever. A database column not in the registry is treated as nonexistent.

3. **Terminal ambiguity.** Candidate sets greater than one fail; they do not collapse. No silent selection, no "most likely" candidate, no positional fallback.

4. **Candidate exposure split.** Full failure detail to audit, sanitized form to LLM, safe display labels to user. Physical identifiers never reach the LLM or the user.

5. **Deterministic authority.** Same compiled registry plus same extracted intent produces the same resolved intent, byte-identically. No LLM in the loop. No randomness. No retrieval-augmented disambiguation.

6. **Retry never changes authority.** Every retry attempt is a fresh resolution against the same registry. The resolver retains no cross-attempt state and relaxes no rules on subsequent attempts.

7. **Two runtime modes only.** `STRICT_DETERMINISTIC` is the default. `GOVERNED_EXTRACTION_RETRY` is the only approved exception, and only with a valid `ApprovalRecord`. No Lite mode.

8. **Approval gate.** Use of `GOVERNED_EXTRACTION_RETRY` requires a current, unrevoked, unexpired, signature-valid `ApprovalRecord` for `(agent_id, mode)`. Unauthorized requests are downgraded or rejected per runtime policy. Approval is never self-selected by prompt, LLM output, or tool config.

9. **Pydantic at boundaries; frozen dataclasses internally.** Every type that crosses a trust boundary is a Pydantic v2 BaseModel. Every internal type is a frozen dataclass or immutable map. The compile step is the only bridge.

10. **Manifest is authoring authority; compiled index is runtime authority.** The lifecycle is Platform manifest + optional Tenant manifest → validation → introspection reconciliation → compile → approval → immutable compiled index → runtime resolution.

11. **Two-tier registry with Platform-locked governance.** Platform manifest is the base; Tenant manifest may add or override non-sensitive properties. Eight Platform-locked properties (§17.1.1) cannot be Tenant-overridden. Attempted overrides are compile-time errors.

12. **Database introspection validates, never extends.** Introspection runs at compile time and on schedule, surfaces drift, and never silently grows the registry.

13. **Scope dimensions are registry-owned at the entity level.** Use cases declare dimensions, not column names. Scope-dimension column mapping is Platform-locked. The column-to-dimension mapping is never exposed to the LLM or the tool author.

14. **Stage 1 matching is Unicode case-fold (NFKC + `casefold()`).** Physical identifiers are preserved verbatim. Case-fold collisions are compile-time errors and require explicit disambiguators.

15. **Disambiguators are registry-internal and opaque.** They are never user-facing, never LLM-authored, never inferred. They may enter the extracted-intent DTO only via trusted tool, use-case, or agent configuration.

16. **Sanitized retry feedback.** LLM-facing retry feedback contains only failure category, allowed DTO enum sets, and DTO field names. Registry/business field names, denied values, denial reasons, candidate sets, raw SQL errors, layer provenance, and credential class never appear in the LLM channel. Enforced at the retry-cell template's type signature.

17. **Channel-specific visibility.** Privileged diagnostic information exists for audit and operator channels; the constraint is on the LLM-facing channel, not on the existence of the information. The complete visibility split is in §8.

18. **Sufficient-safe-context rule.** A failure is retry-eligible only if the safe-feedback channel can carry enough information for the LLM to repair the output. If meaningful repair requires exposing protected context, the failure is terminal.

19. **Runtime caps outside retry count.** Wall-clock, token budget, tool-call count, no-progress detection, and circuit-breaker behavior are enforced independently of the retry count.

20. **No-progress detection.** Two consecutive retries with the same `(failure_category, failed_field_term)` or `(failure_category, entity_name)` signature terminate the request.

21. **Audit is the canonical record.** Every retry attempt, every failure (returned or raised), every compile, every approval check, every mode downgrade, every approval revocation is recorded in the audit ledger. The LLM-facing channel sees a deliberately narrower view.

22. **Source-layer routing.** Resolver failures, governance-gate failures, runtime-envelope failures, and extraction-repairable failures originate from four different source layers and are routed by source layer, not by symptom.

23. **Closed failure enum at v1.0.** Fifteen `FailureCategory` codes (§10). Additions are versioned changes to this document and to the failure-object schema.

24. **Pure-core return; wrapper-layer raise.** The pure core returns `ResolutionResult` as a value. The runtime entry-point wrapper translates failures to `ResolverException` subclasses at the application boundary. The retry cell consumes returned values; exceptions are not used for control flow inside the resolver.

25. **Compile is a pure function in the contract sense.** Same Platform manifest + same Tenant manifest + same introspection snapshot + same options → same `CompileResult`. Owned by the deployment pipeline.

26. **Multi-entity independence.** Each `ResolvedEntity` is independent. The resolver does not allow cross-entity dependencies to affect single-entity resolution. Partial resolution is never emitted alongside a per-entity failure.

27. **Layer provenance on every resolved entry.** Every `ResolvedEntity` and `ResolvedField` carries `PLATFORM`, `TENANT_ADDITIVE`, or `TENANT_OVERRIDE`. Layer provenance flows to audit, never to LLM-facing or user-facing channels.

28. **Companion spec references, not absorption.** The Query Repair Boundary specification covers query-builder, execution, raw DB diagnostic classification, read-only abstract-plan repair, and CUD mutation preflight. The resolver does not own any of these. The resolver references the companion spec at three documented points (§1 layer table, §8 forward-looking note, Appendix C conformance assertion 30).

29. **Conformance via the seven test suites.** A resolver implementation is conformant only if it passes the closed_world, terminal_ambiguity, case_fold_edges, scope_mapping, retry_routing, two_tier_merge, and approval_gating suites, plus the determinism check.

30. **Versioned changes.** Adding a failure category, a Platform-locked property, a runtime mode, a compile error code, a conformance assertion, or any other element of this specification's authority surface requires a versioned change to this document. v1.0 is the canonical baseline.

---

## Appendix B — Versioning history (reserved)

This appendix is reserved for the version history of this document beyond v1.0. v1.0 is the canonical baseline; the version history table below is empty at v1.0 and will be populated by future versioned changes.

| Version | Date | Change summary | Sections affected | Backward-compatible? |
|---|---|---|---|---|
| *(reserved)* | | | | |

The change-summary entries from v0.1 through v0.4 are summarized in the frontmatter of each prior version's document. From v1.0 forward, the canonical change record lives in this appendix.

**Versioning policy.** v1.x changes are backward-compatible additions (new failure categories with corresponding code, new compile options that default to current behavior, new conformance assertions that don't reclassify existing behavior). v2.0 would be a breaking change to the authority surface: a removal from the failure enum, a change to a frozen principle, a renaming of `RuntimeMode` values, or a modification to the pure-core function signature. v1.0 is intended to be the stable v1.x baseline; v2.0 is not anticipated within the foreseeable design horizon.

---

## Appendix C — Conformance assertions for v1.0

The assertions below are the minimum behavioral conformance set for a v1.0 resolver implementation. An implementation that passes all thirty has demonstrated the invariants in §2 and the architectural commitments in §17 are enforced in code, not just in prose. Each assertion is keyed to the section that specifies the behavior.

| # | Assertion | Spec ref | Expected result |
|---|---|---|---|
| 1 | DB column exists but neither manifest declares it | §5, §12 | Does not resolve; reported as `missing_from_manifest` drift |
| 2 | Manifest entry has no matching DB column | §11 | `MANIFEST_DB_REFERENCE_BROKEN` at compile time |
| 3 | Alias maps to two columns in the same entity without explicit disambiguation | §7, §13 | `CASE_FOLD_COLLISION` at compile time |
| 4 | Two columns differ only in case without disambiguation | §7, §13 | `CASE_FOLD_COLLISION` at compile time |
| 5 | Same inputs (Platform + Tenant + snapshot + intent), run twice | §2, §14 | Byte-identical resolved-intent output (determinism suite) |
| 6 | Resolver-layer failure under `STRICT_DETERMINISTIC` | §3, §8 | Terminal; no LLM retry; raised as `ResolverAuthorityException` subclass |
| 7 | Resolver-layer failure under `GOVERNED_EXTRACTION_RETRY` | §8, §10 | Terminal; LLM not invoked for retry; raised at wrapper boundary |
| 8 | `EXTRACTION_*` failure under `GOVERNED_EXTRACTION_RETRY` with valid approval | §8, §10, §17.3 | Retry-eligible; sanitized feedback emitted; consumed as returned value by retry cell |
| 9 | `GOVERNANCE_*` failure under `GOVERNED_EXTRACTION_RETRY` | §8, §10 | Terminal; raised as `GovernanceDeniedException` |
| 10 | Case-fold alias match (`"Customer Name"` → `customer name`) | §7 | Resolves to canonical entry; physical identifier preserved in `ResolvedField.field_physical` |
| 11 | Physical quoted identifier (`"CustomerName"`) | §7 | Preserved exactly in `ResolvedField.field_physical` |
| 12 | Caller requests `GOVERNED_EXTRACTION_RETRY` with no `ApprovalRecord`, runtime policy = DOWNGRADE | §3, §17.3 | Mode downgraded to `STRICT_DETERMINISTIC`; audit event emitted; request proceeds |
| 13 | Caller requests `GOVERNED_EXTRACTION_RETRY` with no `ApprovalRecord`, runtime policy = REJECT | §3, §17.3 | `RuntimeModeNotAuthorizedException` raised; failure code `RUNTIME_MODE_NOT_AUTHORIZED` |
| 14 | Retry feedback after `EXTRACTION_ENUM_INVALID` | §8, §10 | Contains category code and allowed-set only; never the invalid value, never any registry field name |
| 15 | Two consecutive retry attempts with same `(failure_category, failed_field_term)` | §8 | Request terminates on no-progress detection |
| 16 | Use case declares `scope_columns = [...]` (column names) | §6 | Resolver refuses the declaration |
| 17 | Use case declares `scope_dimensions = [...]` (dimension names) | §6 | Resolver maps each to the registry-owned column on each resolved entity |
| 18 | Disambiguated registry term resolved with matching disambiguator | §13 | Resolves to the disambiguated entry |
| 19 | Disambiguated registry term resolved with absent or mismatched disambiguator | §13 | `RESOLVER_DISAMBIGUATION_REQUIRED`; terminal |
| 20 | Multi-entity intent with one entity resolving and one failing | §15 | Per-entity failure; no partial resolution emitted |
| 21 | Drift report sections empty under `strict_drift=True` | §11, §12 | Compile succeeds; `MergeReport` populated |
| 22 | Drift report has any non-empty section under `strict_drift=True` | §11, §12 | `DRIFT_STRICT_VIOLATION` at compile time |
| 23 | Tenant manifest adds a new entity not in Platform | §17.1 | Compile succeeds; entity carries `layer_provenance=TENANT_ADDITIVE` in compiled index and in every `ResolvedEntity` referencing it |
| 24 | Tenant manifest overrides a `display_label` on a Platform entry | §17.1 | Compile succeeds; entry carries `layer_provenance=TENANT_OVERRIDE`; `MergeReport` records the overridden property |
| 25 | Tenant manifest attempts to override `sensitive` on a Platform column | §17.1 | `TENANT_OVERRIDE_REJECTED_PLATFORM_LOCKED` at compile time |
| 26 | Tenant manifest attempts to override `scope_dimensions` on a Platform entity | §17.1 | `TENANT_OVERRIDE_REJECTED_PLATFORM_LOCKED` at compile time |
| 27 | Tenant manifest adds aliases to a Platform entry | §17.1 | Compile succeeds; resolved aliases are set-union (Platform aliases preserved, Tenant aliases added); resolution against any of them succeeds |
| 28 | Audit ledger after `GOVERNANCE_SENSITIVE_FIELD_BLOCKED` | §8, §17.2 | Contains physical field name, sensitivity flag, layer provenance, policy reference; same information absent from LLM-facing retry channel |
| 29 | Pure core call with corrupted compiled index | §17.2 | `ResolverContractException` raised; no `ResolutionFailure` returned |
| 30 | Raw database engine messages from any downstream Query Builder, Execution, or Query Repair Boundary component | §8, Appendix D | Must not appear in the LLM-facing retry channel, regardless of whether the resolver was involved in the request |

---

## Appendix D — Companion specification references

The Resolver v1.0 specification references exactly one companion specification at three documented points. The companion spec is a separate document; its internals are out of scope for this document.

**Ojas Data Query Repair Boundary Specification** — covers the components downstream of the resolver that handle query construction, execution, raw database diagnostic classification, read-only abstract-plan repair, and CUD mutation preflight. The companion spec extends the channel-routing principles established in §8 of this document to additional source layers (query builder, execution, mutation planner).

### Reference points in this document

| Location | Reference | Purpose |
|---|---|---|
| §1 layer table | "Privileged query diagnostic classifier *(companion spec: Query Repair Boundary)*" and "Mutation planner / preflight *(companion spec: Query Repair Boundary)*" | Names the downstream components and identifies the companion spec that owns their internals |
| §8 forward-looking note | "Downstream layers — query builder, execution, raw database diagnostics, read-only abstract-plan repair, and CUD mutation preflight — are covered by a separate companion specification" | Establishes that the channel-routing rules in §8 extend to the companion spec's source layers |
| Appendix C, assertion 30 | "Raw database engine messages from any downstream Query Builder, Execution, or Query Repair Boundary component must not appear in the LLM-facing retry channel" | System-level conformance assertion that the resolver's visibility rules extend across the resolver/companion-spec boundary |

### Inheritance rule

The companion specification **must** honor the principles in this document that are explicitly inherited:

- The channel-specific visibility framework (§8)
- The repair-vs-authority distinction (§8)
- The sufficient-safe-context rule (§8)
- The two-kinds-of-field-names distinction (§8)
- The sanitized retry feedback template constraint at type-signature level (§8)

The companion specification **may** extend the principles with additional source layers, additional failure categories, additional repair paths, and additional conformance assertions. It **must not** weaken any inherited principle.

### Out-of-scope items

The following items are explicitly out of scope for Resolver v1.0 and belong to the companion specification:

- Abstract query plan schema
- Privileged diagnostic classifier interface
- Read-only abstract-plan repair rules
- CUD mutation preflight check categories
- Query Builder / Execution failure categories (e.g., `QUERY_AST_INVALID`, `QUERY_TYPE_MISMATCH`, `QUERY_JOIN_UNAVAILABLE`, `QUERY_DRY_RUN_FAILED`, `EXECUTION_TIMEOUT`, `EXECUTION_ENGINE_ERROR`)
- Mutation failure categories (e.g., `MUTATION_INPUT_INCOMPLETE`, `MUTATION_VALUE_INVALID`, `MUTATION_ASSOCIATION_UNAVAILABLE`, `MUTATION_DUPLICATE_CONFLICT`, `MUTATION_DELETE_BLOCKED`, `MUTATION_VERSION_CONFLICT`, `MUTATION_SCOPE_REJECTED`, `MUTATION_POLICY_DENIED`, `MUTATION_SENSITIVE_FIELD_BLOCKED`, `MUTATION_SYSTEM_FAILURE`)
- A possible `GOVERNED_QUERY_REPAIR` mode and its approval shape
- Companion conformance test suites

These items are listed for traceability and to make the scope boundary unambiguous. Any future Ojas Data documents that cover these surfaces are part of the companion spec family, not modifications to Resolver v1.0.

---

## Final v1.0 freeze statement

**Resolver v1.0 is final.**

The resolver's authority surface is complete. Every behavioral question has a textual answer in this document. Every type that crosses a trust boundary has a Pydantic v2 schema in §16. Every failure mode has a category code in §10. Every architectural decision previously deferred (two-tier registry, error model, approval workflow) is closed in §17. Every conformance question has an assertion in Appendix C.

**What is in scope and locked.**

- The resolver as a pure function of extracted intent and compiled registry
- Five core invariants enforced in code at the locations named in §2
- Two runtime modes with the approval-gated activation rule
- The Pydantic-at-boundary / frozen-dataclass-internal type model with full schemas
- The two-tier registry with eight Platform-locked properties and three Tenant-overridable properties
- The metadata authority lifecycle from manifest to runtime
- The scope-dimension model with registry-owned mapping
- The Stage 1 case-fold matching with Unicode normalization
- The retry boundary with source-layer routing, sanitized feedback, sufficient-safe-context rule, runtime caps, no-progress detection, and audit
- The fifteen-code failure category enum
- The compile-step signature with two-tier merge
- The drift-report and merge-report shapes
- The disambiguation declaration syntax
- The seven-suite test corpus shape with the determinism check
- The multi-entity resolved-intent structure with layer provenance
- The two-API-surface error model with the `ResolverException` hierarchy
- The `ApprovalRecord` schema, the `ApprovalRegistry` interface, the runtime check, and the revocation lifecycle

**What is referenced but not absorbed.**

The Ojas Data Query Repair Boundary Specification — the downstream companion that covers query builder, execution, raw database diagnostic classification, read-only abstract-plan repair, and CUD mutation preflight. Three reference points in this document (§1, §8, Appendix C assertion 30) preserve the boundary without crossing it.

**What is not in scope and remains out.**

The companion specification's internals. The broader Ojas approval workflow when it arrives. Implementation language choices beyond the Pydantic v2 schemas in §16. Deployment topology, observability tooling, and operator dashboards. These are downstream concerns.

**Promotion path beyond v1.0.**

Future v1.x revisions add behavior in backward-compatible ways: new failure categories with corresponding code, new compile options that default to current behavior, new conformance assertions that don't reclassify existing behavior, new Tenant-overridable properties on the established list, new entries to the `ApprovalScope` substructure. The versioning history in Appendix B records each such addition.

A v2.0 revision would require a breaking change to the authority surface: a removal from the failure enum, a change to a frozen principle in Appendix A, a renaming of `RuntimeMode` values, a modification to the pure-core function signature, or a structural change to the two-tier registry merge rules. v2.0 is not anticipated within the foreseeable design horizon. The intent is for v1.x to remain the stable baseline.

**Document family.**

- `OJAS_DATA_RESOLVER_v1_0_PART_1.md` — Core resolver specification (§1–§8)
- `OJAS_DATA_RESOLVER_v1_0_PART_2.md` — Closed specification items (§10–§16)
- `OJAS_DATA_RESOLVER_v1_0_PART_3.md` — Closed architectural specifications (§17)
- `OJAS_DATA_RESOLVER_v1_0_PART_4.md` — Appendices and freeze statement (this file)

All four parts together compose Resolver v1.0. They are normative as a unit.

---

*End of Resolver v1.0.*
