# Ojas Data — Deferred Design Topics

This document records design topics that were identified during the Ojas Data v1.0 design phase but were deliberately deferred. None of them invalidates or blocks the v1.0 freezes. Each one extends the design into a surface the v1.0 phase did not need to reach.

These topics are deferred-by-design: they will be addressed when concrete deployment evidence makes a specific choice load-bearing. Until then, the v1.0 design treats each topic as a known gap with a stated holding position, not as an unresolved decision.

---

## Scope of v1.0 design closure

The Ojas Data v1.0 design closes two surfaces:

- **LLM-facing safety surface** — what the LLM may see, through which channel, with what shape, under which constraints
- **Developer authoring surface** — how schema becomes a compiled registry, through what tooling, with what review process

The topics in this document fall outside both surfaces. They sit in operational structure, governance lifecycle, and deployment behavior that the LLM never interacts with directly and that the developer authoring path does not need to specify.

---

## Topic 1 — Tenant authority structure

### What's deferred

The v1.0 design references "two-tier registry" and "tenant overrides" without specifying what those mean structurally. The questions that remain open:

- Can a tenant add aliases to a platform-published registry, or only restrict what the platform exposes?
- Can a tenant mark a field as more sensitive than the platform default, or only equal-or-less sensitive?
- What happens when a tenant override and a platform update collide — does the tenant override survive, get reset, or trigger a review?
- How does the tenant override layer compose with the strictest-wins gate composition rule?
- Can tenants share registry fragments across themselves, or is every tenant's overlay strictly tenant-local?

### Why it was deferred

The v1.0 design is sufficient for single-tenant deployments and for multi-tenant deployments where the platform owns the entire registry. Tenant-authored overrides are a real future need for SaaS deployments but the right structure depends on operational patterns that won't be visible until multiple tenants are actually operating.

### Holding position for v1.0

Until tenant authority structure is specified:

- All registry authoring is platform-level
- Tenant scope is enforced through scope dimensions in the platform registry, not through tenant-authored overlays
- A deployment that requires per-tenant alias customization must produce per-tenant compiled registries through the same compile pipeline, not through runtime overrides

### When to revisit

When the second or third multi-tenant SaaS deployment of Ojas Data needs tenant-specific aliases, sensitivity classifications, or scope dimensions that can't be expressed through the platform registry's scope dimensions alone.

---

## Topic 2 — Data contract layer binding to the metadata layer

### What's deferred

The v1.0 design references canonical contracts (`ExtractedIntent.v1`, `SafeUserMessage`, etc.) as registered entries in "the Ojas data contract registry." It does not specify the relationship between that contract registry and the compiled metadata registry. The questions that remain open:

- Are data contracts versioned independently from the metadata registry, or do they version together?
- Who authors data contracts — the same developer who annotates entities, or a separate role?
- How does a data contract reference entities and fields from the metadata registry, and what happens when those entities or fields change?
- Is the data contract registry compiled the same way the metadata registry is, or is it a separate compile pipeline?
- What happens to in-flight LLM conversations when a referenced contract is version-bumped?

### Why it was deferred

The v1.0 design treats canonical contracts as a layer borrowed from the broader Ojas governance design, where they are already specified. Whether Ojas Data needs its own contract registry, or extends the platform's, or shares it, depends on operational patterns that aren't yet visible.

### Holding position for v1.0

Until data contract layer binding is specified:

- Ojas Data uses the canonical contracts already registered in the broader Ojas governance design
- Contract version references in prompt schemas are pinned at compile time
- Contract version changes require a registry recompile and a documented review process
- The compile pipeline for prompt schemas validates against contracts at compile time; runtime does not re-validate

### When to revisit

When Ojas Data needs to register a contract that doesn't fit naturally into the broader Ojas contract registry, or when contract evolution begins causing coordination overhead across deployments.

---

## Topic 3 — Model identity binding to channels and profiles

### What's deferred

The v1.0 design specifies that model identity is recorded with `versionKind: PINNED` and that only pinned model versions qualify for auto-approval. It does not specify how models bind to channels. The questions that remain open:

- Does every channel use the same model, or can different channels use different models?
- Can a deployment configure "use a smaller model for extraction-repair, a larger model for safe message generation"?
- If different channels can use different models, how is calibration per channel computed, and what's the relationship between channel-level calibration and the broader calibrated-confidence rule?
- What happens when a model is deprecated by the provider — do all profiles bound to that model become inactive, or only some?
- Is the model identity recorded per-profile, per-channel, or per-request?

### Why it was deferred

The v1.0 design assumes a single model per deployment, which is the simplest case and the most common starting configuration. Multi-model deployments are a real future need (cost optimization, latency optimization, capability matching) but the right binding structure depends on operational patterns that won't be visible until deployments actually run multi-model.

### Holding position for v1.0

Until model-to-channel binding is specified:

- A deployment uses a single pinned model across all channels
- The model identity is recorded once per deployment, referenced by every emission
- A model deprecation requires a deployment-wide migration, not a per-channel update
- Calibration is computed against the deployment's single model

### When to revisit

When a deployment encounters concrete pressure to use different models for different channels — either cost pressure (small model for routine extraction, large model for complex safe-message generation) or capability pressure (different models for different languages or domains).

---

## Topic 4 — Degraded-mode behavior

### What's deferred

The v1.0 design specifies behavior under normal operation. It does not specify behavior when the deployment is partially broken. The questions that remain open:

- The model provider is down. Does the system queue requests, fail fast, fall back to a different model, or fall back to non-LLM paths?
- The compiled registry can't be loaded (corrupt artifact). Does the system refuse all requests or fall back to a previous version?
- The privileged diagnostic classifier raises an unexpected exception. Does the request fail closed (deny) or fail with a generic error message?
- The audit log destination is unavailable. Does the system continue serving requests without audit, queue them in memory, or refuse?
- The database itself is unavailable. Does the system distinguish "no data because DB is down" from "no data because of policy"?

### Why it was deferred

The closed-world principle suggests fail-closed across the board, but each of these has operational consequences. A bank that uses Ojas Data for regulatory filing wants different fallback behavior than a startup that uses it for internal analytics. The right policies depend on deployment risk tolerance, which isn't a design-time decision.

### Holding position for v1.0

Until degraded-mode behavior is specified per case:

- All degraded states default to fail-closed (refuse requests)
- Failed audit log writes block request completion (audit is a prerequisite for response emission)
- Registry load failure refuses all requests until the registry is restored
- Model provider unavailability surfaces as a generic system error to the user, not a model-specific error

These defaults are conservative. Deployments can override them through documented configuration, but the override is a deployment policy decision, not a design-time decision.

### When to revisit

When a deployment encounters concrete operational evidence that the conservative defaults are too restrictive (e.g., a customer-facing deployment where fail-closed during a model outage causes unacceptable user-visible failures), or when regulatory requirements force specific degraded-mode behaviors.

---

## Topic 5 — Registry lifecycle and evolution

### What's deferred

The v1.0 design specifies compile-time review and the immutable compiled artifact. It does not specify how the registry evolves over months and years. The questions that remain open:

- Can a registry be rolled back to a previous version in production, or is rollback only possible through re-compilation?
- When two developers make conflicting changes to the source manifest, how does the merge work? (This is an authoring-tool question, not just a Git question — what happens when one developer adds an alias and another removes the field that alias references?)
- What's the deprecation path for an alias that's been emitted to many LLM conversations but the developer wants to remove? Does the deprecation happen instantly at the next compile, with a grace period, or with a per-tenant migration?
- How are registries archived — does the platform keep every compiled version forever for audit, or compact older ones?
- What happens to a compiled registry when its source manifest is deleted from version control?

### Why it was deferred

The v1.0 design is sufficient for the first compiled registry of any deployment. Evolution questions become load-bearing after the first significant version bump in production, which doesn't happen until the deployment has been running long enough to accumulate operational history.

### Holding position for v1.0

Until registry lifecycle is specified:

- Each compile produces a new immutable artifact with a stable version identifier
- Older compiled registries are retained indefinitely (no compaction)
- Rollback is implemented as deploying an older compiled artifact, not as in-place mutation
- Manifest merge conflicts are resolved through standard version control tooling, with a recompile required after merge resolution
- Alias removal is treated as a registry change requiring full review

### When to revisit

When a deployment has been running long enough that one of these questions becomes concrete (typically when the second or third major registry version is being prepared, or when audit retention policy requires a decision about archival).

---

## Topics deferred as premature

These topics were identified during the v1.0 design phase but deferred not because of operational dependency — because the load on the existing freezes isn't yet sufficient to justify designing the answer.

### Multi-modal extraction

The current design assumes text input. Extending to image, audio, or document input would require channel taxonomy additions and prompt schema additions. The right shape of those additions depends on what multi-modal cases actually look like in deployment.

**Premature until:** a deployment has a concrete use case for multi-modal extraction that the current text-only design cannot serve.

### Cross-tenant federated queries

What happens when a query needs data from two tenants and authorization must compose across both. The closed-world model would have to be extended to handle multi-tenant authority composition.

**Premature until:** a deployment has a concrete use case for federated queries (which is rare in regulated enterprise contexts).

### Cross-domain-pack integration

PDF/JRXML, HireFlux, and other Ojas domain packs reference Ojas Data conceptually. The integration boundary isn't specified.

**Premature until:** a second domain pack actually needs to consume Ojas Data outputs. The first integration will reveal what the boundary needs to be.

### Streaming responses

The current design assumes request-response. Streaming would need its own envelope design and a different audit model.

**Premature until:** a deployment has a concrete latency requirement that request-response cannot meet.

---

## How to use this document

This document is the **deferred-design backlog**. It is not a TODO list for the v1.0 documentation production phase. It is a record of known gaps, intended to:

1. Prevent re-discovery — when someone asks "did we consider tenant overrides?", the answer is "yes, deferred, here's the holding position"
2. Capture context — when a deferred topic becomes urgent, the document records why it was deferred and what would make it ready to revisit
3. Bound the v1.0 scope — by naming what's deliberately not in scope, the v1.0 documentation can be focused without appearing incomplete

When a deferred topic is taken up, it should be moved from this document into the appropriate active design conversation. The "when to revisit" sections name the triggers that should cause that move.

---

## Relationship to v1.0 freezes

None of the topics in this document invalidates any v1.0 freeze. Each topic extends the design into a surface the v1.0 freezes don't reach:

| v1.0 freeze surface | Deferred surface |
|---|---|
| LLM-facing safety rules | Degraded-mode behavior, model-to-channel binding |
| Developer authoring rules | Registry lifecycle, tenant authority structure |
| Compile-time contracts | Data contract layer binding |
| Runtime envelope | Multi-modal extraction, streaming |
| Single-deployment scope | Cross-tenant federation, cross-domain-pack integration |

The v1.0 freezes hold under any reasonable resolution of the deferred topics. A future design pass on tenant authority structure will extend the registry model, not replace it. A future design pass on degraded-mode behavior will specify how the existing fail-closed defaults can be tuned, not whether fail-closed is the right default.

This separation is what makes the v1.0 closure honest. The design is closed for what it covers. It is open for what it doesn't.
