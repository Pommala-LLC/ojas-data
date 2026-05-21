# Ojas Data Resolver Specification v1.0 — Part 2

**Version:** v1.0
**Status:** Final — complete resolver authority specification

**This is Part 2 of 4.** Sections 10 through 16 — closed specification items.

- Part 1: §1 Purpose and boundary, §2 Core invariants, §3 Runtime modes, §4 Type and contract model, §5 Metadata authority, §6 Scope enforcement, §7 Stage 1 matching, §8 Retry boundary
- Part 2 (this file): §10 Failure category discriminator, §11 Compile-step signature, §12 Drift-report shape, §13 Disambiguation syntax, §14 Test corpus shape, §15 Multi-entity resolved-intent structure, §16 Full Pydantic schemas
- Part 3: §17 — previously deferred sections now closed
- Part 4: Appendices A/B/C and freeze statement

§9 is reserved as a numbering placeholder so cross-references from prior versions remain stable.

---

## 10. Failure category discriminator

Every failure object emitted by the extraction layer, the resolver, a downstream governance gate, or the runtime envelope **must** carry a `failure_category` discriminator from the closed enumeration below. The enumeration is exhaustive at the v1.0 baseline; adding a new value is a versioned change to this document and to the failure-object schema.

The `source_layer` column names which component produces the failure. The `retry_eligible` column is the routing rule for `GOVERNED_EXTRACTION_RETRY` and is enforced in code at the boundary of the extraction-retry cell.

| Category code | Source layer | Description | Retry-eligible |
|---|---|---|---|
| `EXTRACTION_DTO_MALFORMED` | Extraction/DTO | Intent DTO failed Pydantic validation | Yes |
| `EXTRACTION_FIELD_MISSING` | Extraction/DTO | A required intent field is absent | Yes |
| `EXTRACTION_ENUM_INVALID` | Extraction/DTO | An enum-typed intent field has a value outside the allowed set | Yes |
| `EXTRACTION_UNDERSPECIFIED` | Extraction/DTO | The extraction is internally inconsistent or under-specified in a way a re-phrasing could fix | Yes |
| `RESOLVER_UNKNOWN_ENTITY` | Resolver | A term resolves to no registry entity | No |
| `RESOLVER_UNKNOWN_COLUMN` | Resolver | A term resolves to no registry column on a known entity | No |
| `RESOLVER_AMBIGUOUS` | Resolver | A term resolves to more than one registry candidate | No |
| `RESOLVER_ALIAS_UNRESOLVED` | Resolver | An alias was provided but does not appear in the case-fold index | No |
| `RESOLVER_DISAMBIGUATION_REQUIRED` | Resolver | A case-fold collision exists at runtime that the registry has not disambiguated, or the intent provided no disambiguator for a disambiguated entry | No |
| `GOVERNANCE_POLICY_DENIED` | Governance | The policy engine denied the request | No |
| `GOVERNANCE_SENSITIVE_FIELD_BLOCKED` | Governance | A sensitive-field block applies | No |
| `GOVERNANCE_SCOPE_MISSING` | Governance | A required scope dimension has no value at request time | No |
| `GOVERNANCE_CREDENTIAL_MISMATCH` | Governance | No credential class satisfies the resolved access requirements | No |
| `GOVERNANCE_ROW_SCOPE_FAILED` | Governance | Row-scope predicate construction failed | No |
| `RUNTIME_MODE_NOT_AUTHORIZED` | Runtime envelope | A caller requested `GOVERNED_EXTRACTION_RETRY` without a valid `ApprovalRecord`; runtime policy is set to reject rather than downgrade | No |

The retry cell **must** consume only failures with `retry_eligible: Yes`. Any failure with `retry_eligible: No` **must** be propagated terminally to the caller and to the audit ledger, regardless of runtime mode.

### Sanitized feedback rule per category

The retry-cell template **must** emit the category code and, where applicable, the allowed-set of DTO enum values. It **must not** emit the field name (registry/business), the denied value, the registry candidates, or any reason text. The complete failure record — with field names, values, candidate sets, reasons, and layer provenance — goes to the audit ledger and is not visible to the LLM. This rule is enforced by the retry-cell template function's type signature, which accepts only DTO-typed inputs (see §8 and §17.2).

