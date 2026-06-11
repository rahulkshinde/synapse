# Synapse — Presentation

> Support Ticket Deflection System — RAG + Guardrails, Safer Automation

---

## Agenda
- Problem & stakes
- Ticket deflection system
- Architecture at a glance
- Guardrails & control loops
- EKS, CI/CD, rollout (incl. support)
- Observability & performance
- Impact, metrics, stakeholders, roadmap
- Q&A

---

## Problem & Stakes
- **On-call pain:** high noise, long context-building, tool-hopping during multiple high pririty tickets/incidents
- **Goal:** reduce MTTR and ticket volume via trustworthy, production-safe AI
- **Constraint:** security, cost, and reliability

---

## Support Ticketing Deflection System
- **Entry points:** Zendesk, Jira/JSM, OpenAI Support page, and email/web widget → queue → webhook to bot
- **LLM steps:** classify intent, extract entities (product, error, tenant), summarize ticket
- **Retrieval:** ground with KB/runbooks; detect “known issue” banners; propose resolution
- **Deflection paths:** instant answers, guided flows/forms, similar tickets; escalate with summary if confidence low
- **Feedback loop:** thumbs up/down → eval dataset → weekly prompt/tool retraining

---


## Architecture at a Glance
```mermaid
graph TB
  subgraph Entry[User Channels]
    A[Slack App: HMAC] -->|HMAC| GW[API Gateway]
    S[Slack Bot] -->|Events| GW
  end

  subgraph Edge[Security Perimeter]
    GW --> WAF[AWS WAF]
    WAF --> ALB[ALB + mTLS]
    ALB --> EKS[EKS Cluster]
  end

  subgraph Core[Core Engine]
    EKS --> WH[Webhook Handler]
    WH --> INT[Intent Classifier]
    INT -->|Incident Qs| ORCH[Query Orchestrator]
    INT -->|Health| LIVE[Live Telemetry Fetcher]
    ORCH --> CTX[Context Manager]
    CTX --> REDIS[(Redis 5m)]
    CTX --> DDB[(DynamoDB History)]
    ORCH --> VS[(OpenSearch Vector)]
  end

  subgraph AI[AI Processing - Bedrock]
    ORCH --> MINI[gpt-4o-mini]
    ORCH --> GPT[gpt-4o]
    MINI --> RESP[Response Generator]
    GPT --> RESP
  end

  subgraph Knowledge[Knowledge Pipeline - Write]
    GH[GitHub Webhooks] --> SQS[SQS Buffer]
    CONF[Confluence Webhooks] --> SQS
    SWP[Nightly Sweeper] --> SQS
    SQS --> XTR[Lambda Extractor]
    XTR --> EMB[OpenAI Embeddings: text-embedding-3-large]
    EMB --> VS
    EMB --> S3[(S3 Backup)]
  end

  subgraph Live[Live Data Sources]
    LIVE --> DDog[DataDog]
    LIVE --> PD[PagerDuty]
    LIVE --> GHAPI[GitHub]
  end

  RESP --> A
  RESP --> S
```

Key decisions
- RAG: split read (ORCH→OpenSearch) vs write (pipeline→OpenSearch)
- Cost control: 60% gpt-4o-mini / 40% gpt-4o routing; cache + circuit breakers
- Spike safety: SQS buffers bursts; token bucket rate limiting on APIs

---

## Ticket Flow: Zendesk/Jira Service Management → Resolution
- Intake (Zendesk/JSM → API Gateway)
  - Source sends HMAC-signed webhook; rate limits per source; replay protection
  - Normalize payload → {org_id, user_id, product, endpoint, sdk_version, region, severity, attachments, correlation_id}
- Security perimeter (WAF → ALB → EKS)
  - Raw body preserved for signature verification; header canonicalization
- Webhook Handler (EKS)
  - Validate and transform; attach source metadata; buffer to SQS on spikes
- Intent classification (gpt-4o-mini)
  - Classify (billing/auth/latency/SDK), extract entities; fall back to rules on very low confidence
- Context manager (Redis/DynamoDB)
  - Fetch cached context (Redis 5m), store conversation history (DynamoDB), dedupe via idempotency key
- Retrieval (OpenSearch + live fetches)
  - Vector search over KB/runbooks/release notes; fetch live status/metrics/incidents as needed
- Candidate response (OpenAI routing)
  - Route simple to gpt-4o-mini; complex to gpt-4o; return structured JSON with steps, refs, confidence
- Decision engine (deflect vs escalate)
  - If known-issue + high confidence + safe topic → post public reply in Zendesk/JSM, tag deflected-known, add internal note
  - Else → assign to AI Support Engineer queue with summary, repro checklist, next-step buttons
- Agent assist (console/Slack)
  - Sidebar suggestions, macros; Slack slash commands to fetch/attach diagnostics to ticket
