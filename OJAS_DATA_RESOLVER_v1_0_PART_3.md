# Ojas Data Resolver Specification v1.0 — Part 3

**Version:** v1.0
**Status:** Final — complete resolver authority specification

**This is Part 3 of 4.** Section 17 — the three previously deferred architectural sections, now closed at design depth.

- Part 1: §1 Purpose and boundary, §2 Core invariants, §3 Runtime modes, §4 Type and contract model, §5 Metadata authority, §6 Scope enforcement, §7 Stage 1 matching, §8 Retry boundary
- Part 2: §10 Failure category discriminator, §11 Compile-step signature, §12 Drift-report shape, §13 Disambiguation syntax, §14 Test corpus shape, §15 Multi-entity resolved-intent structure, §16 Full Pydantic schemas
- Part 3 (this file): §17.1 Two-tier registry, §17.2 Error model, §17.3 Approval workflow
- Part 4: Appendices A/B/C and freeze statement

---

## 17. Closed architectural specifications

The three sections that v0.3 and v0.4 deferred — two-tier registry, error model, and approval workflow — are closed here. Each subsection is a complete design specification at v1.0; future revisions are versioned changes to this document.

---

### 17.1 Two-tier registry

The compiled registry is constructed by merging two manifests: a Platform manifest authored by Platform owners, and an optional Tenant manifest authored by Tenant owners. The merge happens at compile time (§11) and produces a single immutable compiled index that the resolver consults at runtime. The Tenant tier may extend the Platform tier and may override certain non-sensitive properties; it cannot override Platform-locked properties.

#### 17.1.1 Platform-locked property list

The following manifest properties are Platform-locked. When set in the Platform manifest, a Tenant manifest **must not** override them. Attempting to do so is a compile-time error `TENANT_OVERRIDE_REJECTED_PLATFORM_LOCKED`.

| Property | Lives on | Why Platform-locked |
|---|---|---|
| `sensitive: bool` | `ManifestColumn` | Sensitivity classification is a governance-load-bearing decision; a Tenant changing it would shift the policy surface |
| `access_class` | `ManifestEntity`, `ManifestColumn` | Access class is consumed by the credential selector; a Tenant changing it would shift the credential surface |
| `scope_dimensions[].physical_column` | `ManifestEntity` | The column carrying a Platform-declared scope dimension is the load-bearing path Lock 2 closes (registry-owned, never use-case-selected) |
| `participates_in_dimension` | `ManifestColumn` | Field-level scope refinement points back to a Platform-declared dimension; a Tenant redirecting it would break dimension-to-column authority |
| `disambiguator` (when set in Platform) | `ManifestEntity`, `ManifestColumn` | Platform-declared disambiguators resolve Platform-internal case-fold collisions; a Tenant overriding one could cause cross-layer ambiguity |
| `physical_name` | `ManifestEntity`, `ManifestColumn` | The physical database identifier is what executes; a Tenant rewriting it would mean a different table or column was queried than the Platform manifest declared |
| `type` | `ManifestColumn` | Column type drives downstream validation and credential selection; a Tenant changing it would create a type-system inconsistency |
| `nullable` | `ManifestColumn` | Nullability is a schema constraint; a Tenant changing it would create a constraint inconsistency |

The Platform-locked set is exhaustive at v1.0. Any future property added to the manifest schema **must** be classified as Platform-locked or Tenant-overridable as part of the versioned change that adds it.

#### 17.1.2 Tenant-overridable property list

The following properties may be overridden by Tenant on entries that exist in Platform. These are display-and-vocabulary surfaces — they affect how the registry is *named* and *described*, not how it is *enforced*.

| Property | Lives on | Override semantics |
|---|---|---|
| `display_label` | `ManifestEntity`, `ManifestColumn` | Tenant value replaces Platform value in user-facing surfaces |
| `aliases` | `ManifestEntity`, `ManifestColumn` | Tenant aliases are *additive* to Platform aliases (set-union), not replacing. A Tenant cannot remove a Platform alias. |
| `disambiguator` (when not set in Platform) | `ManifestEntity`, `ManifestColumn` | Tenant may set a disambiguator on a Platform entry that did not have one, provided it is required by a cross-layer collision (§13) |

The list is exhaustive at v1.0. Tenant attempts to set properties not on this list — or properties on this list when the Platform entry has them in a Platform-locked form — produce `TENANT_OVERRIDE_REJECTED_PLATFORM_LOCKED`.

