# Open Risks Addressed by Ojas Data

## Part 1 — Issues Addressed by Ojas Data

Ojas Data addresses real, publicly reported classes of incidents in AI-agent, LLM-tool, SQL-agent, RAG, and enterprise assistant systems.

The central security principle is:

```text
The LLM may understand or propose intent.
Policy controls execution.
The runtime constructs the data operation.
Sensitive values are blocked or masked before LLM visibility.
```

Ojas Data does **not** depend on the LLM behaving correctly. It assumes the LLM, framework, prompt, or tool layer can be manipulated and places final authority in deterministic policy, query construction, masking, credentials, and audit.

---

## 1. Issue Classes Addressed

| # | Issue Class | Real-World Pattern | Ojas Data Control |
|---:|---|---|---|
| 1 | Prompt injection | LLM follows malicious instructions hidden in email, web pages, or documents | LLM can propose, but policy controls execution |
| 2 | Zero-click / indirect prompt injection | Assistant processes malicious content without explicit user intent | Tool access is constrained; execution goes through core policy |
| 3 | Model-generated SQL risk | LLM writes unsafe SQL directly | LLM never writes executable SQL |
| 4 | SQL injection / prompt-to-SQL injection | Prompt manipulates SQL-generating chain | Safe SQL/document builder constructs operations from policy |
| 5 | Sensitive data exfiltration | Assistant leaks private/internal data | Sensitive fields blocked; masked fields transformed before LLM visibility |
| 6 | Over-broad tool access | Agent can call tools beyond its job | Agent-to-tool authorization |
| 7 | Excessive agency | Agent performs destructive or unintended actions | Operation guardrails and approval workflows |
| 8 | Credential leakage | Tool/framework exposes `.env`, API keys, DB credentials, stack traces | Secret-leak prevention and least-privilege credential roles |
| 9 | Cross-user / cross-tenant data exposure | Users see other users’ records or conversation data | Row/path scope and audit |
| 10 | Client-side filtering leaks | Backend returns too much data and UI hides it | Query builder fetches only approved fields |
| 11 | Framework/library vulnerabilities | LangChain/LangGraph/plugin vulnerabilities expose data | Core enforcement boundary outside framework adapters |
| 12 | Weak auditability | Cannot prove what the AI accessed | Policy-versioned audit events |

---

## 2. Public Incident and Vulnerability Patterns

### 2.1 Microsoft 365 Copilot “EchoLeak” — Prompt Injection Data Exfiltration

EchoLeak, tracked as **CVE-2025-32711**, was reported as a zero-click prompt-injection vulnerability in Microsoft 365 Copilot. A crafted email could trigger data exfiltration without normal user interaction.

Reference: <https://arxiv.org/html/2509.10540v1>

**Ojas Data relevance:**

```text
Problem:
  LLM processes malicious content and tries to access or exfiltrate data.

Ojas Data mitigation:
  LLM cannot directly access databases.
  It can only call registered tools.
  Tools pass through policy, row/path scope, masking, credential role, and audit.
```

Ojas Data does not solve all prompt injection, but it reduces the blast radius at the data-access layer.

---

### 2.2 LangChain / LangGraph Framework Vulnerabilities

Public reports have described LangChain/LangGraph vulnerabilities involving path traversal, unsafe deserialization, SQL injection classes, and possible exposure of configuration files, environment secrets, API keys, and conversation histories.

References:

- <https://www.cyera.com/research/langdrained-3-paths-to-your-data-through-the-worlds-most-popular-ai-framework>
- <https://nvd.nist.gov/vuln/detail/cve-2024-8309>

**Ojas Data relevance:**

```text
Problem:
  Framework/tool layer has vulnerabilities or lets model-generated queries reach the backend.

Ojas Data mitigation:
  Frameworks are adapters, not the authority.
  All adapters call the same core dispatcher.
  Core authorization and safe query construction still run.
```

This is why the architecture line matters:

```text
Frameworks provide infrastructure. Ojas Data provides governance content.
```

---

### 2.3 Prompt-to-SQL Injection in LLM-Integrated Applications

Research and community issues have documented prompt-to-SQL injection risks in applications that translate natural language prompts into SQL queries.

References:

- <https://www.computer.org/csdl/proceedings-article/icse/2025/056900a076/215aWuWbxeg>
- <https://github.com/langchain-ai/langchain/issues/5923>

**Ojas Data relevance:**

```text
Problem:
  User prompt → LLM-generated SQL → SQL executes.

Ojas Data mitigation:
  User prompt → LLM selects registered tool.
  Runtime builds SQL/document operation.
  SQL comes from policy intersections, not the model.
```

This is one of the clearest differentiators of Ojas Data.

---

