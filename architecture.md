# Architecture Design — Adaptive Reasoning Agent

> **Module 3:** Reasoning depth adapts to network; answer quality stays constant  
> **Stack:** Python 3.11 · FastAPI · React 18 · Qdrant · Mistral API

---

## 1. High-Level System Architecture

```mermaid
graph TB
    subgraph CLIENT["🖥️ Client Layer — React 18 + TypeScript"]
        UI[Chat UI]
        MS[Mode Selector<br/>Fast ∣ Standard ∣ Deep ∣ Auto]
        NI[Network Indicator<br/>🟢🟡🟠🔴]
        VI[Voice Input<br/>Web Speech API]
        DS[Document Sidebar<br/>Upload & List]
        DC[Download Cards<br/>PDF ∣ DOCX ∣ XLSX]
    end

    subgraph GATEWAY["🔌 Communication Layer"]
        WS[WebSocket<br/>Token Streaming]
        REST[REST API<br/>Fallback + Uploads]
        AUTH_MW[Auth Middleware<br/>JWT Validation]
    end

    subgraph BACKEND["⚙️ Backend — FastAPI"]
        subgraph CORE["🧠 Core Engine"]
            AGENT[Agent Orchestrator]
            NM[Network Monitor<br/>Latency Probing]
            QA[Query Analyzer<br/>Complexity Scoring]
            SS[Strategy Selector<br/>Decision Matrix]
        end

        subgraph REASONING["💭 Reasoning Engine"]
            FAST["⚡ Fast Mode<br/>Single-Pass"]
            STD["🔧 Standard Mode<br/>Step-Based"]
            DEEP["🔬 Deep Mode<br/>Multi-Step Analysis"]
        end

        subgraph TOOLS["🔨 Tool Layer"]
            TR[Tool Router]
            WEB_S[Web Search<br/>DuckDuckGo]
            WEB_D[Deep Search<br/>Tavily]
            DT[DateTime Tool]
            DG[Doc Generator<br/>PDF · DOCX · XLSX]
        end

        subgraph RAG["📚 RAG Pipeline — Native"]
            ING[Ingestion<br/>Parse → Chunk → Embed]
            RET[Retriever<br/>Search + Rerank]
        end

        subgraph SERVICES["🔧 Services"]
            MC[Mistral Client<br/>Async + Streaming]
            CB[Circuit Breaker]
            SESS[Session Store<br/>SQLite]
        end
    end

    subgraph EXTERNAL["☁️ External Services"]
        MISTRAL[Mistral API<br/>LLM + Embeddings]
        QDRANT[(Qdrant<br/>Vector DB)]
        DDG[DuckDuckGo API]
        TAV[Tavily API]
    end

    %% Client ↔ Gateway
    UI --> WS
    UI --> REST
    DS --> REST
    WS --> AUTH_MW
    REST --> AUTH_MW

    %% Gateway → Core
    AUTH_MW --> AGENT

    %% Core flow
    AGENT --> NM
    AGENT --> QA
    NM --> SS
    QA --> SS
    SS --> REASONING

    %% Reasoning → Tools & RAG
    FAST --> TR
    STD --> TR
    DEEP --> TR
    TR --> WEB_S
    TR --> WEB_D
    TR --> DT
    TR --> DG
    TR --> RET

    %% RAG
    ING --> QDRANT
    RET --> QDRANT
    ING -.-> MC

    %% Services
    FAST --> MC
    STD --> MC
    DEEP --> MC
    MC --> CB
    CB --> MISTRAL

    %% External
    WEB_S --> DDG
    WEB_D --> TAV
    NM -.->|HEAD /v1/models| MISTRAL

    %% Session
    AGENT --> SESS

    %% Styles
    classDef client fill:#dbeafe,stroke:#3b82f6,color:#1e3a5f
    classDef gateway fill:#fef3c7,stroke:#f59e0b,color:#78350f
    classDef core fill:#ede9fe,stroke:#8b5cf6,color:#4c1d95
    classDef reasoning fill:#dcfce7,stroke:#22c55e,color:#14532d
    classDef tools fill:#fce7f3,stroke:#ec4899,color:#831843
    classDef rag fill:#ffedd5,stroke:#f97316,color:#7c2d12
    classDef external fill:#f1f5f9,stroke:#64748b,color:#1e293b

    class UI,MS,NI,VI,DS,DC client
    class WS,REST,AUTH_MW gateway
    class AGENT,NM,QA,SS core
    class FAST,STD,DEEP reasoning
    class TR,WEB_S,WEB_D,DT,DG tools
    class ING,RET rag
    class MISTRAL,QDRANT,DDG,TAV external
```

