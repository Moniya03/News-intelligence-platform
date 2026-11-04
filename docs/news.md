# PRD: Multilingual News Intelligence Platform

*NLP course final project. Solo, short timeline. Status: draft from planning brainstorm.*

## 1. Summary

A multilingual news assistant. A user asks a question in English, Hindi, Bengali or Tamil. The system retrieves relevant news articles across all four languages and answers **in English**, with citations to the source articles and a credibility flag. A topic/event cluster view and cross-lingual search support the assistant.

The project is a **core NLP and GenAI** project. It has no heavy scraping and little backend engineering. Every component uses existing pretrained models (no fine-tuning), and the main contribution is a careful evaluation of them.

## 2. Problem

News about the same event is reported in many languages, and a reader in one language usually sees only that language's coverage. Searching across languages is hard, and so is judging whether a story is reliable. This project tests how well modern multilingual embeddings and LLMs can:

1. find relevant news across languages,
2. answer questions grounded in that news with verifiable citations,
3. group articles by topic across languages,
4. flag likely misinformation.

## 3. Goals and non-goals

**Goals**
- G1. Cross-lingual retrieval over EN, HI, BN, TA news that measurably beats a lexical baseline.
- G2. A RAG assistant that answers in English with correct, checkable citations.
- G3. A cross-lingual topic/event view.
- G4. A credibility flag, evaluated on public Hindi and English misinformation data.
- G5. A reproducible evaluation with metrics and baselines for each feature (needed for the report and viva).

**Non-goals**
- No fine-tuning of any model.
- No live scraping pipeline or production-grade backend.
- No user accounts, personalization or alerts.
- No bias detection, NER, sentiment, keyphrase or summarization features (cut for time; see section 8).
- No synthetic news data (real public datasets are used).

## 4. Users

- **Primary: course evaluators** (viva and report). They need a working demo, clear metrics, and defensible design choices.
- **Illustrative end user:** a multilingual news reader who wants to ask one question and see coverage from several languages, in English.

## 5. Functional requirements

| ID | Requirement | Priority |
|---|---|---|
| FR1 | Ingest and normalize articles from the chosen datasets into MongoDB, with fields: id, title, body, language, category (if labeled), source, date (if available). | Must |
| FR2 | Chunk articles, embed chunks with a multilingual embedding model, and index the vectors in Weaviate with metadata. | Must |
| FR3 | Cross-lingual search: a query in any supported language returns ranked articles in all languages (dense and hybrid modes). | Must |
| FR4 | RAG chat: retrieve top-k chunks, generate an English answer, and attach citations (title, language, source, link to article). | Must |
| FR5 | Topic/event cluster view: cluster all articles, label clusters, and show language mix per cluster. | Must |
| FR6 | Credibility flag on each answer: per-cited-article veracity label with a short reason, plus a cross-source agreement indicator. | Must |
| FR7 | Evaluation harness that reproduces all reported metrics from saved test sets. | Must |
| FR8 | Rerank the top 30 hybrid-search results with a cross-encoder reranker (bge-reranker-v2-m3) and keep the top 5 to 8 for generation. | Must |
| FR9 | Near-duplicate removal at ingest, and de-duplication of citations in answers. | Must |
| FR10 | Show original-language snippet next to an English gist for each citation. | Stretch |
| FR11 | Cross-lingual story (event) clustering, only if dated multilingual data (for example Babel Briefings) proves usable. | Stretch |

## 6. Non-functional requirements

- Runs locally on a laptop with a 4 GB GPU for query-time work. Heavy batch work (embedding the corpus) runs once on a free Kaggle or Colab GPU.
- Answers in under about 10 seconds for a typical question.
- All experiments are reproducible from a config file and fixed random seeds.
- Respect dataset licenses. Document each source in the report.

## 7. Data

| Purpose | Source | Notes |
|---|---|---|
| News corpus (EN, HI, BN, TA) | L3Cube-IndicNews (GitHub: `l3cube-pune/indic-nlp`) | 26,000+ rows per language, 10-12 topic categories, headlines and full articles. Subsample about 5,000 articles per language to keep the index small. Confirm license. |
| Optional extra corpus | Kaggle Multi Indic Languages News Dataset, Babel Briefings | Not separated by language/category, so use only as a backup. Babel Briefings' language coverage is unverified. |
| Misinformation, Hindi | HinFakeNews (about 68k real/fake Hindi articles) | Hosted on the AIKosh portal. Confirm access and license. |
| Misinformation, English | A public English fake-news dataset from Kaggle | Check for source leakage (see risks). |
| Retrieval benchmark | FLORES-200 devtest (EN to HI/BN/TA parallel sentences) | Clean cross-lingual retrieval accuracy. |
| RAG test set | About 40-50 hand-written questions over the index, with relevant articles marked | Written by the project owner. |