### Enum closure rule

The v1.0 enumeration above is closed at the v1.0 baseline. Implementations **must not** emit a `failure_category` value outside this enumeration. Any future addition (for example, when downstream layers covered by the Ojas Data Query Repair Boundary Specification become resolver-observable in some form) requires a versioned change to this document and a coordinated update to the failure-object schema, the retry-cell template, and the audit ledger.

---

## 11. Compile-step signature

The compile step is the boundary between the Pydantic manifests and the frozen-dataclass compiled index. It is a pure function in the contract sense: given the same manifests and the same introspection snapshot, it **must** produce the same compiled index or the same compile-error set. It is owned by the deployment pipeline, not by the runtime resolver.

### Signature

```
compile(
    platform_manifest: PlatformRegistryManifest,
    tenant_manifest: TenantRegistryManifest | None,
    introspection: IntrospectionSnapshot,
    options: CompileOptions
) -> CompileResult
```

**Inputs.**

- `platform_manifest: PlatformRegistryManifest` — the Pydantic-validated Platform manifest. Always required.
- `tenant_manifest: TenantRegistryManifest | None` — the Pydantic-validated Tenant manifest. Optional. When `None`, the compiled index reflects Platform only.
- `introspection: IntrospectionSnapshot` — a captured snapshot of the live database schema at the time of compile. Treated as data, not as a live connection. The compile step does not query the database itself; it consumes a snapshot produced by the introspection step.
- `options: CompileOptions` — a small bundle of compile flags. v1.0 names three: `strict_drift` (default `True`; drift is treated as compile error rather than warning), `disambiguation_required` (default `True`; case-fold collisions must be disambiguated explicitly, not silently broken), and `tenant_override_audit` (default `True`; every Tenant override of a Platform entry produces an audit event in the compile result).

**Output.**

`CompileResult` is one of two shapes, discriminated by `status`:

- `status: COMPILED` — carries a `CompiledRegistryIndex` (frozen dataclass + immutable maps; the resolver's runtime authority), a `DriftReport` (see §12), and a `MergeReport` (see §17.1).
- `status: COMPILE_FAILED` — carries an ordered list of `CompileError` objects, a `DriftReport`, and a partial `MergeReport`. No compiled index is produced.

**Merge semantics.**

When both manifests are present, the compile step merges them according to the rules in §17.1. The merge is deterministic and produces a `MergeReport` recording, for every resolved entry, which layer contributed it (`PLATFORM`, `TENANT_ADDITIVE`, or `TENANT_OVERRIDE`). Layer provenance is carried into the compiled index and emitted on every resolved field at runtime (§15).

**Properties.**

- The compile step **must** be deterministic: same `platform_manifest` + same `tenant_manifest` + same `introspection` + same `options` → same `CompileResult`.
- The compile step **must not** mutate its inputs.
- The compile step **must not** have side effects observable outside its return value, with the single exception of structured logging.
- A `CompiledRegistryIndex` once produced **must** be immutable for its lifetime. Loading a new registry version produces a new index; the old one is not modified.

**Failure modes** the compile step emits:

| Compile error | Trigger |
|---|---|
| `MANIFEST_VALIDATION_FAILED` | Pydantic validation of one of the manifests failed |
| `MANIFEST_DB_REFERENCE_BROKEN` | A manifest references an entity or column not present in the introspection snapshot |
| `CASE_FOLD_COLLISION` | Two manifest entries (within or across layers) fold to the same canonical form with no explicit disambiguation |
| `SCOPE_DIMENSION_UNREACHABLE` | A declared scope dimension points to a column not present on the entity |
| `TENANT_OVERRIDE_REJECTED_PLATFORM_LOCKED` | A Tenant manifest attempts to override a Platform-locked property (see §17.1) |
| `DRIFT_STRICT_VIOLATION` | `strict_drift=True` and the drift report contains any non-empty section |

### Audit emission

Beyond the structured `CompileResult` and `MergeReport`, the compile step **must** emit an audit event recording: the Platform manifest version, the Tenant manifest version (or `null`), the introspection snapshot identifier, the compile options, the compile outcome, and the integrity hash of the produced compiled index (when compile succeeds). This audit event is the canonical record of how a runtime compiled index came to exist.

---

## 12. Drift-report shape

The drift report is produced by the compile step (§11) on every invocation, regardless of whether the compile succeeded. It is the canonical record of how the merged manifest and the live database differ. It is consumed by registry authors of both layers, by the manifest-approval workflow, and by the audit ledger.

### Structure

```
DriftReport:
  snapshot_id: str
  snapshot_taken_at: datetime
  platform_manifest_version: str
  tenant_manifest_version: str | None
  sections:
    missing_from_db: list[ManifestRef]
    missing_from_manifest: list[DbRef]
    type_mismatches: list[TypeMismatch]
    constraint_changes: list[ConstraintChange]
    nullable_changes: list[NullableChange]
```

Each section is independently populated. An empty section means no drift of that kind. A non-empty section under `strict_drift=True` is a compile error; under `strict_drift=False` it is a warning surfaced to the registry author(s).

**`missing_from_db`** lists manifest entries (entities or columns) that the introspection snapshot does not contain. Each entry carries its source layer (`PLATFORM` or `TENANT`). These are broken references; the manifest cannot compile against this snapshot.

**`missing_from_manifest`** lists database entities or columns that exist in the snapshot but have no entry in either Platform or Tenant manifest. The resolver treats these as nonexistent regardless of compile mode. The list is surfaced so the registry authors can decide whether to add the entries to one of the manifests or leave them out deliberately.

**`type_mismatches`** lists manifest entries whose declared type does not match the snapshot's type for the same identifier. Each entry names the manifest type, the snapshot type, the identifier, and the source layer of the manifest entry.

**`constraint_changes`** lists differences in primary-key, foreign-key, unique, or check constraints between the merged manifest and the snapshot.

**`nullable_changes`** lists columns whose nullability differs between manifest and snapshot.

### Authority

The drift report is informational, never authoritative. It **must not** be consulted by the resolver at request time. The compile step is the only consumer of the drift report; the resolver consumes only the compiled index.

---

## 13. Disambiguation declaration syntax

When two manifest entries case-fold to the same canonical form (§7), the manifest **must** declare an explicit disambiguation or the compile fails (§11). The disambiguation is registry-owned and is recorded in the compiled index.

### Declaration form

Disambiguation is declared on the colliding entries themselves. Each entry that participates in a collision **must** declare a `disambiguator` field whose value distinguishes it from its collision peers. The `disambiguator` value is opaque to the resolver — it is used only as a tiebreaker key — but it **must** be unique within the collision group.

```
entity: customer
  columns:
    - canonical: account_number
      aliases: ["acct no"]
      disambiguator: "long_form"
    - canonical: acct_no
      aliases: ["acct no"]
      disambiguator: "short_form"
```

With both entries declaring distinct disambiguators, the manifest compiles. The case-fold index records the folded form `"acct no"` as ambiguous-but-disambiguated; resolution of the term `"acct no"` from an extracted intent **must** then require the intent to carry the disambiguator value.

### Intent-side reference

When a registry term is disambiguated, the extracted-intent DTO **must** carry the disambiguator alongside the term:

```
extracted_intent:
  field:
    term: "acct no"
    disambiguator: "long_form"
```

The resolver matches the folded term *and* the disambiguator. If the disambiguator is absent or does not match any peer in the collision group, the resolution failure is `RESOLVER_DISAMBIGUATION_REQUIRED` (§10), which is terminal.

### LLM cannot author the disambiguator

The disambiguator is not a display label, not an alias, and not user-facing. It is a registry-internal tag. The extraction layer **may** carry a disambiguator in the DTO only if it was injected from trusted tool configuration, use-case declaration, or agent manifest — not generated by the LLM. The LLM-facing schema for the extracted-intent DTO **must not** present the disambiguator as a free-text field. Typical implementations either omit the disambiguator from the LLM-facing prompt schema entirely and have the calling layer attach it post-extraction, or present a small fixed enumeration of disambiguator values determined by the tool/use-case configuration.

### Scoping

Disambiguators **must** be unique within a collision group, not globally. Two unrelated entities may both use `"short_form"` as a disambiguator for unrelated case-fold collisions. The compile step verifies uniqueness per group, not across the manifest.

### Cross-layer collisions

When a Platform manifest entry and a Tenant manifest entry case-fold to the same canonical form, the collision is handled by the same disambiguation mechanism. The Platform entry's disambiguator is Platform-authored; the Tenant entry's disambiguator is Tenant-authored. The compile step verifies that the two disambiguators are distinct within the collision group. If they collide, the compile error names both source layers and the duplicate value.

---

## 14. Test corpus shape

A v1.0 resolver implementation is conformant only if it passes a corpus that exercises every invariant from §2, every failure category from §10, every runtime mode from §3, the case-fold and scope behaviors from §6 and §7, and the two-tier merge behaviors from §17.1. The corpus is not specified at the fixture level in this document — that belongs to the implementation pass — but the corpus *shape* is.

### Corpus organization

The corpus **must** be partitioned into seven suites, each with its own pass/fail criteria:

| Suite | Purpose | Pass criterion |
|---|---|---|
| `closed_world` | Verifies the closed-world invariant | Every reference outside the registry produces a terminal failure of the correct category; no silent extension |
| `terminal_ambiguity` | Verifies the terminal-ambiguity invariant | Every multi-candidate match produces `RESOLVER_AMBIGUOUS`; no silent selection |
| `case_fold_edges` | Verifies Stage 1 matching against Unicode edge cases | Every fixture's expected fold result matches the resolver's actual fold; collisions trigger compile errors |
| `scope_mapping` | Verifies entity-level scope-dimension mapping | Every fixture's expected `resolved_scope` matches the resolver's output exactly |
| `retry_routing` | Verifies the source-layer-based retry routing | Every fixture's expected `retry_eligible` value matches the resolver's actual routing decision under `GOVERNED_EXTRACTION_RETRY` |
| `two_tier_merge` | Verifies the Platform + Tenant merge rules | Every fixture's expected `MergeReport` and resolved layer provenance match the resolver's output exactly |
| `approval_gating` | Verifies the runtime mode authorization rule | Every fixture's expected `ModeAuthorizationResult` matches the runtime check's actual decision |

### Fixture form

Every fixture **must** carry:

- A Platform manifest (or a reference to a shared one)
- An optional Tenant manifest (or a reference to a shared one)
- An introspection snapshot (or a reference to a shared one)
- An extracted-intent DTO
- The runtime mode under test
- The `ApprovalRecord` set, if relevant
- The expected outcome: either a resolved-intent DTO or a typed failure with its category code

### Determinism check

The corpus **must** include a determinism suite that runs every other suite twice with identical inputs and asserts byte-identical outputs. This suite is the conformance check for the deterministic-authority invariant (§2). A resolver implementation that produces different outputs on a re-run is non-conformant regardless of how many other suites it passes.

### Coverage requirement

Every category code in §10 **must** appear in at least one fixture as an expected outcome. Every compile-error code in §11 **must** appear in at least one compile-error fixture. Every drift section in §12 **must** appear non-empty in at least one drift fixture. Every entry in the Platform-locked property list (§17.1) **must** appear as a rejected Tenant override in at least one fixture.

---

## 15. Multi-entity resolved-intent structure

A single extracted intent often spans more than one entity. The resolved-intent DTO **must** represent multi-entity resolution as a collection of independent per-entity resolutions, not as a single flat structure.

### Structure

```
ResolvedIntent:
  intent_id: str
  registry_version: str
  mode: RuntimeMode
  entities: list[ResolvedEntity]

ResolvedEntity:
  entity_canonical: str
  entity_physical: str
  layer_provenance: LayerProvenance     # PLATFORM | TENANT_ADDITIVE | TENANT_OVERRIDE
  fields: list[ResolvedField]
  scope: dict[DimensionName, PhysicalColumnName]

ResolvedField:
  field_canonical: str
  field_physical: str
  role: FieldRole
  layer_provenance: LayerProvenance
```

The order of `entities` in the list reflects the order of mention in the extracted intent. It is preserved as metadata for downstream layers but **must not** be interpreted by the resolver as a join order or precedence. Join ordering is the query builder's responsibility.

### Layer provenance

Every `ResolvedEntity` and every `ResolvedField` **must** carry a `layer_provenance` value indicating which manifest layer authored the entry the resolution matched against:

- `PLATFORM` — the entry exists in the Platform manifest and was not overridden by Tenant
- `TENANT_ADDITIVE` — the entry exists only in the Tenant manifest (no Platform counterpart)
- `TENANT_OVERRIDE` — the entry exists in the Platform manifest and was overridden by Tenant (non-sensitive properties only; see §17.1)

Layer provenance is consumed by the audit ledger and may be consumed by downstream governance gates. It **must not** appear in LLM-facing retry feedback or in user-facing messages, per the visibility-split rule in §8.

### Per-entity independence

Each `ResolvedEntity` is the output of an independent application of the resolver's per-entity logic against the same compiled registry. The resolver **must not** allow cross-entity dependencies to affect the resolution of any single entity. If one entity fails to resolve, the resolver emits a typed failure naming that entity; it **must not** partially resolve other entities and emit a mixed result.

### Worked example

A user asks: *"Show recent orders and the email of the customer who placed each one."*

The extracted intent references two entities (`customer_order`, `customer`) and four fields (`customer_order.created_at`, `customer.email`, plus the join keys `customer.id` / `customer_order.customer_id`).

The resolved intent is:

```
ResolvedIntent:
  intent_id: "intent-001"
  registry_version: "registry-v17"
  mode: STRICT_DETERMINISTIC
  entities:
    - ResolvedEntity:
        entity_canonical: "customer_order"
        entity_physical: "CustomerOrder"
        layer_provenance: PLATFORM
        fields:
          - field_canonical: "created_at"
            field_physical: "CreatedAt"
            role: ORDER
            layer_provenance: PLATFORM
          - field_canonical: "customer_id"
            field_physical: "CustomerId"
            role: JOIN_KEY
            layer_provenance: PLATFORM
        scope:
          tenant: "tenant_ref"
          region: "ord_region"
    - ResolvedEntity:
        entity_canonical: "customer"
        entity_physical: "Customer"
        layer_provenance: PLATFORM
        fields:
          - field_canonical: "email"
            field_physical: "Email"
            role: PROJECT
            layer_provenance: TENANT_OVERRIDE
          - field_canonical: "id"
            field_physical: "Id"
            role: JOIN_KEY
            layer_provenance: PLATFORM
        scope:
          tenant: "tenant_id"
          region: "region"
```

The resolver has emitted two independent `ResolvedEntity` objects. Each carries its own scope mapping and its own layer provenance. The `customer.email` field came from a non-sensitive Tenant override (perhaps the Tenant supplied a custom display label or an additional alias); the underlying physical column and the entity declaration remain Platform-owned.

### Failure under multi-entity intent

If the LLM extracts a field that exists on one entity but not the other, the failure is per-entity. The resolver emits `RESOLVER_UNKNOWN_COLUMN` naming the entity it attempted resolution against. There is no fallback to the other entity, no "best match" across entities, and no partial resolution returned alongside the failure.

---

## 16. Pydantic boundary schemas

This section specifies the full Pydantic v2 schemas for every type that crosses a trust boundary. v1.0 is the implementation contract; new boundary types require a versioned change.

### Conventions

- All boundary types are Pydantic v2 `BaseModel` subclasses with `model_config = ConfigDict(extra='forbid', frozen=True)` unless otherwise noted.
- `str` identifiers used as keys (entity canonicals, alias terms, dimension names) are normalized at validation time per §7's NFKC + `casefold()` rule for case-insensitive forms; physical identifiers are preserved as-is.
- `datetime` fields are timezone-aware UTC; `tzinfo=timezone.utc` enforced by validator.
- Closed enumerations are Python `StrEnum` (Pydantic v2 native).

### Enumerations

```python
class RuntimeMode(StrEnum):
    STRICT_DETERMINISTIC = "STRICT_DETERMINISTIC"
    GOVERNED_EXTRACTION_RETRY = "GOVERNED_EXTRACTION_RETRY"


class FieldRole(StrEnum):
    PROJECT = "PROJECT"
    FILTER = "FILTER"
    GROUP = "GROUP"
    ORDER = "ORDER"
    JOIN_KEY = "JOIN_KEY"


class LayerProvenance(StrEnum):
    PLATFORM = "PLATFORM"
    TENANT_ADDITIVE = "TENANT_ADDITIVE"
    TENANT_OVERRIDE = "TENANT_OVERRIDE"


class FailureCategory(StrEnum):
    # Extraction
    EXTRACTION_DTO_MALFORMED = "EXTRACTION_DTO_MALFORMED"
    EXTRACTION_FIELD_MISSING = "EXTRACTION_FIELD_MISSING"
    EXTRACTION_ENUM_INVALID = "EXTRACTION_ENUM_INVALID"
    EXTRACTION_UNDERSPECIFIED = "EXTRACTION_UNDERSPECIFIED"
    # Resolver
    RESOLVER_UNKNOWN_ENTITY = "RESOLVER_UNKNOWN_ENTITY"
    RESOLVER_UNKNOWN_COLUMN = "RESOLVER_UNKNOWN_COLUMN"
    RESOLVER_AMBIGUOUS = "RESOLVER_AMBIGUOUS"
    RESOLVER_ALIAS_UNRESOLVED = "RESOLVER_ALIAS_UNRESOLVED"
    RESOLVER_DISAMBIGUATION_REQUIRED = "RESOLVER_DISAMBIGUATION_REQUIRED"
    # Governance
    GOVERNANCE_POLICY_DENIED = "GOVERNANCE_POLICY_DENIED"
    GOVERNANCE_SENSITIVE_FIELD_BLOCKED = "GOVERNANCE_SENSITIVE_FIELD_BLOCKED"
    GOVERNANCE_SCOPE_MISSING = "GOVERNANCE_SCOPE_MISSING"
    GOVERNANCE_CREDENTIAL_MISMATCH = "GOVERNANCE_CREDENTIAL_MISMATCH"
    GOVERNANCE_ROW_SCOPE_FAILED = "GOVERNANCE_ROW_SCOPE_FAILED"
    # Runtime envelope
    RUNTIME_MODE_NOT_AUTHORIZED = "RUNTIME_MODE_NOT_AUTHORIZED"


class SourceLayer(StrEnum):
    EXTRACTION = "EXTRACTION"
    RESOLVER = "RESOLVER"
    GOVERNANCE = "GOVERNANCE"
    RUNTIME = "RUNTIME"


class ColumnType(StrEnum):
    STRING = "STRING"
    TEXT = "TEXT"
    INTEGER = "INTEGER"
    BIGINT = "BIGINT"
    DECIMAL = "DECIMAL"
    FLOAT = "FLOAT"
    BOOLEAN = "BOOLEAN"
    DATE = "DATE"
    TIMESTAMP = "TIMESTAMP"
    UUID = "UUID"
    JSON = "JSON"
    BINARY = "BINARY"


class CompileStatus(StrEnum):
    COMPILED = "COMPILED"
    COMPILE_FAILED = "COMPILE_FAILED"


class ModeAuthorizationResult(StrEnum):
    AUTHORIZED = "AUTHORIZED"
    DOWNGRADED_TO_STRICT_DETERMINISTIC = "DOWNGRADED_TO_STRICT_DETERMINISTIC"
    REJECTED = "REJECTED"
```

### Registry manifest schemas

```python
class ScopeDimensionDeclaration(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    dimension_name: str                          # e.g., "tenant", "region"
    physical_column: str                         # the column on this entity that carries the dimension


class ManifestColumn(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    canonical: str
    physical_name: str
    type: ColumnType
    nullable: bool
    aliases: list[str] = Field(default_factory=list)
    sensitive: bool = False                      # Platform-locked when set in Platform manifest
    access_class: str | None = None              # Platform-locked when set in Platform manifest
    participates_in_dimension: str | None = None # field-level scope refinement, references entity-level dimension
    disambiguator: str | None = None             # required if entry is in a case-fold collision group
    display_label: str | None = None             # human-facing label; non-sensitive, Tenant-overridable


class ManifestEntity(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    canonical: str
    physical_name: str
    aliases: list[str] = Field(default_factory=list)
    columns: list[ManifestColumn]
    scope_dimensions: list[ScopeDimensionDeclaration] = Field(default_factory=list)
    access_class: str                            # Platform-locked when set in Platform manifest
    disambiguator: str | None = None
    display_label: str | None = None             # non-sensitive, Tenant-overridable


class PlatformRegistryManifest(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    manifest_kind: Literal["PLATFORM"] = "PLATFORM"
    version: str
    entities: list[ManifestEntity]
    scope_dimension_catalog: list[str] = Field(default_factory=list)  # canonical dimension names
    signed_by: str
    signed_at: datetime


class TenantRegistryManifest(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    manifest_kind: Literal["TENANT"] = "TENANT"
    version: str
    tenant_id: str
    entities: list[ManifestEntity]
    scope_dimension_additions: list[str] = Field(default_factory=list)
    approved_by: str
    approved_at: datetime
```

### Extracted-intent DTO

```python
class ExtractedEntityRef(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    term: str
    disambiguator: str | None = None             # see §13; never LLM-authored


class ExtractedFieldRef(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    entity_term: str
    field_term: str
    role: FieldRole
    disambiguator: str | None = None


class ExtractedIntent(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    intent_id: str
    source_query: str
    requested_mode: RuntimeMode
    entities: list[ExtractedEntityRef]
    fields: list[ExtractedFieldRef]
    agent_id: str                                # consumed by the approval check (§3, §17.3)
```

### Resolved-intent DTO

```python
class ResolvedField(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    field_canonical: str
    field_physical: str
    role: FieldRole
    layer_provenance: LayerProvenance


class ResolvedEntity(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    entity_canonical: str
    entity_physical: str
    layer_provenance: LayerProvenance
    fields: list[ResolvedField]
    scope: dict[str, str]                         # dimension_name -> physical_column_name


class ResolvedIntent(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    intent_id: str
    registry_version: str
    mode: RuntimeMode
    entities: list[ResolvedEntity]
```

### Resolution-failure DTOs

```python
class FailureContext(BaseModel):
    """
    Full failure context for audit ledger.
    NEVER serialized to the LLM-facing retry channel.
    """
    model_config = ConfigDict(extra='forbid', frozen=True)
    failed_entity_term: str | None = None
    failed_field_term: str | None = None
    candidate_set: list[str] = Field(default_factory=list)      # registry candidates (audit only)
    layer_provenance_observed: LayerProvenance | None = None
    governance_reason: str | None = None                         # audit only
    credential_class_required: str | None = None                 # audit only


class ResolutionFailure(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    failure_id: str
    failure_category: FailureCategory
    source_layer: SourceLayer
    retry_eligible: bool                                         # derived from category
    intent_id: str
    registry_version: str
    occurred_at: datetime
    context: FailureContext                                      # never reaches LLM channel
```

The `ResolutionFailure` object is the full record. The retry-cell template function (see §8 and §17.2) takes `FailureCategory` and DTO-level inputs only — never `FailureContext`. This is the type-level enforcement of the sanitized-feedback rule.

### Authoring-validation error

```python
class AuthoringValidationError(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    error_code: str                                              # MANIFEST_VALIDATION_FAILED, etc.
    manifest_kind: Literal["PLATFORM", "TENANT"]
    manifest_version: str
    path: str                                                    # JSONPath-style locator
    message: str
```

### ApprovalRecord

(Full schema in §17.3.) Referenced here for completeness as a boundary type.

### JSON Schema generation

All boundary types **must** be able to emit JSON Schema via Pydantic v2's `model_json_schema()` method. Implementations **should** publish the JSON Schemas as part of the deployment artifact set so that external consumers (manifest authors, audit consumers, LLM extraction prompt builders) can validate against the same contract the resolver enforces.

**Part 2 ends here. Part 3 begins with §17 (previously deferred sections now closed).**