---

## 2. Query Lifecycle — Data Flow

```mermaid
sequenceDiagram
    actor User
    participant UI as React UI
    participant WS as WebSocket
    participant Auth as Auth Middleware
    participant Agent as Agent Orchestrator
    participant NM as Network Monitor
    participant QA as Query Analyzer
    participant SS as Strategy Selector
    participant RE as Reasoning Engine
    participant Tools as Tool Router
    participant RAG as RAG Retriever
    participant MC as Mistral Client
    participant Mistral as Mistral API

    User->>UI: Types query + selects mode
    UI->>WS: Send chat_message
    WS->>Auth: Validate JWT
    Auth->>Agent: Authenticated request

    par Parallel Assessment
        Agent->>NM: Fast probe (HEAD request)
        NM->>Mistral: HEAD /v1/models
        Mistral-->>NM: Latency measurement
        NM-->>Agent: Network tier (🟢🟡🟠🔴)
    and
        Agent->>QA: Analyze query complexity
        QA-->>Agent: Complexity tier (LOW/MED/HIGH)
    end

    Agent->>SS: Network tier + Complexity + User override
    SS-->>Agent: Selected mode (Fast/Standard/Deep)

    Agent->>WS: reasoning_step: "Mode selected"
    Agent->>RE: Execute with selected mode

    alt ⚡ Fast Mode
        RE->>RAG: Get top-3 chunks
        RAG-->>RE: Context
        RE->>MC: Single LLM call (stream)
        MC->>Mistral: Chat completion
        Mistral-->>MC: Token stream
        MC-->>WS: Stream tokens
    else 🔧 Standard Mode
        RE->>MC: Step 1 — Plan (JSON)
        MC-->>RE: Plan with tool list
        RE->>WS: reasoning_step: "Planning..."
        RE->>Tools: Execute planned tools
        Tools-->>RE: Tool results
        RE->>WS: reasoning_step: "Synthesizing..."
        RE->>MC: Step 2 — Synthesize
        MC-->>WS: Stream tokens
    else 🔬 Deep Mode
        RE->>MC: Step 1 — Decompose into sub-questions
        MC-->>RE: Sub-questions
        RE->>WS: reasoning_step: "Decomposing..."
        loop Each Sub-Question
            par Research
                RE->>RAG: Targeted retrieval
                RE->>Tools: Web search
            end
            RE->>MC: Answer sub-question
        end
        RE->>WS: reasoning_step: "Synthesizing..."
        RE->>MC: Step 3 — Synthesize
        RE->>WS: reasoning_step: "Verifying..."
        RE->>MC: Step 4 — Verify & Refine
        MC-->>WS: Stream final answer
    end

    WS-->>UI: done + metadata
    UI-->>User: Complete response + reasoning steps
```

---

## 3. Reasoning Mode Selection — Decision Flow