#### 17.1.3 Tenant-additive entries

A Tenant manifest may declare entirely new entities, columns, aliases, and scope dimensions that do not exist in the Platform manifest. These are *additive*, not overrides, and are not subject to the Platform-locked list — the Tenant owns the entry entirely. The Tenant author **must** set all required fields on the new entry (including `physical_name`, `access_class`, `sensitive`, etc.).

When a Tenant declares a scope dimension on a Tenant-additive entity, the dimension declaration is Tenant-owned. When a Tenant declares a scope dimension on a Platform entity, this is treated as an attempted override of the Platform `scope_dimensions` and is rejected per §17.1.1.

#### 17.1.4 Merge algorithm

The compile step's merge proceeds entity by entity. For each entity in the union of Platform and Tenant manifests:

```
merge_entity(platform_entity, tenant_entity):

    if platform_entity is None and tenant_entity is not None:
        # Tenant-additive entity
        validate_all_required_fields(tenant_entity)
        emit MergeReport entry: TENANT_ADDITIVE, source=Tenant
        return tenant_entity with layer_provenance=TENANT_ADDITIVE

    if platform_entity is not None and tenant_entity is None:
        # Platform-only entity
        emit MergeReport entry: PLATFORM, source=Platform
        return platform_entity with layer_provenance=PLATFORM

    if platform_entity is not None and tenant_entity is not None:
        # Platform entry with Tenant override; check each property
        for property in tenant_entity.properties_set:
            if property in PLATFORM_LOCKED_LIST:
                if property is also set in platform_entity:
                    raise CompileError TENANT_OVERRIDE_REJECTED_PLATFORM_LOCKED
                else:
                    # Tenant is setting a Platform-locked property that
                    # Platform did not set; this is allowed only when the
                    # Tenant entry is otherwise Tenant-additive on the
                    # specific property (see §17.1.1 disambiguator rule)
                    apply_tenant_locked_property_rule(property)
            elif property in TENANT_OVERRIDABLE_LIST:
                apply_override(platform_entity, tenant_entity, property)
            else:
                raise CompileError TENANT_OVERRIDE_REJECTED_PLATFORM_LOCKED

        emit MergeReport entry: TENANT_OVERRIDE per overridden property
        return merged_entity with layer_provenance=TENANT_OVERRIDE
```

The merge is deterministic: the same Platform manifest plus the same Tenant manifest produces the same merged compiled index every time.

Column-level merge follows the same logic. The `aliases` property is a special case: union, not replacement.

#### 17.1.5 Merge report

The merge step emits a `MergeReport` carried in the `CompileResult` (§11):

```python
class MergeReport(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    platform_manifest_version: str
    tenant_manifest_version: str | None
    entries: list[MergeEntry]


class MergeEntry(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    entity_canonical: str
    column_canonical: str | None
    layer_provenance: LayerProvenance
    overridden_properties: list[str]   # populated when layer_provenance=TENANT_OVERRIDE
```

The `MergeReport` is consumed by the audit ledger and by the manifest-approval workflow. It is informational at runtime — the resolver consults only the compiled index, which already carries `layer_provenance` per entry — but the merge report is the canonical record of *which decisions were made* during compile.

#### 17.1.6 Cross-layer case-fold collisions

When a Platform entry and a Tenant-additive entry case-fold to the same canonical form (§7), the compile step **must** apply the same disambiguation rule as for within-layer collisions (§13). The Platform entry's disambiguator (if set) is Platform-authored; the Tenant entry's disambiguator is Tenant-authored. The two disambiguators **must** be distinct within the collision group. If the Platform entry has no disambiguator (because the collision did not exist within Platform alone) and the Tenant entry case-folds against it, the Tenant manifest **must** set a disambiguator on its own entry, and the compile step **must** treat the Platform entry as implicitly disambiguated by a Platform-reserved sentinel value. The sentinel value is documented in the implementation but is opaque to the resolver and to LLM-facing channels (§13).

#### 17.1.7 Single-manifest case

When `tenant_manifest` is `None`, the compile step proceeds with the Platform manifest alone. The `MergeReport` carries `tenant_manifest_version: None` and contains one entry per Platform entry with `layer_provenance=PLATFORM`. This case **must** be a first-class supported configuration — many deployments will have no Tenant tier.

---

