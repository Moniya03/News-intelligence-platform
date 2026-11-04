# 📡 REST API Reference

The **Multilingual News Intelligence Platform** exposes a high-performance RESTful API built on **FastAPI**. All endpoints run under the `/api` prefix (with the exception of root probes and documentation).

---

## 🌐 General Information

- **Base URL**: `http://localhost:8000`
- **Interactive OpenAPI Documentation (Swagger UI)**: `http://localhost:8000/docs`
- **Alternative ReDoc UI**: `http://localhost:8000/redoc`
- **Content-Type**: `application/json` (for all POST request bodies and responses)
- **CORS Support**: Enabled for all origins (`allow_origins=["*"]`) to support modern frontend clients.

---

## 📋 Endpoint Summary

| HTTP Method | Path | Summary | Description |
|---|---|---|---|
| `GET` | `/` | Root Probe | Service identification and version check |
| `GET` | `/api/health` | Health Check | Validates backend connectivity to MongoDB and Weaviate |
| `POST` | `/api/search` | Multilingual Search | Retrieves news articles across Hybrid, Dense, or BM25 modes |
| `POST` | `/api/chat` | RAG Synthesis | Multilingual RAG with grounded citations and veracity check |
| `GET` | `/api/clusters` | List Clusters | Discovered cross-lingual topic and event clusters |
| `GET` | `/api/clusters/{id}` | Cluster Details | Paginated member articles and language distribution |

---

## 1. Root Probe

### `GET /`
Provides basic service identity, version string, and a pointer to the interactive OpenAPI documentation.

#### Request Example
```bash
curl -X GET "http://localhost:8000/"
```

#### Response (`200 OK`)
```json
{
  "name": "Multilingual News Intelligence Platform API",
  "version": "1.0.0",
  "status": "online",
  "docs_url": "/docs"
}
```

---

## 2. Health Probe

### `GET /api/health`
Probes active database connections to verify that the backend is operational and ready to serve queries.

#### Request Example
```bash
curl -X GET "http://localhost:8000/api/health"
```

#### Response (`200 OK`)
```json
{
  "status": "ok",
  "services": {
    "mongodb": true,
    "weaviate": true
  }
}
```

#### Response Attributes:
- `status` (`string`): Overall system operational flag (`"ok"`).
- `services.mongodb` (`boolean`): `true` if MongoDB ping succeeded, `false` otherwise.
- `services.weaviate` (`boolean`): `true` if Weaviate `is_ready()` or `is_live()` succeeded, `false` otherwise.

---

## 3. Multilingual Search

### `POST /api/search`
Executes high-speed information retrieval over indexed multilingual news articles. Supports **Hybrid**, **Dense**, and **BM25** search modes, along with optional language filtering.

#### Request Headers
```http
Content-Type: application/json
```

#### Request Body Schema (`SearchRequest`)

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `query` | `string` | **Yes** | — | Search query string (can be in English, Hindi, Bengali, or Tamil). |
| `lang_filter` | `list[string]` | No | `null` | Optional list of language codes to filter: `["en", "hi", "bn", "ta"]`. |
| `mode` | `string` | No | `"hybrid"` | Retrieval mode. Allowed values: `"hybrid"`, `"dense"`, `"bm25"`. |
| `top_k` | `integer` | No | `10` | Number of ranked results to return (min: 1, max: 50). |

#### Request Example: Hybrid Search
```bash
curl -X POST "http://localhost:8000/api/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "solar energy grid modernization and transmission",
    "lang_filter": ["en", "hi"],
    "mode": "hybrid",
    "top_k": 3
  }'
```

#### Response (`200 OK`)
```json
{
  "results": [
    {
      "article_id": "en_000101",
      "title": "India Advances Clean Energy Infrastructure with New Grid Modernization Initiative",
      "lang": "en",
      "source": "l3cube-indicnews",
      "category": "technology",
      "snippet": "New renewable integration policies target expanded solar and wind capacities across western and southern regional grids, improving reliability and inter-state transmission efficiency.",
      "score": 0.94,
      "url": "https://news.example.com/clean-energy-grid"
    },
    {
      "article_id": "hi_000102",
      "title": "सौर ऊर्जा ग्रिड विस्तार: पश्चिमी राज्यों में अंतर्राज्यीय पारेषण परियोजना का शुभारंभ",
      "lang": "hi",
      "source": "l3cube-indicnews",
      "category": "energy",
      "snippet": "नवीन एवं नवीकरणीय ऊर्जा मंत्रालय ने क्षेत्रीय ग्रिड के आधुनिकीकरण के लिए नई पारेषण लाइनों की स्थापना को मंजूरी दी है।",
      "score": 0.89,
      "url": "https://news.example.com/solar-grid-hi"
    }
  ]
}
```

