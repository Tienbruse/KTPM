# Domain Analysis

## Overview
The legacy system implements a company-information assistant that collects raw datasets, indexes
company profiles into Elasticsearch, and exposes a conversational chatbot and UI that retrieves the
data via Retrieval-Augmented Generation (RAG). The monolith couples ingest, search, and dialogue
logic, which prevents independent scaling, deployments, and technology evolution.

## Identified Bounded Contexts

### 1. Data Acquisition & Processing
* **Responsibilities:** Crawling external sources, cleansing spreadsheets (`data/`), preparing
  records for indexing (current `indexer/` scripts).
* **Core concepts:** Raw company files, schema normalization, enrichment jobs, ingestion schedules.
* **Reason for separation:** Workloads are batch oriented and depend on external formats. They only
  interact with downstream systems through produced datasets. Release cadence differs from online
  services.

### 2. Catalog Indexing & Search
* **Responsibilities:** Managing Elasticsearch indices, building search queries, exposing structured
  search APIs. Currently handled inside `chatbot/src/services/query_creator.py` and
  `ElasticsearchService`.
* **Core concepts:** Searchable company document, query templates, ranking parameters.
* **Reason for separation:** Search tuning and infrastructure scaling (Elasticsearch, caching)
  benefit from isolated deployments. Search must be reusable by multiple channels (chatbot, UI,
  potential partner integrations).

### 3. Conversational Experience (Chatbot)
* **Responsibilities:** Entity extraction, LLM orchestration, dialogue state management, calling the
  search capability (now via HTTP) and formatting answers.
* **Core concepts:** Conversation session, extracted entities, RAG orchestration, memory store.
* **Reason for separation:** Requires rapid experimentation with prompts and models. Latency and
  availability requirements differ from batch ingestion. Needs clean API contract with search.

### 4. Presentation & UI
* **Responsibilities:** Streamlit UI (`ui/`) that calls chatbot APIs to present responses and collect
  feedback.
* **Reason for separation:** Front-end concerns (auth, branding, analytics) evolve independently and
  can be deployed separately.

### 5. Observability Platform
* **Responsibilities:** Centralized logging, metrics collection, tracing correlations. Currently
  absent; will be introduced as shared platform components (ELK stack already partially provisioned).

## Extraction Priorities
1. **Catalog Indexing & Search** – High coupling inside chatbot generates tight dependency on
   Elasticsearch credentials and query logic. Extracting first enables reuse and simplifies chatbot
   deployment.
2. **Data Acquisition & Processing** – Once search is externalized, ingestion can publish to search
   through API or message queues without touching chatbot code.
3. **Conversational Experience** – After core dependencies are external, the chatbot can be migrated
   to its own repository/service boundaries with clearer contracts.
4. **Presentation & UI** – Fewer backend dependencies; can be modernized in parallel once chatbot
   API is stable.
5. **Observability Platform** – Implemented alongside first services so that all new services emit
   unified telemetry from the start.