### 17.2 Error model

The resolver exposes two API surfaces (§1). The error model is layered to match: returned-value semantics at the pure core boundary, exception semantics at the runtime entry-point wrapper.

#### 17.2.1 The pure-core boundary

The resolver's pure core function has the signature:

```python
def resolve(
    extracted_intent: ExtractedIntent,
    compiled_index: CompiledRegistryIndex,
) -> ResolutionResult:
    ...
```

where:

```python
ResolutionResult = ResolvedIntent | ResolutionFailure
```

The pure core **must** return a `ResolvedIntent` on success and a `ResolutionFailure` on any modeled failure. It **must not** raise exceptions for any condition described by the failure-category enum (§10). The only exceptions the pure core may raise are programmer-error conditions: input that is not a `ResolvedIntent` Pydantic instance, a compiled-index argument that has been corrupted or partially mutated, or other contract violations.

This is the layer the test corpus (§14) exercises. Every failure category in §10 must be observable as a returned `ResolutionFailure` value, not as a caught exception. This is what makes the determinism suite possible — exceptions break referential transparency.

#### 17.2.2 The runtime entry-point wrapper

The runtime entry-point wrapper has the signature:

```python
def resolve_request(
    extracted_intent: ExtractedIntent,
    compiled_index: CompiledRegistryIndex,
    approval_registry: ApprovalRegistry,
    runtime_policy: RuntimePolicy,
    now: datetime,
) -> ResolvedIntent:
    ...
```

The wrapper:

1. Calls `check_mode_authorization` (§3, §17.3) against the `requested_mode` in the intent
2. Applies the result: `AUTHORIZED` proceeds; `DOWNGRADED_TO_STRICT_DETERMINISTIC` rewrites the intent's mode and proceeds; `REJECTED` raises `RuntimeModeNotAuthorizedException`
3. Calls the pure core
4. Inspects the returned `ResolutionResult`:
   - If `ResolvedIntent`, returns it
   - If `ResolutionFailure` with `retry_eligible: True` and the active mode is `GOVERNED_EXTRACTION_RETRY`, the wrapper routes the failure to the retry cell (caller-supplied or runtime-supplied); the retry cell may produce a new extracted intent that the wrapper re-resolves from zero
   - If `ResolutionFailure` with `retry_eligible: False`, the wrapper raises the corresponding `ResolverException` subclass

The retry cell consumes `ResolutionFailure` values directly. The exception-raising path is only taken at the boundary between the wrapper and application code, not internally.

#### 17.2.3 The `ResolverException` hierarchy

```python
class ResolverException(Exception):
    """Base class for all resolver-raised exceptions. Carries the full ResolutionFailure."""
    failure: ResolutionFailure
    def __init__(self, failure: ResolutionFailure):
        self.failure = failure
        super().__init__(failure.failure_category.value)


class ResolverContractException(ResolverException):
    """
    Programmer error: invalid input shape, corrupted compiled index,
    contract violation. Raised from the pure core for these conditions
    only. Application code should not catch this; it indicates a bug.
    """


class ResolverAuthorityException(ResolverException):
    """
    Base class for any authority-terminal failure. Raised by the wrapper.
    Catching this is appropriate at the application boundary to
    surface a safe user-facing message.
    """


class ExtractionRepairExhaustedException(ResolverAuthorityException):
    """
    The retry cell exhausted its budget (count, wall-clock, tokens,
    tool calls, or no-progress) on extraction-repairable failures.
    Final attempt's failure is in self.failure.
    """


class UnknownReferenceException(ResolverAuthorityException):
    """Raised for RESOLVER_UNKNOWN_ENTITY, RESOLVER_UNKNOWN_COLUMN, RESOLVER_ALIAS_UNRESOLVED."""


class TerminalAmbiguityException(ResolverAuthorityException):
    """Raised for RESOLVER_AMBIGUOUS, RESOLVER_DISAMBIGUATION_REQUIRED."""


class GovernanceDeniedException(ResolverAuthorityException):
    """
    Raised for any GOVERNANCE_* failure. The specific category is
    in self.failure.failure_category.
    """


class RuntimeModeNotAuthorizedException(ResolverException):
    """
    Raised when the runtime policy rejects (rather than downgrades)
    an unapproved GOVERNED_EXTRACTION_RETRY request.
    """
```