---

## 4. Conversational RAG & Verification

### `POST /api/chat`
The core intelligence endpoint. Performs cross-lingual retrieval, cross-encoder reranking, English answer synthesis using **Google Gemini 1.5 Flash**, strict citation tracking, article-level veracity labeling, and cross-source consensus evaluation.

#### Query Parameters
- `demo` (`boolean`, optional, default: `false`): When set to `true`, returns a pre-cached high-fidelity response. Useful for offline evaluation and live demonstrations.

#### Request Headers
```http
Content-Type: application/json
```

#### Request Body Schema (`ChatRequest`)

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `query` | `string` | **Yes** | — | User question in English, Hindi, Bengali, or Tamil. |
| `lang_filter` | `list[string]` | No | `null` | Optional list of language codes to constrain retrieval: `["en", "hi", "bn", "ta"]`. |

#### Request Example: RAG Question
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the latest government initiatives regarding solar power grid expansion?",
    "lang_filter": ["en", "hi", "bn"]
  }'
```

#### Response (`200 OK`)
```json
{
  "answer": "Recent multilateral coverage confirms significant acceleration in renewable grid infrastructure across South Asia [en_000101_c000]. Regional press reports in Hindi verify matching budgetary provisions for rural electrification networks [hi_000204_c000], while state reports in Bengali emphasize dedicated technology corridors for green manufacturing [bn_000305_c000]. Independent evaluators note that cross-state transmission integration remains on schedule for 2026.",
  "citations": [
    {
      "chunk_id": "en_000101_c000",
      "article_id": "en_000101",
      "title": "India Advances Clean Energy Infrastructure with New Grid Modernization Initiative",
      "lang": "en",
      "source": "l3cube-indicnews",
      "url": "https://news.example.com/clean-energy-grid",
      "snippet": "New renewable integration policies target expanded solar and wind capacities across western and southern regional grids, improving reliability and inter-state transmission efficiency.",
      "veracity": "Likely reliable",
      "reason": "Corroborated by official ministry releases and energy regulatory commission filings."
    },
    {
      "chunk_id": "hi_000204_c000",
      "article_id": "hi_000204",
      "title": "केंद्रीय बजट में ग्रामीण बुनियादी ढांचे और कृषि तकनीक के लिए नए आवंटन की घोषणा",
      "lang": "hi",
      "source": "l3cube-indicnews",
      "url": "https://news.example.com/budget-agriculture-hi",
      "snippet": "संसद में पेश बजट प्रस्तावों में सिंचाई विस्तार, कोल्ड स्टोरेज नेटवर्क और डिजिटल कृषि मिशन के लिए वित्तीय सहायता में उल्लेखनीय वृद्धि की गई है।",
      "veracity": "Likely reliable",
      "reason": "Parliamentary reporting verified against official budget documentation."
    },
    {
      "chunk_id": "bn_000305_c000",
      "article_id": "bn_000305",
      "title": "পশ্চিমবঙ্গে তথ্যপ্রযুক্তি ক্ষেত্রে নতুন বিনিয়োগ ও কর্মসংস্থান প্রকল্প চালু",
      "lang": "bn",
      "source": "l3cube-indicnews",
      "url": "https://news.example.com/bengal-it-investments",
      "snippet": "রাজ্য শিল্পোন্নয়ন পর্ষদের নতুন নীতি অনুযায়ী কলকাতা ও রাজারহাট এলাকায় নতুন সফটওয়্যার পার্ক স্থাপনের অনুমোদন দেওয়া হয়েছে।",
      "veracity": "Likely reliable",
      "reason": "Confirmed by state commerce department announcement."
    }
  ],
  "credibility": {
    "agreement_score": 0.92,
    "agreement_label": "High cross-lingual agreement (3 distinct languages)"
  }
}
```

#### Citation Fields:
- `chunk_id` (`string`): Unique identifier of the specific passage cited in the answer.
- `article_id` (`string`): Parent article identifier in MongoDB.
- `title` (`string`): Headline of the source article.
- `lang` (`string`): Source language (`"en"`, `"hi"`, `"bn"`, or `"ta"`).
- `veracity` (`string`): Truthfulness classification (`"Likely reliable"`, `"Uncertain"`, or `"Likely misleading"`).
- `reason` (`string`): One-sentence rationale for the veracity classification.

---

## 5. Topic & Event Clusters

### `GET /api/clusters`
Returns a list of all cross-lingual topic clusters discovered across the indexed corpus via BERTopic (UMAP + HDBSCAN).

#### Request Example
```bash
curl -X GET "http://localhost:8000/api/clusters"
```

#### Response (`200 OK`)
```json
{
  "clusters": [
    {
      "id": 1,
      "label": "Renewable Energy & Power Grid Modernization",
      "size": 340,
      "lang_counts": {
        "en": 120,
        "hi": 110,
        "bn": 60,
        "ta": 50
      },
      "top_terms": [
        "solar",
        "renewable",
        "grid",
        "transmission",
        "energy"
      ]
    },
    {
      "id": 2,
      "label": "Agricultural Technology & Rural Subsidies",
      "size": 285,
      "lang_counts": {
        "en": 65,
        "hi": 130,
        "bn": 55,
        "ta": 35
      },
      "top_terms": [
        "agriculture",
        "budget",
        "farmers",
        "irrigation",
        "crops"
      ]
    }
  ]
}
```

---

## 6. Cluster Details & Articles

### `GET /api/clusters/{cluster_id}`
Retrieves detailed metadata for a specific cluster along with a paginated list of member articles across languages.

#### Path Parameters
- `cluster_id` (`integer`, required): Unique cluster ID (e.g. `1`).

#### Query Parameters
- `page` (`integer`, optional, default: `1`, min: 1): Page number for pagination.
- `limit` (`integer`, optional, default: `20`, min: 1, max: 100): Number of articles per page.

#### Request Example
```bash
curl -X GET "http://localhost:8000/api/clusters/1?page=1&limit=2"
```

#### Response (`200 OK`)
```json
{
  "cluster": {
    "id": 1,
    "label": "Renewable Energy & Power Grid Modernization",
    "size": 340,
    "lang_counts": {
      "en": 120,
      "hi": 110,
      "bn": 60,
      "ta": 50
    },
    "top_terms": [
      "solar",
      "renewable",
      "grid",
      "transmission",
      "energy"
    ]
  },
  "total": 340,
  "articles": [
    {
      "article_id": "en_000101",
      "title": "India Advances Clean Energy Infrastructure with New Grid Modernization Initiative",
      "lang": "en",
      "source": "l3cube-indicnews",
      "category": "technology",
      "url": "https://news.example.com/clean-energy-grid"
    },
    {
      "article_id": "hi_000102",
      "title": "सौर ऊर्जा ग्रिड विस्तार: पश्चिमी राज्यों में अंतर्राज्यीय पारेषण परियोजना का शुभारंभ",
      "lang": "hi",
      "source": "l3cube-indicnews",
      "category": "energy",
      "url": "https://news.example.com/solar-grid-hi"
    }
  ]
}
```

---

## 7. Error Handling & Status Codes

The API uses standard HTTP response codes to indicate status:

| Status Code | Description | Scenario |
|---|---|---|
| `200 OK` | Request succeeded | Standard response for search, chat, and cluster queries. |
| `422 Unprocessable Entity` | Validation error | Invalid query parameters (e.g. `top_k < 1`), missing required fields, or ill-formed JSON body. |
| `404 Not Found` | Resource not found | Cluster ID does not exist in MongoDB or mock fallback. |
| `500 Internal Server Error`| Unexpected server failure | Unhandled exceptions; check backend logs for detailed stack traces. |

#### Example `422 Unprocessable Entity` Response
```json
{
  "detail": [
    {
      "type": "greater_than_equal",
      "loc": ["body", "top_k"],
      "msg": "Input should be greater than or equal to 1",
      "input": 0,
      "ctx": { "ge": 1 }
    }
  ]
}
```
