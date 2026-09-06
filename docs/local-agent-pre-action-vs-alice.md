# How local / air-gapped agents do pre-action verification today — and why ALICE is differentiated

Updated: 2026-09-05. Positioning and prior-art note. Scope follows the
[two-mode architecture](prds/ALICE-DCAMR-Architecture.md) (ONLINE and OFFLINE / DDIL)
and complements the [threat model](threat-model.md).

Sources are 2025–2026 web material gathered for this note (linked inline). Several
are vendor blogs describing their own products; treat product-framing claims as
directional, not audited. The strongest independent anchors are the Palantir AIP
capability descriptions and the recurring NIST-control mapping, which appear across
multiple sources.

**Bottom line:** local and air-gapped agent deployments today *do* perform
pre-action verification and event logging — this is not empty space. But they do it
in ways that leave specific seams, and those seams are exactly what ALICE / DCAMR is
built to close. ALICE's differentiator is **not** "pre-action gating exists"; it is
**pre-action gating that runs as an independent hardware trust boundary, under
externally-signed governance, assuming the agent itself is the compromised party,
and that survives disconnection.**

---

## 1. How pre-action verification works today

The dominant pattern for local / air-gapped agents is a **deny-by-default tool
registry + approval gates**, enforced by a **local control plane inside the
boundary**:

- Each agent is granted named tools for a named purpose; **every state-changing call
  is gated**, evaluated against policy by *identity + intent* (not just the action),
  then allowed / blocked / escalated to a human owner — all locally, with no external
  dependency. Human approval triggers above a configurable **risk threshold**.
  ([Prediction Guard — runtime policy enforcement](https://predictionguard.com/blog/runtime-ai-policy-enforcement),
  [6clicks — classified & air-gapped agents](https://www.6clicks.com/resources/blog/deploying-ai-agents-in-classified-and-air-gapped-environments))
- The integrated exemplar is **Palantir AIP** (cleared to DoD IL5/IL6, supports
  ITAR): the **Ontology** is the control point — agents inherit the same ACLs and
  Markings as human users, are constrained to an explicit **action set**,
  structural / high-risk changes **require human approval**, and every model call is
  filtered, permission-scoped, and logged.
  ([Palantir AIP deep dive](https://www.instinctools.com/blog/palantir-aip/),
  [Maxim — governance platforms for air-gapped](https://www.getmaxim.ai/articles/top-5-ai-governance-platforms-for-air-gapped-deployments/))
- A recurring hard requirement: enforcement **must run inside the sealed network**.
  Vendors explicitly disqualify gateways that phone home — routing "enforcement
  decisions and telemetry outside the customer's perimeter … is a structural
  disqualifier."
  ([Mattermost — agentic AI in air-gapped environments](https://mattermost.com/blog/can-agentic-ai-work-in-air-gapped-environments/))

The cloud/managed-runtime versions of this same pattern (for context — these assume
connectivity and do **not** reach the disconnected edge) include AWS Bedrock
AgentCore's Cedar-policy Gateway with stateful/temporal policies, Azure AI Foundry's
approval-checkpoint workflows, and MCP/A2A gateways (AgentGateway, Docker MCP
Gateway, Microsoft's MCP Security Gateway).
([AWS — policy in AgentCore](https://aws.amazon.com/blogs/machine-learning/secure-ai-agents-with-policy-in-amazon-bedrock-agentcore),
[Microsoft — runtime authorization](https://techcommunity.microsoft.com/blog/microsoft-security-blog/authorization-and-governance-for-ai-agents-runtime-authorization-beyond-identity/4509161))

## 2. How event logging works today

- **Local SIEM, append-only, in-enclave.** Splunk on-prem is the de facto default in
  defense; the log store must be "a first-class in-enclave component," not a cloud
  service with an in-region option. Every prompt, model response, tool call, and
  human approval is logged locally.
  ([Prediction Guard — the SIEM gap in agentic AI](https://predictionguard.com/blog/ai-security-event-logging-the-siem-gap-in-agentic-ai-governance),
  [ibl.ai — air-gapped AI for federal agencies](https://ibl.ai/blog/air-gapped-ai-for-federal-agencies))
- **One-way data diode** (hardware) for controlled telemetry export to a separately
  accredited monitoring enclave; nothing returns by network. Policy and model updates
  come **in** via signed physical media or a cross-domain solution, batched on a
  defined cadence.
  ([Truefoundry — air-gapped LLMs in defense](https://www.truefoundry.com/blog/air-gapped-ai-deploying-enterprise-llms-in-highly-regulated-industries))
- Maps to specific **NIST controls**: AU-2 / AU-12 (audit logging, no vendor in the
  chain), CM-2 / CM-3 (model artifacts, prompts, configs version-controlled by the
  agency), SC-7 (boundary protection), SI-4 (system monitoring inside the agency's
  stack); NIST SP 800-171 for CUI. OpenTelemetry is used to *emit* traces but "does
  not store or sign an audit trail on its own."
  ([ibl.ai](https://ibl.ai/blog/air-gapped-ai-for-federal-agencies),
  [miniOrange — AI agent audit trails 2026](https://www.miniorange.com/blog/ai-agent-audit-trail/))

## 3. Where today's practice falls short — and what ALICE changes

Current air-gapped practice is, in short: **allow-lists + human approval + local
Splunk + diode export.** Functional and accreditable, but with real seams.

| Dimension | Air-gapped practice today | What ALICE / DCAMR changes |
| --- | --- | --- |
| **Where enforcement lives** | Inside the agent's *orchestration layer* — the same framework the agent runs in | A separate **hardware trust boundary** (the Pi) the agent cannot modify. If the orchestrator is compromised, the gate is not in the blast radius |
| **Policy source** | Local disk "under version control," authored by the operating agency | **Signed, externally-governed, removable** policy + baseline packages; the Pi verifies the signature and **rejects tampered** packages — author ≠ enforcer |
| **Detection logic** | Deny-by-default registry (RBAC / ABAC allow-lists) | Adds a **behavioral baseline + sequence anomaly engine (L2)** — catches the "every step is individually allowed, the sequence is an attack" case allow-lists miss |
| **Under-justified actions** | Binary allow / deny / escalate-to-human | **REQUEST_CONTEXT** structured step-up — bounded, schema-constrained negotiation before burning a human, that can raise or lower risk but never override hard policy |
| **Audit integrity** | "Immutable" / append-only Splunk (retention + ACLs) | **Hash-chained, batch-signed** log, plus the **decision-vs-explanation split** and **reconcile-never-rewrite** semantics |
| **Connectivity model** | *Static* air-gap (permanent isolation) | **DDIL** — intermittent: full enforcement while disconnected *and* evidence reconciliation on reconnect (a broader, harder case than a fixed air-gap) |

## 4. Takeaways for positioning

1. **The biggest genuine gap is "enforcement lives in the orchestrator."** Today's
   deny-by-default gate is embedded in the same framework the (potentially
   compromised) agent runs in — it largely trusts the orchestration layer to police
   itself. ALICE's **independent physical PDP/PEP** is the real differentiator, not
   the existence of pre-action gating. State this plainly rather than claiming
   novelty on gating itself.

2. **ALICE should interoperate, not replace.** Splunk-on-prem + data diode + signed
   media + the NIST AU / CM / SC / SI controls are the entrenched, accreditation-shaped
   reality. This is an advantage: ALICE's design — signed removable authority, an
   in-enclave hash-chained audit log, and syslog / OCSF export at the audit boundary —
   **maps cleanly onto those same controls**, which makes ALICE easier to accredit and
   lets it emit into the Splunk / diode pipeline the enclave already runs rather than
   fighting it.

3. **ALICE targets DDIL, not just air-gap.** Pure air-gap tooling assumes permanent
   isolation. ALICE's disconnected-*capable*-with-reconciliation model covers the
   intermittent (DDIL) case that static air-gap products do not, while degrading
   gracefully to the fully-disconnected case they do cover.

## Related docs

- [ALICE-DCAMR architecture (PRD)](prds/ALICE-DCAMR-Architecture.md)
- [Trust boundaries and threat model](threat-model.md)
- [Accepted data and product direction — 2026-09-05](data-direction-2026-09-05.md)
