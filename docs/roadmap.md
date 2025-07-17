# Podcast/YouTube Knowledge System – Full Project Plan & Roadmap  
> **Last updated:** 16 July 2025  

---

## 0  Executive Overview
* **Goal** — Make any spoken‑content channel instantly searchable and analyzable for arbitrarily‑phrased user questions.  
* **Latency / Cost targets** — `< 3 s P95`; `< $0.003` marginal OpenAI spend per query after caching.  
* **v1 scope** — Support YouTube, English language, single‑channel namespace (“My First Million”) across **≥ 500 episodes** using YouTube’s native transcripts wherever available.  
* **Key KPIs**

| Metric | Target |
| ------ | ------ |
| Precision@3 | ≥ 0.90 |
| MRR@5 | ≥ 0.85 |
| Server OpEx | ≤ $100 / month at 20 k queries |

---

## 1  System Architecture (bird’s‑eye)

```text
        ┌────────────┐
        │   Client   │─► HTTPS / JSON
        └────┬───────┘
             ▼
┌───────────────────────────┐
│  API Gateway / Router     │  (small GPT‑4o‑mini call)
└────┬──────────┬───────────┘
     │          │
     ▼          ▼
Pinpoint svc  Analytics svc
(RAG focus)   (Postgres views)
     │          │
     ├─► Vector / Keyword index
     │
     ▼
Postgres 16 (pgvector) + Blob store (S3/GCS)
```

---

## 2  Core Data Schemas (Phase 1)

| Table / Object  | Key fields                                              | Purpose                            |
| --------------- | ------------------------------------------------------- | ---------------------------------- |
| `episode`       | `id, title, channel_id, publish_dt, duration_s, url`    | Episode metadata                   |
| `chunk`         | `id, episode_id, start_s, end_s, text`                  | 30‑60 s spans for retrieval        |
| `chunk_embedding` | `chunk_id, vector(1536)`                              | Dense embedding                    |
| `entity`        | `id, type(PERSON/ORG/PRODUCT), canon_name`              | Canonical entity list              |
| `query_log`     | `ts, user_id, intent, latency_ms, token_cost`           | Observability                      |

> *Phase 2 backlog*: `entity_occurrence`, `attribute_score` (salience, sentiment, leaderboards).

---

## 3  Technology Stack

| Layer                 | Choice (Phase 1)                                        |
| --------------------- | ------------------------------------------------------- |
| **Ingestion workers** | Python 3.12 + Celery + Redis                            |
| **Transcript / ASR**  | **Pull YouTube transcript**; *Whisper tiny* fallback    |
| **Chunk & NLP**       | spaCy 3, NLTK, Pydantic                                 |
| **Embeddings**        | `text-embedding-3-small`                                |
| **Vector store**      | Postgres 16 + pgvector                                  |
| **Keyword search**    | Typesense (BM25 + HNSW rank‑fusion)                     |
| **Analytics store**   | Postgres views; *DuckDB‑on‑S3 arrives in Phase 2*       |
| **LLM inference**     | OpenAI GPT‑4o / GPT‑4o‑mini                              |
| **API layer**         | FastAPI + Uvicorn                                       |
| **CI / Tests**        | Pytest, Coverage, pre‑commit                            |
| **Observability**     | Structured JSON logs + StatsD/OTel → **single‑node Grafana Cloud** |
| **Deploy**            | Docker Compose (no Terraform hardening)                 |

---

## 4  Phased Implementation Roadmap (12 “day‑scale” sprints)

### Phase 1 – MVP value in ~8 sprints

| Sprint | Deliverables                                   | Key Tasks (excerpt)                                        | Acceptance tests |
| ------ | ---------------------------------------------- | ---------------------------------------------------------- | ---------------- |
| **0 Bootstrap** | Repo scaffolding, Compose, secrets vault                 | Create `ingest`, `search`; wire transcript fetch & Whisper tiny | Health endpoint |
| **1 Ingestion MVP** | 10 episodes → blob & `episode`                      | yt‑dl, transcript fetch, persist JSON                      | Text contains phrase |
| **2 Hybrid Search** | `/search/pinpoint` endpoint                         | Sentence split, embeddings + pgvector, BM25, GPT rerank    | Returns correct timestamp |
| **3 Entity Fusion (light)** | Canonical entity list                        | spaCy tagging, simple canonicalisation                     | Lists all Elon Musk mentions |
| **4 Intent Router & Enumerate** | `/enumerate` endpoint                   | GPT router, dedupe entities                                | “List every VC guest” |
| **5 Observability v1** | StatsD metrics, Grafana Cloud board              | Export latency, cost, error rates                          | Manual board check |
| **6 Golden‑Set CI** | Nightly `tests/golden_set.py`                       | 15 fixtures, Pytest + coverage                             | CI fails on mis‑ranking |
| **7 Scale‑out & Caching** | S3 storage, CloudFront edge cache             | Move blobs to S3, schedule nightly ingestion               | 100 qps < 300 ms |

### Phase 2 – Backlog (post‑MVP)