```mermaid
flowchart TD
    START([User Query Arrives]) --> PROBE[/"🌐 Network Probe<br/>HEAD → Mistral API"/]
    START --> ANALYZE[/"📊 Query Complexity<br/>Heuristic Analysis"/]

    PROBE --> TIER{Network Tier?}
    TIER -->|"< 300ms, 0% err"| EXCELLENT["🟢 EXCELLENT"]
    TIER -->|"300–800ms, < 10% err"| GOOD["🟡 GOOD"]
    TIER -->|"800–2000ms, < 30% err"| FAIR["🟠 FAIR"]
    TIER -->|"> 2000ms or > 30% err"| POOR["🔴 POOR"]

    ANALYZE --> COMPLEXITY{Query Complexity?}
    COMPLEXITY -->|"< 10 words, simple"| LOW["LOW"]
    COMPLEXITY -->|"10–30 words, some analysis"| MEDIUM["MEDIUM"]
    COMPLEXITY -->|"> 30 words, multi-part"| HIGH["HIGH"]

    EXCELLENT --> MATRIX["🎯 Decision Matrix"]
    GOOD --> MATRIX
    FAIR --> MATRIX
    POOR --> MATRIX
    LOW --> MATRIX
    MEDIUM --> MATRIX
    HIGH --> MATRIX

    MATRIX --> OVERRIDE{User Override?}
    OVERRIDE -->|"Yes — forced mode"| FORCED[Use Forced Mode]
    OVERRIDE -->|"No — auto"| AUTO_SELECT

    AUTO_SELECT{Matrix Result}
    AUTO_SELECT -->|"POOR + any<br/>FAIR + LOW"| FAST_MODE["⚡ Fast Mode<br/>1 LLM call · ~500 tokens<br/>1–3s latency"]
    AUTO_SELECT -->|"FAIR + MED/HIGH<br/>GOOD + LOW/MED<br/>EXCELLENT + LOW"| STD_MODE["🔧 Standard Mode<br/>2–3 LLM calls · ~1500 tokens<br/>4–10s latency"]
    AUTO_SELECT -->|"GOOD + HIGH<br/>EXCELLENT + MED/HIGH"| DEEP_MODE["🔬 Deep Mode<br/>4–6 LLM calls · ~4000 tokens<br/>15–45s latency"]

    FORCED --> EXECUTE[Execute Reasoning Pipeline]
    FAST_MODE --> EXECUTE
    STD_MODE --> EXECUTE
    DEEP_MODE --> EXECUTE

    style FAST_MODE fill:#fef9c3,stroke:#eab308,color:#713f12
    style STD_MODE fill:#dbeafe,stroke:#3b82f6,color:#1e3a5f
    style DEEP_MODE fill:#dcfce7,stroke:#22c55e,color:#14532d
    style MATRIX fill:#ede9fe,stroke:#8b5cf6,color:#4c1d95
    style START fill:#f8fafc,stroke:#64748b
```

---

## 4. RAG Pipeline — Ingestion & Retrieval

```mermaid
flowchart LR
    subgraph INGESTION["📥 Ingestion Pipeline"]
        UPLOAD["📎 User Upload"] --> DETECT{Format?}
        DETECT -->|PDF| PDF_P["PyMuPDF<br/>Page-by-page"]
        DETECT -->|DOCX| DOCX_P["python-docx<br/>Paragraph-level"]
        DETECT -->|TXT| TXT_P["Built-in<br/>Encoding detection"]
        DETECT -->|CSV| CSV_P["csv module<br/>Row + headers"]

        PDF_P --> CLEAN["🧹 Text Cleaning"]
        DOCX_P --> CLEAN
        TXT_P --> CLEAN
        CSV_P --> CLEAN

        CLEAN --> CHUNK["✂️ Recursive Chunker<br/>512 tokens · 50 overlap"]
        CHUNK --> EMBED["🔢 mistral-embed<br/>1024-dim · batch=16"]
        EMBED --> STORE[("💾 Qdrant Upsert<br/>+ metadata")]
    end

    subgraph RETRIEVAL["📤 Retrieval Pipeline"]
        QUERY["🔍 User Query"] --> Q_EMBED["🔢 Embed Query<br/>mistral-embed"]
        Q_EMBED --> SEARCH["Vector Search<br/>Cosine Similarity"]
        SEARCH --> STORE
        STORE --> RESULTS["Raw Results"]
        RESULTS --> FILTER["🔒 Filter by user_id"]
        FILTER --> RERANK{"Reranking?"}
        RERANK -->|"Fast: skip"| TOP3["Top-3 chunks"]
        RERANK -->|"Standard: keyword"| TOP5["Top-5 + keyword boost"]
        RERANK -->|"Deep: multi-query"| TOP10["Top-10 + sub-question queries"]
    end

    TOP3 --> CONTEXT["📄 Assembled Context"]
    TOP5 --> CONTEXT
    TOP10 --> CONTEXT
    CONTEXT --> LLM["🧠 → Reasoning Engine"]

    style INGESTION fill:#fff7ed,stroke:#f97316
    style RETRIEVAL fill:#f0f9ff,stroke:#0ea5e9
```