- Audit & safety
  - Structured logs with correlation_id; PII redaction; timeouts, retries, rate limits
- Metrics emitted
  - FCR, deflection success/fail, override rate, time-to-first-response, resolution time, backlog age, cost/ticket
- KB & eval updates
  - On resolution, update KB/runbook gaps; ingest to vector index; add Q/A to eval set
- Closure & digest
  - CSAT request and reason codes; weekly digest to Product/Eng with top topics and automation backlog

```mermaid
sequenceDiagram
  autonumber
  participant ZD as Zendesk
  participant JSM as Jira_JSM
  participant SUP as Support_Page
  participant GW as API_Gateway
  participant SEC as WAF_ALB
  participant WH as Webhook_Handler
  participant CL as Classifier
  participant CTX as Context_Manager
  participant RET as Retrieval
  participant DEC as Decision_Engine
  participant AG as Agent_Console
  participant ENG as AI_Support_Engineer

  alt Zendesk
    ZD->>GW: HMAC webhook (ticket created/updated)
  else Jira JSM
    JSM->>GW: HMAC webhook
  else Support Page
    SUP->>GW: Web form submit
  end

  GW->>SEC: forward (rate-limit, replay check)
  SEC->>WH: request with raw body
  WH->>WH: validate + normalize payload
  WH-->>WH: buffer to SQS on spike
  WH->>CL: classify intent + extract entities (gpt-4o-mini)
  CL-->>WH: labels, entities, confidence
  WH->>CTX: fetch cache/history
  CTX-->>WH: context blob
  WH->>RET: retrieve KB, similar tickets, live status
  RET-->>WH: grounded snippets + signals
  WH->>DEC: assemble candidate response
  DEC-->>AG: suggest reply + confidence
  alt High confidence known issue
    DEC->>ZD: auto public reply + tag deflected-known
  else Needs human review
    DEC->>ENG: escalate with summary + next steps
  end
  DEC->>CTX: metrics + eval set update
```

---

## User Operations: AI Support Engineer — Ticket Workflow 
- **Channel intake:** Slack, Zendesk, Jira/JSM, or OpenAI Support page ticket arrives with org ID, endpoint, error code, severity
- **Auto-triage (gpt-4o-mini):** classify intent (billing/auth/latency), extract entities (product, endpoint, SDK, region), set priority and owner queue
- **Grounding:** retrieve KB/runbooks, release notes, incident status, similar tickets; surface known-issue banner if matched
- **Candidate reply:** propose steps with references (docs, runbook anchors); show confidence, require human send for medium/low
- **Decision gates:**
  - **High-confidence known issue →** deflect with one-click reply, log artifacts, tag “deflected-known”
  - **Else →** escalate to AI Support Engineer with prefilled ticket fields and suggested next actions
- **Human investigation assist:** generate repro checklist, request IDs, minimal code sample; suggest SDK/version checks and quick diagnostics
- **Partner loop:** if bug suspected, open issue in tracker with auto-filled impact, severity, repro, logs; link Slack thread and customer ticket
- **Closure & learning:** update KB/runbook gaps, add to eval dataset, tag topic for future automation; notify product/eng in weekly digest
- **Metrics captured:** FCR, deflection, time-to-first-response, resolution time, backlog age, CSAT; override rate and hallucination incidents

---

## Staff Proposal: Multi-Channel Intake Changes (Zendesk, Jira/JSM, OpenAI Support)
- **Unified intake gateway:** standardize webhooks from Zendesk, Jira/JSM, and Support page to API Gateway → normalized ticket schema
- **Normalization schema:** require org_id, user_id, product, endpoint, SDK/version, region, severity, reproduction artifacts, correlation_id
- **Source auth:** per-source HMAC secrets, replay protection, rate limits; source label preserved for reporting and routing
- **Smart triage:** gpt-4o-mini for classification/entity extraction; policy thresholds for auto-deflect vs. human-in-loop
- **Known-issue banners:** dynamic banners on Support page and agent console; driven by releases/incidents and KB updates
- **Slack integration:** slash command to create/attach tickets; thread-to-ticket linking; on-call handoff templates
- **Quality loop:** offline evals from historical tickets; shadow A/B by source; weekly error analysis to tune prompts/tools
- **Dashboards:** deflection, FCR, TFR, backlog age, CSAT, cost/ticket by source; failure modes and override rates
- **Rollout:** Phase 1 Zendesk (agents only) → Phase 2 JSM → Phase 3 Support page end-user deflection; feature flags and auto-disable on breach

## Guardrails & Control Loops
- Policy tiers: read-only by default; action paths require explicit confirmation and safety checks
- SLO gates: canary windows, burn-rate alarms, health windows post-change
- Fallbacks: degrade gracefully — no silent failures
- Deterministic wrappers: retries, idempotency keys, bounded concurrency

