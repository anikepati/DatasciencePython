# Browser Agent Gen AI Application: System Design and Flow Presentation

This presentation outlines the system design and detailed flows for the Browser Agent, a generative AI-powered SaaS platform for enterprise browser automation. It is tailored for executives, senior leaders, and architects, focusing on modular architecture, end-to-end flows, scalability, and security. Diagrams are provided as Mermaid code for interactive rendering (e.g., in mermaid.live or integrated tools).

---

### Slide 1: Title
**Browser Agent: Generative AI Platform for Enterprise Browser Automation**  
- **Overview**: A modular, scalable SaaS solution to automate SOP-based browser tasks using Gen AI, with risk-based execution and full observability.  
- **Audience Focus**: High-level design for strategic alignment; flows and diagrams for architectural depth.

---

### Slide 2: System Overview
**Core Design Principles**:  
- **Modularity**: Three independent modules (Ingestion, Execution, Observability & Evaluations) for targeted scaling and maintenance.  
- **AI Integration**: GADK (Google Agent Development Kit) for agent planning, skill generation, and dynamic execution.  
- **Risk-Based Routing**: Low/medium-risk SOPs run headless on OCP; high-risk via installer on Cloud PCs with manual HITL.  
- **Data Handling**: Centralized PostgreSQL for configs/skills; sharded for high-volume tasks/work items.  
- **Inputs/Outputs**: Work items via Excel (batch), Kafka (streaming), REST APIs (on-demand); outputs include logs, evaluations, and evidence (e.g., screenshots).

**Technologies**:  
- AI/Backend: GADK, Python, Playwright.  
- DB: PostgreSQL (sharded).  
- Frontend: ReactJS, Streamlit.  
- Infra: OCP/K8s, Cloud PCs (e.g., Azure/AWS VMs).

---

### Slide 3: Modular System Design
**Three Core Modules**:  

1. **Ingestion Module**:  
   - Handles SOP source uploads and AI-driven config/skill generation.  
   - Flow: Upload → AI Extraction → Storage.  
   - Scale: Serverless for variable loads.  

2. **Execution Module**:  
   - Manages scheduling, work item processing, and risk-routed runtimes.  
   - Flow: Login/Schedule → Work Item Ingestion → Orchestration → Runtime Execution.  
   - Scale: Auto-scaling pods for headless; on-demand VMs for high-risk.  

3. **Observability & Evaluations Module**:  
   - Provides monitoring, logging, alerting, and AI/manual evaluations.  
   - Flow: Event Capture → Analysis → Dashboards/Alerts.  
   - Scale: Distributed systems (e.g., Prometheus cluster).  

**Shared Elements**:  
- PostgreSQL DB: Centralized for consistency; sharded partitions for performance.  
- API Gateway: Secure inter-module communication with RBAC.

---

### Slide 4: High-Level System Design Diagram
**Overall Architecture Diagram**  
This diagram shows module interactions, data flows, and shared infrastructure.

```mermaid
graph TD
    %% Module 1: Ingestion
    subgraph Ingestion ["Module 1: Ingestion"]
        UP_SRC[User Uploads SOP Sources<br/>(Videos/Docs/CSVs via ReactJS)]
        ING_SVC[Ingestion Service<br/>Python + GADK]
        SKILL_GEN[Generate Skills/Configs<br/>w/ Risk Levels]
        UP_SRC --> ING_SVC --> SKILL_GEN --> DB[PostgreSQL Central DB<br/>SOPs, Skills, Configs]
    end

    %% Module 2: Execution
    subgraph Execution ["Module 2: Execution"]
        LOGIN[User Login<br/>ReactJS Dashboard]
        WORK_UP[Upload Work Items<br/>(Excel/Kafka/REST APIs)]
        SCHED_MGR[Manage Scheduler<br/>Cron/Continuous Triggers]
        HITL_VAL[HITL Validation/Rerun<br/>Specific Work Items]
        ORCH[Orchestrator<br/>Map to Skills/Work Items]
        LOGIN --> WORK_UP & SCHED_MGR & HITL_VAL
        WORK_UP --> DB_SHARD[Sharded Work Items DB]
        SCHED_MGR --> ORCH
        ORCH -->|Low/Medium Risk| OCP[OCP Headless Servers<br/>Playwright Automated]
        ORCH -->|High Risk| INSTALL[Provide Installer<br/>for Cloud PC]
        INSTALL --> CLOUD_PC[Cloud PC Runtime<br/>Headless=False + Streamlit HITL<br/>Manual Start/Stop + End-to-End Process]
        OCP --> PLAY[Playwright Browser]
        CLOUD_PC --> PLAY
        HITL_VAL --> CLOUD_PC
        ORCH -->|Fetch Configs/Skills| DB
        DB_SHARD --> ORCH
    end

    %% Module 3: Observability & Evaluations
    subgraph ObsEval ["Module 3: Observability & Evaluations"]
        MON_DASH[Monitoring Dashboard<br/>ReactJS/Streamlit]
        LOG_ALERT[Logging & Alerting<br/>Prometheus/ELK]
        EVAL_ENG[Evaluation Engine<br/>AI Scoring + Manual Review]
        MON_DASH --> LOG_ALERT & EVAL_ENG
    end

    %% Cross-Module Flows
    ING_SVC --> LOG_ALERT
    ORCH --> LOG_ALERT
    OCP --> LOG_ALERT
    CLOUD_PC --> LOG_ALERT
    EVAL_ENG -->|Post-Execution| DB_SHARD
    MON_DASH -->|View| DB & DB_SHARD

    %% Shared
    subgraph Shared ["Shared Infrastructure"]
        DB
        DB_SHARD
    end
```