---

## 5. Error Handling & Graceful Degradation

```mermaid
flowchart TD
    subgraph ERRORS["⚠️ Failure Points"]
        E1["Mistral API Timeout"]
        E2["Mistral Rate Limit 429"]
        E3["Mistral Server Error 5xx"]
        E4["Qdrant Unavailable"]
        E5["Web Search Fails"]
        E6["Doc Parse Error"]
        E7["Network Probe Timeout"]
        E8["WebSocket Disconnect"]
    end

    subgraph CIRCUIT["🔌 Circuit Breaker"]
        CB_CLOSED["CLOSED<br/>Normal operation"]
        CB_OPEN["OPEN<br/>Fail fast, skip calls"]
        CB_HALF["HALF-OPEN<br/>Test with single call"]

        CB_CLOSED -->|"failures > threshold"| CB_OPEN
        CB_OPEN -->|"cooldown elapsed"| CB_HALF
        CB_HALF -->|"test succeeds"| CB_CLOSED
        CB_HALF -->|"test fails"| CB_OPEN
    end

    subgraph DEGRADATION["📉 Degradation Chain"]
        D_DEEP["🔬 Deep Mode Fails"] -->|"Salvage sub-answers"| D_STD["🔧 Fallback → Standard"]
        D_STD -->|"Planning fails"| D_FAST["⚡ Fallback → Fast"]
        D_FAST -->|"LLM unreachable"| D_CACHE["📦 Cached / Partial Response"]
        D_CACHE -->|"Nothing available"| D_ERROR["❌ User-friendly Error<br/>+ retry suggestion"]
    end

    E1 --> |"Retry once"| RETRY1{Success?}
    RETRY1 -->|No| DEGRADATION
    RETRY1 -->|Yes| CONTINUE["✅ Continue"]

    E2 --> |"Backoff: 1s→2s→4s"| RETRY2{Success?}
    RETRY2 -->|No| DEGRADATION
    RETRY2 -->|Yes| CONTINUE

    E3 --> |"Retry once"| RETRY3{Success?}
    RETRY3 -->|No| D_ERROR

    E4 --> SKIP_RAG["Skip RAG<br/>Answer without docs"]
    E5 --> SKIP_WEB["Skip web results<br/>Use RAG + LLM knowledge"]
    E6 --> USER_MSG["Notify user<br/>Suggest re-upload"]
    E7 --> DEFAULT_POOR["Default → POOR tier<br/>Use Fast mode"]
    E8 --> AUTO_RECONNECT["Auto-reconnect<br/>Exponential backoff"]

    style ERRORS fill:#fef2f2,stroke:#ef4444
    style CIRCUIT fill:#fefce8,stroke:#eab308
    style DEGRADATION fill:#faf5ff,stroke:#a855f7
```

---

## 6. Tool Routing Architecture