The mapping from `FailureCategory` to exception subclass is fixed and lives in code as a deterministic dispatch. The exception's `failure` attribute carries the full `ResolutionFailure` object, including the `FailureContext` (§16). Whether the application catches at `ResolverException`, `ResolverAuthorityException`, or a specific subclass is the application's choice.

#### 17.2.4 Information visibility in exceptions

The `ResolutionFailure` attached to a raised exception carries the full `FailureContext` — including registry candidates, denied field names, governance reasons, layer provenance, and credential-class hints. This is the audit-and-operator channel from the visibility-split table in §8.

Application code that catches a `ResolverException` **must not** propagate the `failure.context` fields into LLM-facing or user-facing channels. The exception object is for internal handling, logging, and audit emission. The user-facing message **must** be constructed from a fixed template that takes only safe inputs (failure category, display labels, generic policy text). This is the same channel-routing rule as §8, applied at the exception boundary.

#### 17.2.5 Audit emission

Every `ResolutionFailure` — whether returned from the pure core to a retry cell or raised through the wrapper — **must** be recorded in the audit ledger before any retry decision is made. The audit record contains the full `ResolutionFailure`, the runtime mode at the time of failure, the `agent_id`, the registry version, and the timestamp. The LLM-facing channel sees only what the sanitized-feedback template emits (§8); the audit ledger sees the full record.

---

### 17.3 Approval workflow for `GOVERNED_EXTRACTION_RETRY`

The `GOVERNED_EXTRACTION_RETRY` mode is approval-gated. Approval takes the form of a separate `ApprovalRecord` artifact bound to `(agent_id, mode)`, persisted in an `ApprovalRegistry` consulted by the runtime entry-point wrapper at every request.

This design separates approval from the agent manifest itself, which means: revocation does not require a manifest re-publish; approval has its own audit lifecycle; and the same approval mechanism extends cleanly to future Ojas approval surfaces (companion specs, additional modes) without modifying the agent manifest schema.

#### 17.3.1 `ApprovalRecord` schema

```python
class ApprovalScope(BaseModel):
    """
    Optional constraints layered on top of (agent_id, mode).
    Populated by the approving authority when the approval is conditional.
    """
    model_config = ConfigDict(extra='forbid', frozen=True)
    tenant_id: str | None = None              # if set, approval applies only to this tenant
    environment: str | None = None            # if set, approval applies only to this environment
    max_retries_per_request: int | None = None  # if set, overrides default retry cap


class ApprovalRecord(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    approval_id: str                          # globally unique
    agent_id: str
    mode: RuntimeMode
    approver_id: str                          # identity of approving principal
    approver_signature: bytes                 # cryptographic signature over the canonical form
    approved_at: datetime                     # UTC
    expires_at: datetime | None = None        # if set, approval is time-bound
    scope: ApprovalScope = ApprovalScope()
    revoked: bool = False
    revoked_at: datetime | None = None
    revoked_by: str | None = None
    revocation_reason: str | None = None
```

The `approver_signature` is a cryptographic signature over the canonical serialization of the other fields (excluding the signature itself). The signing key, signature algorithm, and verification process are deployment-specific; the requirement is that the runtime check (§17.3.3) verifies the signature before honoring the record. Implementations **should** use a key separation between Platform-approval signing keys and Tenant-approval signing keys when the broader Ojas governance layer makes that distinction.

#### 17.3.2 `ApprovalRegistry` interface

```python
class ApprovalRegistry(Protocol):
    def find_current(
        self,
        agent_id: str,
        mode: RuntimeMode,
        now: datetime,
    ) -> ApprovalRecord | None:
        """
        Return the current, unrevoked, unexpired ApprovalRecord for
        (agent_id, mode), or None.

        Implementations must verify the signature before returning a record.
        Implementations must return None for any record that is revoked,
        expired, or has an invalid signature.
        """
```

The registry is consulted by the runtime entry-point wrapper at every request. Implementations may cache approval records but **must** honor revocation events within a bounded latency (the recommended bound is one minute; the exact value is deployment-policy).

#### 17.3.3 The runtime check

The runtime check from §3 has the full signature:

```python
def check_mode_authorization(
    agent_id: str,
    requested_mode: RuntimeMode,
    approval_registry: ApprovalRegistry,
    runtime_policy: RuntimePolicy,
    now: datetime,
) -> ModeAuthorizationResult:
    if requested_mode == RuntimeMode.STRICT_DETERMINISTIC:
        return ModeAuthorizationResult.AUTHORIZED   # default mode, no approval needed

    record = approval_registry.find_current(agent_id, requested_mode, now)

    if record is not None:
        # Apply ApprovalScope constraints, if any
        if not approval_scope_matches(record.scope, runtime_policy, now):
            return _no_approval_result(runtime_policy)
        return ModeAuthorizationResult.AUTHORIZED

    return _no_approval_result(runtime_policy)


def _no_approval_result(runtime_policy: RuntimePolicy) -> ModeAuthorizationResult:
    if runtime_policy.unauthorized_mode_request_action == "DOWNGRADE":
        return ModeAuthorizationResult.DOWNGRADED_TO_STRICT_DETERMINISTIC
    elif runtime_policy.unauthorized_mode_request_action == "REJECT":
        return ModeAuthorizationResult.REJECTED
```

Three outcomes:

- **`AUTHORIZED`** — a current, unrevoked, unexpired, signature-valid `ApprovalRecord` exists for `(agent_id, requested_mode)`, and any `ApprovalScope` constraints are satisfied. The runtime entry-point wrapper proceeds with the requested mode.

- **`DOWNGRADED_TO_STRICT_DETERMINISTIC`** — no valid approval, and runtime policy is configured to downgrade. The wrapper rewrites the intent's `requested_mode` to `STRICT_DETERMINISTIC`, emits an audit event recording the downgrade (with the original mode, the missing approval reason, the `agent_id`, and the timestamp), and proceeds.

- **`REJECTED`** — no valid approval, and runtime policy is configured to reject. The wrapper raises `RuntimeModeNotAuthorizedException` carrying a `ResolutionFailure` with `failure_category=RUNTIME_MODE_NOT_AUTHORIZED`. The audit ledger records the rejection.

The choice between downgrade and reject is `RuntimePolicy` configuration set at deployment, not per-request. Both are auditable.

#### 17.3.4 Revocation

Revocation is a separate event, not a manifest re-publish. The revoking principal updates the `ApprovalRecord` in the registry with `revoked=True`, `revoked_at`, `revoked_by`, and `revocation_reason`. The signature on the original record is preserved for audit. The registry's `find_current` implementation **must** return `None` for any record where `revoked=True`, regardless of other fields.

Revocation propagation latency is deployment-specific but bounded (recommended one minute). During the propagation window, a request that has already passed the runtime check but not yet completed continues to run; a new request after propagation sees the revoked state.

Revocation **must** emit an audit event recording: the `approval_id`, the revoking principal, the revocation reason, the timestamp, and the prior state of the record. This is the canonical record of why approval was withdrawn.

#### 17.3.5 Expiry

When `expires_at` is set, the approval record is automatically invalid after that timestamp regardless of revocation state. The registry's `find_current` **must** return `None` for any record where `expires_at <= now`. Expiry does not require a separate event — the `expires_at` field is the authority — but implementations **should** emit an audit event when a previously-valid approval transitions to expired, for observability.

#### 17.3.6 Approval composability with broader Ojas approval workflow

The `ApprovalRecord` schema is intentionally minimal at v1.0: `(agent_id, mode)` binding, signature, expiry, revocation, and a small scope object. When the broader Ojas approval workflow eventually arrives — covering agents, tools, domain packs, and runtime envelopes across the platform — the `ApprovalRecord` schema is the precedent that other approval artifacts compose against. Specifically:

- The same signing infrastructure can sign other approval artifact types
- The same revocation event shape applies
- The same `find_current` query pattern extends
- The same audit-event shape extends

This composability is by design. v1.0 does not specify the broader workflow; v1.0 does specify a record shape that the broader workflow can adopt without breaking changes.

#### 17.3.7 What the `ApprovalRecord` does not contain

For clarity, the `ApprovalRecord` does not contain:

- The agent's manifest, prompt, or capability declarations (those live in the agent manifest)
- The list of approved tools or use cases (those are governed by separate approval surfaces in the broader Ojas approval workflow when it arrives)
- Per-request usage counters or quotas (those are runtime concerns, not approval concerns)
- LLM-facing content of any kind

The record is a small, signed authority assertion that says: *for this agent and this mode, approval exists*. Everything downstream of that assertion is governed by other components.

---

**Part 3 ends here. Part 4 begins with Appendix A (frozen principles).**