**Diagram Insights**:  
- Flows emphasize separation: Ingestion feeds Execution via DB; Observability captures all events.  
- RBAC enforced at gateways and DB levels.

---

### Slide 5: Detailed Flow - Ingestion Module
**End-to-End Ingestion Flow**:  
1. User uploads SOP sources (e.g., video demo + document) via ReactJS interface.  
2. Ingestion Service (Python) processes: Extract transcripts/frames using libraries (e.g., FFmpeg/OpenCV).  
3. GADK AI generates skills (e.g., "navigate form") and configs, including risk level classification.  
4. Store in centralized PostgreSQL (e.g., skills table with JSON contexts).  
5. Notify Observability for logging; ready for Execution module.

**Key Design Notes**:  
- AI-Driven: GADK handles extraction to ensure reusable, modular skills.  
- Scale: Asynchronous queues for large sources; no blocking.

---

### Slide 6: Detailed Flow - Execution Module
**End-to-End Execution Flow**:  
1. User logs in via ReactJS; manages schedulers (cron for periodic, Kafka for continuous, APIs for on-demand).  
2. Upload work items: Parse Excel batches, stream from Kafka, or ingest via REST; store in sharded DB (e.g., by batch_id).  
3. Orchestrator triggers: Maps work items to SOPs/skills from central DB.  
4. Risk Routing:  
   - Low/Medium: Deploy to OCP headless pods; auto-execute Playwright steps.  
   - High: Provide downloadable installer; user installs on Cloud PC, pulls config, runs non-headless with Streamlit UI for manual start/stop and end-to-end HITL.  
5. HITL/Validation: Streamlit prompts for approvals; rerun specific items via dashboard API.  
6. Update states in sharded DB; feed evidence (screenshots) to storage.

**Flow Diagram**:

```mermaid
flowchart TD
    A[Start: User Login & Scheduler Setup] --> B[Ingest Work Items<br/>(Excel Batch / Kafka Stream / REST API)]
    B --> C[Store in Sharded DB<br/>Batch Grouping & Status Tracking]
    C --> D[Orchestrator Trigger<br/>Map to SOPs/Skills]
    D --> E{SOP Risk Level?}
    E -->|Low/Medium| F[OCP Headless Execution<br/>Playwright Automation<br/>Process 1000s Items]
    E -->|High| G[Download Installer<br/>Deploy to Cloud PC]
    G --> H[Run Non-Headless Mode<br/>Streamlit HITL UI<br/>Manual Start/Stop + Validation]
    H --> I[Rerun Specific Items if Needed]
    F --> J[Update DB States & Evidence]
    I --> J
    J --> K[End: Feed to Observability]
```

**Design Notes**:  
- Resilience: Retries for failures; idempotent work items.  
- Performance: Parallel processing in OCP; manual controls for high-risk compliance.

---

### Slide 7: Detailed Flow - Observability & Evaluations Module
**End-to-End Observability Flow**:  
1. All modules emit events (e.g., ingestion complete, execution step failed) to centralized collector.  
2. Logging/Alerting: Prometheus for metrics (e.g., throughput, latency); ELK for logs; configurable alerts (e.g., error thresholds).  
3. Evaluations: Post-execution AI scoring via GADK (e.g., output accuracy); manual review in Streamlit dashboard.  
4. Dashboards: ReactJS for real-time views (queues, success rates); exportable reports.  
5. Feedback Loop: Evaluations update skills/SOPs in central DB for iterative improvement.

**Design Notes**:  
- Full Coverage: Traces from ingestion to execution outputs.  
- AI-Enhanced: GADK for anomaly detection in evaluations.

---

### Slide 8: Scalability and Security Design
**Scalability Features**:  
- **Ingestion**: Serverless functions for peak loads.  
- **Execution**: K8s HPA (Horizontal Pod Autoscaler) on OCP; sharded DB (e.g., Citus) for 10M+ tasks/month.  
- **Observability**: Distributed clusters; auto-scaling collectors.  
- **Overall**: Multi-tenant isolation via DB schemas; geo-redundancy.

**Security Features**:  
- **RBAC**: Role enforcement (e.g., Admin for configs, Operator for HITL).  
- **Encryption**: Data at rest/transit; vaulted credentials.  
- **Compliance**: Audit trails in DB; risk routing isolates sensitive ops.  
- **Threat Model**: API gateways with rate limiting; zero-trust for Cloud PC installs.

---

### Slide 9: Roadmap and Implementation Considerations
**Phased Rollout**:  
- **Phase 1**: Ingestion + Low-Risk Execution.  
- **Phase 2**: High-Risk HITL + Full Observability.  
- **Phase 3**: Advanced Integrations (e.g., enterprise APIs).

**Implementation Notes for Architects**:  
- Microservices: Each module deployable independently.  
- Testing: End-to-end flows with mocks; load testing for sharding.  
- Monitoring: Built-in from Day 1.

**Q&A**: Open for discussions on design trade-offs, flows, or customizations.