* `entity_occurrence` + salience & sentiment scoring  
* `attribute_score` and airtime / “attention‑minutes” leaderboards  
* DuckDB lakehouse + columnar analytics & `/trend`, `/compare` endpoints  
* Content helpers (`/clip`, `/quote_cards`)  
* Terraform or other IaC hardening; multi‑node observability

---

## 5  Detailed Module Reference

### 5.1 `ingest/`

| File            | Responsibility                                   |
| --------------- | ------------------------------------------------- |
| `discover.py`   | Find canonical feed IDs (YouTube API)             |
| `download.py`   | Fetch audio/MP4 + checksum                        |
| `transcribe.py` | **Use YouTube transcript; Whisper tiny fallback** |
| `chunker.py`    | 45 s windows, 25 % overlap                        |
| `ner.py`        | spaCy model + Wikidata linker                     |
| `embed.py`      | Batch embeddings                                  |

### 5.2 `search/`

| File            | Responsibility |
| --------------- | -------------- |
| `router.py`     | GPT function‑call → `{intent, attrs, corpus}` |
| `retrieval.py`  | Hybrid union (vector ∪ BM25)                  |
| `rerank.py`     | Cohere‑rerank‑v3 or GPT‑4o‑mini               |
| `pinpoint.py`…  | Endpoint pipelines                            |

### 5.3 `analytics/`

_Minimal in Phase 1 – raw SQL views over Postgres.  Extended views (salience, leaderboards) land in Phase 2._

### 5.4 `infra/`

Dockerfiles, Compose, StatsD/OTel exporters, Grafana Cloud dashboards.

---

## 6  Testing & QA Matrix

| Layer      | Tests                                               |
| ---------- | --------------------------------------------------- |
| Ingestion  | Transcript word‑count ≥ 0.9 × expected              |
| Retrieval  | Golden‑set precision/recall, MRR@5                 |
| Analytics  | Unit tests on Postgres views                        |
| E2E        | `curl` scripted user journeys; latency & token spend|
| Regression | Nightly full suite on sample feeds                  |

---

## 7  Observability & Cost Guardrails

* **Metrics** — `query_latency_ms`, `openai_input_tokens`, `openai_cost_usd`, `retrieved_chunks`, cache hit %.  
* **Alerts** (Grafana Cloud) — `p95_latency > 4 s / 5 min`, `daily_cost > $20`, ingestion lag.  
* **Logs** — FastAPI structured JSON (rotated daily, shipped via OTel).  

---

## 8  Security & Compliance

* Secrets loaded from environment at container start.  
* Rate‑limit: 2 req/s/user; JWT (placeholder).  
* Data retention: deletion of raw audio once finished with it.  
* Privacy: no end‑user personal data; log IDs are salted hashes.  

---

## 9  Future‑Proofing

* Language support via alternate Whisper + `language_id`.  
* Multi‑channel namespace (`channel_id` partition key).  
* Fine‑tuned embeddings (E5) once corpus > 50 k chunks.  
* Edge caching: Cloudflare Workers for static JSON.  
* Agent actions: expose `clip_audio`, `generate_deck` for copilots.  

---

## 10  Handover Package for AI Agents (Phase 1)

1. `README.md` – goals, KPIs, sprint table, run instructions  
2. `/docs/system_architecture.drawio` – architecture diagram  
3. `/docs/golden_set.json` – initial 15 Q/A fixtures  
4. `openapi.yaml` – contract covering `/search`, `/enumerate`, etc.  
5. `Makefile` – `make dev`, `make test`, `make deploy-dev`  

---

## 11  Agent‑by‑Agent Execution Script

| Phase          | Agent      | One‑liner prompt                                     |
| -------------- | ---------- | ---------------------------------------------------- |
| Scaffold       | **Codex**  | “Implement Sprint 0 Bootstrap per roadmap”           |
| Feature coding | **Claude** | Plan ➜ Act with guard‑rails                          |
| Infra & Docker | **Claude** | “Update Docker Compose and OTel exporters”           |
| Tests & CI     | **Cline**  | “Write param‑tests for retrieval.golden_set”         |
| Code review    | **Codex**  | “Review PR #X for performance regressions”           |

---

## 12  Coding Guard‑Rails & Hooks

```
.cursor/rules
- Use Python 3.12+ with type hints
- Run `ruff check . && ruff format .` after each write
- Run `pytest -q`; abort on failure
- Ask before adding deps
- No secrets / binaries > 2 MB
```

**Hooks**

```bash
/hooks add after_write "ruff check . && ruff format ."
/hooks add after_write "pytest -q || (echo 'Tests failed'; exit 1)"
```

---

## 13  Changelog Template

```md
## [Unreleased]
### Added
- ...
### Changed
- ...
### Fixed
- ...
```

---

## 14  Glossary

| Term          | Meaning |
| ------------- | ------- |
| **Pinpoint**  | RAG‑style question answering endpoint |
| **Enumerate** | Structured list extraction (guests, startups, etc.) |
| **Raw mention search** | Full‑text entity keyword search (Phase 1 baseline) |
| ~~Leaderboards~~ | *(Phase 2)* Ranking entities by airtime or sentiment |
| ~~Attribute score~~ | *(Phase 2)* Lazy‑filled adjective rating |