```mermaid
flowchart TD
    AGENT["🧠 Agent Orchestrator"] --> TR["🔀 Tool Router"]

    TR --> BUDGET{Mode Budget?}

    BUDGET -->|"⚡ Fast: 0–1 tools"| FAST_TOOLS["DateTime only<br/>(if explicitly asked)"]
    BUDGET -->|"🔧 Standard: 1–2 tools"| STD_TOOLS["Selected by<br/>planning step"]
    BUDGET -->|"🔬 Deep: All tools"| DEEP_TOOLS["Full suite<br/>parallel execution"]

    STD_TOOLS --> DISPATCH
    DEEP_TOOLS --> DISPATCH
    FAST_TOOLS --> DISPATCH

    DISPATCH["🚀 Dispatcher"]

    DISPATCH --> WS_TOOL["🌐 Web Search<br/>DuckDuckGo<br/>Shallow retrieval"]
    DISPATCH --> WD_TOOL["🔎 Deep Search<br/>Tavily API<br/>Research-grade"]
    DISPATCH --> DT_TOOL["🕐 DateTime<br/>Local call<br/>Zero latency"]
    DISPATCH --> RAG_TOOL["📚 RAG<br/>Qdrant retrieval<br/>User documents"]
    DISPATCH --> DOC_TOOL["📄 Doc Generator<br/>PDF · DOCX · XLSX<br/>Template-based"]

    WS_TOOL --> RESULTS["📋 Tool Results"]
    WD_TOOL --> RESULTS
    DT_TOOL --> RESULTS
    RAG_TOOL --> RESULTS
    DOC_TOOL --> RESULTS

    RESULTS --> RE["🧠 Reasoning Engine<br/>Synthesis step"]

    style TR fill:#ede9fe,stroke:#8b5cf6
    style DISPATCH fill:#dbeafe,stroke:#3b82f6
```

---

## 7. Design Patterns Map

```mermaid
graph LR
    subgraph PATTERNS["🏗️ Design Patterns"]
        P1["♟️ Strategy"]
        P2["🔗 Chain of<br/>Responsibility"]
        P3["👁️ Observer"]
        P4["🏭 Factory"]
        P5["🔌 Circuit Breaker"]
        P6["📦 Repository"]
        P7["🔄 Pipeline"]
        P8["🔌 Adapter"]
        P9["1️⃣ Singleton"]
        P10["🎀 Decorator"]
    end

    subgraph APPLIED["Applied To"]
        A1["Reasoning Modes<br/>Fast / Standard / Deep"]
        A2["Degradation Chain<br/>Deep → Std → Fast"]
        A3["Network Monitor →<br/>Strategy Selector"]
        A4["Tool creation<br/>Doc generation"]
        A5["Mistral API calls<br/>Web search calls"]
        A6["Qdrant operations"]
        A7["RAG ingestion<br/>Reasoning steps"]
        A8["DuckDuckGo / Tavily<br/>uniform interface"]
        A9["Network Monitor<br/>Qdrant Client"]
        A10["Auth middleware<br/>Logging · Metrics"]
    end

    P1 --- A1
    P2 --- A2
    P3 --- A3
    P4 --- A4
    P5 --- A5
    P6 --- A6
    P7 --- A7
    P8 --- A8
    P9 --- A9
    P10 --- A10

    style PATTERNS fill:#f0fdf4,stroke:#22c55e
    style APPLIED fill:#eff6ff,stroke:#3b82f6
```

---

## 8. Deployment Architecture