### 2.4 ChatGPT March 2023 Redis Bug — Cross-User Data Exposure

OpenAI disclosed that a bug in an open-source Redis client library caused some users to see other users’ chat history titles and, under specific timing conditions, possibly the first message of newly created conversations.

Reference: <https://openai.com/index/march-20-chatgpt-outage/>

**Ojas Data relevance:**

```text
Problem:
  Cross-user data exposure through shared state/session/cache bug.

Ojas Data mitigation:
  Row/path scope is explicit.
  Credential and policy context are included in execution.
  Audit records actor, policy version, resource, and decision.
```

Ojas Data would not prevent every Redis/client-library bug, but its row/path scoping and audit model address the same class of “wrong user sees wrong data” risk.

---

### 2.5 Meta AI Prompt/Response Access Bug — Missing Authorization Check

A 2025 report said a Meta AI vulnerability allowed users to access other people’s chatbot prompts and responses by changing numeric identifiers in network traffic because the system failed to verify authorization for the requested prompt/response.

Reference: <https://www.tomsguide.com/computing/online-security/meta-ai-was-leaking-chatbot-prompts-and-answers-to-unauthorized-users>

**Ojas Data relevance:**

```text
Problem:
  Object ID changed → backend returns someone else’s data.

Ojas Data mitigation:
  Lookup values are not enough.
  Runtime applies row/path scope and agent authorization.
  Query builder injects allowed scope before data is returned.
```

This maps directly to Ojas Data’s row-scope/path-scope design.

---

### 2.6 Copilot “Reprompt” Exploit — Prompt-Triggered Tool/Data Exfiltration

A 2026 report described a Copilot “Reprompt” exploit where attackers could trigger prompt instructions through a crafted link, potentially collecting sensitive user details and exfiltrating them.

Reference: <https://www.windowscentral.com/artificial-intelligence/microsoft-copilot/copilot-ai-reprompt-exploit-detailed-2026>

**Ojas Data relevance:**

```text
Problem:
  LLM/action layer manipulated into collecting and sending sensitive data.

Ojas Data mitigation:
  Tool calls are limited.
  Sensitive data is blocked or masked before model visibility.
  External operations should require governed tools and audit.
```

Ojas Data is not a browser security product, but it addresses the data-access and tool-permission side of this class.

---

## 3. Strongest Ojas Data Controls

### 3.1 Ojas Data Avoids Model-Generated Executable SQL

Many systems do this:

```text
LLM writes SQL → checker/filter reviews → DB executes
```

Ojas Data does this:

```text
LLM selects tool → policy authorizes → runtime builds query → DB executes
```

This avoids a large class of prompt-to-SQL and model-generated query issues.

---

### 3.2 Sensitive Values Never Reach the LLM

This is one of the strongest controls.

```text
Bad pattern:
  DB returns raw email/SSN/token → LLM asked not to leak it.

Ojas pattern:
  DB returns only approved fields → runtime masks before LLM visibility.
```

The LLM cannot leak raw values it never received.

---

### 3.3 Frameworks Are Not the Security Boundary

LangChain, LangGraph, CrewAI, OpenAI function calling, and similar frameworks help with orchestration. Ojas Data treats them as adapters.

```text
Adapter can select/call tool.
Core still authorizes and executes.
```

This matters because framework vulnerabilities and misconfigurations are real.

---

### 3.4 Least-Privilege Credentials Reduce Blast Radius

Even if a bug reaches the DB path, the runtime should use a credential that cannot perform unrestricted operations.

```text
agent_read    → read only
agent_write   → read / insert / update, no DDL / drop / grant
 audit_writer → audit only
```

---

## 4. What Ojas Data Does Not Fully Solve

Ojas Data does **not** fully solve:

```text
all prompt injection
all browser-agent risks
all cloud misconfiguration
all Redis/session library bugs
all framework CVEs
all insider/admin abuse
all credential compromise
```

What it does solve or strongly mitigate is narrower and defensible:

```text
AI-agent data-access overreach
model-generated SQL risk
sensitive/masked field leakage to LLMs
unauthorized tool/use-case execution
wrong-row/wrong-path access at the governed data layer
weak auditability of AI data operations
```

---

## 5. Final Positioning for Issues Addressed

Ojas Data addresses real incident classes already seen in the AI ecosystem:

```text
prompt injection
zero-click indirect injection
LLM-to-SQL injection
framework/tool vulnerabilities
cross-user data exposure
credential/config leakage
over-broad agent permissions
sensitive data exfiltration
```

The best positioning is:

```text
Existing incidents show that LLM/tool layers can be manipulated or flawed.
Ojas Data assumes that risk and puts the final data-access authority in policy-controlled runtime execution.
```

---
