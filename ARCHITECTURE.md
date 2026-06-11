# Sentinel — Architecture

Sentinel is a multi-agent **reasoning** system that performs incident root-cause
analysis. It is composed as a Microsoft Agent Framework workflow, runs on a
Microsoft Foundry reasoning deployment, and gathers live evidence through MCP
tool servers (Azure MCP + GitHub MCP). Every step is emitted to OpenTelemetry so
the reasoning is observable in the Foundry Control Plane.

## Reasoning flow

```mermaid
flowchart TB
    subgraph SRC[" "]
      A[Azure Monitor / PagerDuty alert]:::src
    end

    A -->|incident| ORCH

    subgraph FND["Microsoft Foundry  ·  Agent Service"]
      direction TB
      ORCH["Sentinel Orchestrator<br/>(Microsoft Agent Framework workflow)"]:::orch

      PL["🧭 Planner<br/>decompose → competing hypotheses"]:::agent

      subgraph FAN["INVESTIGATE — concurrent fan-out / fan-in"]
        direction LR
        LOG["🔎 Log Investigator"]:::agent
        CODE["🧬 Code Investigator"]:::agent
        INF["🖥️ Infra Investigator"]:::agent
      end

      SYN["🧮 Synthesizer<br/>eliminate hypotheses"]:::agent
      CRI["🧪 Critic<br/>adversarial self-review"]:::agent
      PM["📝 Postmortem Writer"]:::agent

      ORCH --> PL --> FAN --> SYN --> CRI
      CRI -- "needs follow-up<br/>(self-correction loop)" --> LOG
      CRI -- approved --> PM

      MODEL["Reasoning model<br/>GPT-5.2 / MAI-Thinking-1"]:::model
      PL -. reasons .- MODEL
      SYN -. reasons .- MODEL
      CRI -. reasons .- MODEL
    end

    subgraph MCP["MCP tool servers"]
      direction TB
      AZ["Azure MCP<br/>App Insights (KQL) · Azure Monitor · Activity Log"]:::tool
      GH["GitHub MCP<br/>commits · diffs · deploys"]:::tool
    end

    LOG <-->|exceptions, 5xx, deps| AZ
    INF <-->|metrics, config changes| AZ
    CODE <-->|recent deploys, diffs| GH

    AZ --- AZURE["Azure services<br/>AKS / Container Apps · Cosmos DB · Monitor"]:::az

    PM --> OUT["Postmortem + remediation<br/>→ on-call / incident channel"]:::out
    ORCH -. OpenTelemetry spans .-> OTEL["Foundry Control Plane<br/>traces · evals"]:::obs

    classDef src fill:#1f2937,stroke:#9ca3af,color:#fff;
    classDef orch fill:#0b3d91,stroke:#60a5fa,color:#fff;
    classDef agent fill:#111827,stroke:#34d399,color:#e5e7eb;
    classDef model fill:#3b0764,stroke:#c084fc,color:#fff;
    classDef tool fill:#7c2d12,stroke:#fb923c,color:#fff;
    classDef az fill:#0e7490,stroke:#67e8f9,color:#fff;
    classDef out fill:#064e3b,stroke:#34d399,color:#fff;
    classDef obs fill:#374151,stroke:#9ca3af,color:#fff;
```

## How the required stack is used

| Requirement | Where it shows up |
|-------------|-------------------|
| **Microsoft Foundry** | Hosts the reasoning model deployment; OpenTelemetry traces + evals land in the Foundry Control Plane (`tracing.py`, `.env`). |
| **Microsoft Agent Framework** | Six role agents composed with `WorkflowBuilder` fan-out/fan-in + a `MagenticBuilder` synthesize⇄critique loop (`maf_workflow.py`). |
| **Azure MCP** | Log Investigator + Infra Investigator query App Insights (KQL), Azure Monitor metrics, and the activity log through the Azure MCP server (`tools.py`, `mcp_client.py`). |
| **GitHub MCP** | Code Investigator correlates the incident with recent deploys/diffs via the hosted GitHub MCP server. |
| **Azure services** | The agent reasons over real Azure resources — AKS / Container Apps, Cosmos DB, Azure Monitor. |
| **GitHub Copilot** | Used to build the project (Foundry Toolkit for VS Code authoring path). |

## Why this is a *reasoning* agent, not a chatbot

1. **Hypothesis generation** — the Planner enumerates competing causes instead of pattern-matching one answer.
2. **Evidence-tagged investigation** — each finding explicitly *supports* or *refutes* specific hypotheses.
3. **Deductive elimination** — the Synthesizer removes refuted hypotheses and elevates the survivor.
4. **Adversarial self-correction** — the Critic refuses to commit until temporal causality is independently verified, sending the team back for a targeted follow-up (the loop edge above).
5. **Confidence-gated output** — a conclusion below 0.80 confidence is flagged for a human instead of asserted.

The same engine reaches *different* correct conclusions on different incidents
(`checkout_500` → bad deploy; `api_latency_infra` → resource exhaustion), which
is the proof it reasons over evidence rather than replaying a script.