```mermaid
graph TB
    subgraph DOCKER["🐳 Docker Compose"]
        subgraph FE_CONTAINER["frontend"]
            NGINX["Nginx<br/>:80"]
            REACT["React Build<br/>Static Assets"]
        end

        subgraph BE_CONTAINER["backend"]
            UVICORN["Uvicorn<br/>:8000"]
            FASTAPI["FastAPI App"]
            SQLITE[("SQLite<br/>Sessions & Auth")]
        end

        subgraph QD_CONTAINER["qdrant"]
            QD_ENGINE["Qdrant Engine<br/>:6333 REST<br/>:6334 gRPC"]
            QD_STORAGE[("Vector Storage")]
        end
    end

    USER["👤 User Browser"] -->|":80"| NGINX
    NGINX -->|"proxy /api/*<br/>proxy /ws/*"| UVICORN
    FASTAPI --> QD_ENGINE
    FASTAPI -->|"HTTPS"| MISTRAL_EXT["☁️ Mistral API"]
    FASTAPI -->|"HTTPS"| SEARCH_EXT["☁️ DuckDuckGo / Tavily"]

    style DOCKER fill:#f8fafc,stroke:#475569
    style FE_CONTAINER fill:#dbeafe,stroke:#3b82f6
    style BE_CONTAINER fill:#dcfce7,stroke:#22c55e
    style QD_CONTAINER fill:#fef3c7,stroke:#f59e0b
```

---

## 9. Project Structure

```
adaptive-reasoning-agent/
├── backend/
│   ├── main.py                    # FastAPI entry point
│   ├── config.py                  # pydantic-settings configuration
│   ├── api/
│   │   ├── auth.py                # Login, register, JWT
│   │   ├── chat.py                # WebSocket + REST chat
│   │   ├── documents.py           # Upload, list, delete docs
│   │   └── downloads.py           # Serve generated files
│   ├── core/
│   │   ├── agent.py               # Main orchestrator
│   │   ├── network_monitor.py     # Latency probing & tiers
│   │   ├── query_analyzer.py      # Complexity heuristics
│   │   ├── strategy_selector.py   # Decision matrix
│   │   ├── reasoning/
│   │   │   ├── base.py            # Abstract reasoning interface
│   │   │   ├── fast.py            # ⚡ Single-pass
│   │   │   ├── standard.py        # 🔧 Step-based
│   │   │   └── deep.py            # 🔬 Multi-step
│   │   └── prompts/
│   │       ├── fast_prompts.py
│   │       ├── standard_prompts.py
│   │       └── deep_prompts.py
│   ├── tools/
│   │   ├── router.py              # Tool dispatcher
│   │   ├── base.py                # Abstract tool interface
│   │   ├── web_search.py          # DuckDuckGo
│   │   ├── web_deep.py            # Tavily
│   │   ├── datetime_tool.py       # Date/time
│   │   └── doc_generator.py       # PDF, DOCX, XLSX
│   ├── rag/
│   │   ├── ingestion.py           # Upload handling
│   │   ├── parser.py              # PDF, DOCX, TXT, CSV
│   │   ├── chunker.py             # Recursive splitting
│   │   ├── embedder.py            # Mistral embeddings
│   │   ├── vector_store.py        # Qdrant operations
│   │   └── retriever.py           # Search + reranking
│   ├── auth/
│   │   ├── jwt_handler.py         # Token create/validate
│   │   └── middleware.py          # Auth middleware
│   ├── models/
│   │   ├── schemas.py             # Pydantic models
│   │   └── enums.py               # Tiers, modes, tools
│   ├── services/
│   │   ├── mistral_client.py      # Async Mistral wrapper
│   │   ├── session_store.py       # SQLite history
│   │   └── circuit_breaker.py     # Failure protection
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── ChatWindow.tsx
│   │   │   ├── MessageBubble.tsx
│   │   │   ├── NetworkIndicator.tsx
│   │   │   ├── ModeSelector.tsx
│   │   │   ├── ReasoningSteps.tsx
│   │   │   ├── DocumentSidebar.tsx
│   │   │   ├── VoiceInput.tsx
│   │   │   └── DownloadCard.tsx
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts
│   │   │   ├── useVoice.ts
│   │   │   └── useAuth.ts
│   │   └── stores/
│   │       └── chatStore.ts
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml
├── architecture.md                # ← This document
└── README.md
```