The previously scraped Hindi/English articles are **not** used (unstructured, and too imbalanced).

## 8. Scope decisions

- **MVP (must ship):** FR1 to FR9.
- **Stretch:** FR10, FR11.
- **Cut:** personalization/alerts, auth, bias detection, NER, sentiment, keyphrases, translation model, summarization view, fine-tuning, synthetic data, live scraping.

## 9. Success metrics (evaluation plan)

Every feature has one metric set and one baseline, so the report can show a results table per feature.

| Feature | Metrics | Methods compared |
|---|---|---|
| Cross-lingual retrieval (benchmark) | Recall@1 and Recall@10 on FLORES-200, per language pair | BGE-M3 vs multilingual-e5-base vs BM25 (lexical baseline) |
| Retrieval on the news index | Recall@5, MRR, nDCG@10 on the 40-50 hand-written queries | BM25 vs dense vs hybrid vs hybrid + reranker (ablation table) |
| RAG answers | Faithfulness and answer correctness (LLM judge, with about 15 manual spot checks), citation accuracy | RAG vs the same LLM with no retrieval |
| Clustering | NMI and ARI against L3Cube category labels, per language; share of clusters containing more than one language | BERTopic on multilingual embeddings vs TF-IDF + KMeans |
| Misinformation flag | Macro-F1, per-class precision/recall on HinFakeNews and the English set | LLM zero-shot vs LLM with retrieved evidence vs TF-IDF + logistic regression (classical baseline) |

A short error analysis (5 to 10 failure cases per feature) goes into the report.

## 10. Milestones

Dates should be fitted to the real deadline; the order matters more than the exact days.

1. **Week 1: data and index.** Load datasets into MongoDB, run the batch embedding job on Kaggle, bring up Weaviate, get cross-lingual search working.
2. **Week 2: intelligence layer and evaluation.** RAG with citations, reranking, duplicate handling, clustering, credibility flag. Run all evaluations and save result tables. **Feature freeze at the end of this week.**
3. **Week 3: UI, report, viva.** Build the demo UI, write the report from saved results, rehearse the demo and viva answers.

If less time remains, cut FR5 polish first, then the credibility agreement indicator, and keep retrieval, RAG and their evaluation.

## 11. Risks and mitigations

| Risk | Mitigation |
|---|---|
| L3Cube articles are not parallel across languages, so there is no ground truth for same-event matching. | Evaluate cross-lingual retrieval on FLORES-200 and on the hand-written query set instead of event matching. |
| Fake-news datasets can leak source style, which inflates scores. | Report per-dataset results and test cross-dataset where possible. Be explicit about this in the limitations. |
| HinFakeNews or L3Cube access or license problems. | Check both on day 1. Fallback: Kaggle Multi Indic Languages News Dataset plus the Hindi/Bengali Kaggle news set for the corpus. |
| LLM-judge evaluation can be biased. | Manually check a sample and report agreement. |
| Gemini API limits or outages during the demo. | Cache demo answers and keep a small set of pre-run example queries. |
| 4 GB GPU memory. | Do the heavy embedding on Kaggle. Load only BGE-M3 (fp16) locally at query time. |

## 12. Decision log (from the planning brainstorm)

| Decision | Choice |
|---|---|
| Headline story | Multilingual news RAG assistant |
| Languages | English, Hindi, Bengali, Tamil (pending the day-1 data check) |
| Answer language | Always English |
| Data | Real public datasets, not synthetic |
| Existing scraped articles | Set aside |
| Database | MongoDB (documents) + Weaviate (vectors) |
| Fine-tuning | None; evaluate existing models only |
| LLM | Gemini API for generation and judging |
| Compute | Kaggle/Colab GPU for batch work, local RTX 3050 Ti (4 GB) for query time |
| Demo UI | Chat with citations, cross-lingual search, cluster view, credibility flag |
| Reranking | Cross-encoder reranker (bge-reranker-v2-m3) on the top 30 hybrid results; reported as an ablation |
| Duplicate detection | Light only: near-duplicate removal at ingest and citation de-duplication in answers |
| Cross-lingual story clustering | Stretch, only if dated multilingual data proves usable |

## 13. Open items to confirm

- L3Cube-IndicNews and HinFakeNews licenses and access.
- Whether Babel Briefings has Hindi, Bengali or Tamil (optional source).
- The real submission deadline, to fix the milestone dates.
- UI framework (the architecture doc recommends Streamlit).