Control-loop framing
- Sense: metrics/logs/traces, recent deploys, similar incidents
- Compare: error budgets, SLO targets, risk thresholds
- Act: suggest next step, or gated automation with rollbacks

---

## Assumptions & Alternatives
Assumptions
- Support platform exposes webhooks/APIs; KB exists but is fragmented
- Acceptable deflection target: 15–30% for L1 known-issues; human-in-loop required (PCR required)

Alternatives considered
- Rules-only triage (cheap, brittle) vs LLM classification + RAG (scalable, higher precision)
- “Copilot only” responses vs gated automation for simple actions (status lookups, resets)


---

## EKS, CI/CD, Rollout
- EKS Multi-AZ: autoscaling via Karpenter/Cluster Autoscaler; mTLS between services
- CI/CD: GitHub Actions → Bazel → container image → ArgoCD progressive delivery
- Feature flags: staged enablement by team/service; kill-switches
- Rollout plan: internal champions → single team → region → global


---

## Phased Rollout & Metrics (Support)
Phases
- Phase 0: Instrument baseline (deflection, FCR, TTR, backlog age, CSAT)
- Phase 1: Read-only assistant in agent console; auto-suggested replies; opt-in feedback
- Phase 2: End-user deflection on portal with confidence gates and safe topics
- Phase 3: Limited automation (e.g., status lookups) behind feature flags and audits

Success metrics
- Deflection rate, FCR, time-to-first-response, resolution time, CSAT, agent handle time
- Quality guardrails: false-positive deflections, override rate, hallucination incidents
- Scalability: QPS, cost/ticket, concurrency headroom, backlog distribution

Validation steps
- Offline eval set from historical tickets → acceptance thresholds
- Live shadow A/B in one queue → expand by cohort
- Red-team tests; guardrail monitors with auto-disable on breach


---

## Observability & Performance
- Tracing: end-to-end traces per user query (bot → ORCH → vendors)
- Metrics: p95 latency, deflection rate, FCR, time-to-first-response, backlog age, resolver accuracy, cost/query
- Logging: structured, redaction by policy, correlation IDs
- Profiling: eBPF/Pyroscope harness for CPU hot spots and tail latencies
- Performance playbook: pre-warm connections, parallel fetches, cache tiers

---

## Security by Default
- HMAC validation at ingress; strict header casing; raw-body signature
- Mutual TLS between internal services (certs via ACM)
- Secrets Manager with local cache TTLs; rotation schedules per secret class
- Rate limiting per vendor SLA; circuit breakers and timeouts

---

## Stakeholders & Governance
- Product & Support leadership: targets, deflection thresholds, CSAT safeguards
- Platform/SRE: reliability, cost, performance budgets, rollout gates
- Data Privacy/Legal/Sec: PII handling, retention, audit trails, model/data boundaries
- Change governance: RFCs, feature flags, staged rollouts, post-launch reviews

---

## Impact, Risks, Roadmap
Impact (targets and examples)
- MTTR: -20–35% in P1/P2 via faster context
- Ticket deflection: 15–30% of “known issue” L1 tickets
- Cost: model routing + cache lowers spend ~20% vs naive Sonnet-only

Risks & mitigations
- Hallucination: retrieval-augmented grounding + confidence bands; never automate irreversible actions
- Vendor limits: token bucket + SQS buffering; stale-but-acceptable caches
- Security drift: rotation audits, mTLS everywhere, IAM least privilege

Roadmap
- Toolformer-style action plugins with dry-run diffs
- Broader channel support; incident timeline summarizer
- Offline eval harness and regression suite in CI

---

## Demo Storyboard
1) Incident starts; on-call asks: “Why auth-api 503s?”
2) Bot replies with:
   - last deploys, error spikes, similar P0s
   - runbook link and 2 next-step options
3) Follow-up: “Show CPU/GC over last 15m” → inline chart
4) Optional gated action: “Rollback latest canary?” → safety checks → ArgoCD action → confirmation

---

## Q&A
- How do you prevent bad automation? Guardrails + human-in-the-loop + rollbacks
- What’s your eval strategy? Offline harness + live A/B + SLO watching
- How do you scale cost-effectively? Model routing, caching, SQS buffering, parallel fetches

---

## Appendix
- Full deep dive: [AI_SRE_ASSISTANT_README_INTERVIEW.md](./AI_SRE_ASSISTANT_README_INTERVIEW.md)
- Detailed system walk-through: [S -AI sre-assistant-deep-dive.md](./S%20-AI%20sre-assistant-deep-dive.md)
- Platform background & K8s operator: [R -Trustedpath.md](./R%20-Trustedpath.md)

Presenter notes
- Keep slides-to-sections pacing: ~1–2 min per section
- Use the Mermaid diagram as the visual anchor; everything else are short bullets
- If time-crunched, skip Appendix and Roadmap; preserve Guardrails + Observability
