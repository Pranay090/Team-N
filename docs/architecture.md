# Architecture — Aiden AI

## Pipeline Overview

```
User Query
    │
    ▼
[Node 1: Intent Classifier]  ← Claude LLM
    │
    ├── job     → [Node 2A: Job Scraper]      (Tavily + job board targeted crawl)
    ├── product → [Node 2B: Product Scraper]  (Tavily + review site crawl)
    └── general → [Node 2C: General Scraper]  (Tavily search API)
                        │
                        ▼
              [Node 3: Validator]
              HTTP HEAD checks, scam heuristics, 404 filter
                        │
                        ▼
              [Node 4: Ranker]
              Score by: domain trust, recency, query relevance
                        │
                        ▼
              [Node 5: Extractor & Summarizer]
              Claude LLM → structured markdown cards
                        │
                        ▼
              [Node 6: Next Actions]
              CTA deeplinks, apply prompts, follow-up suggestions
                        │
                        ▼
              Streamlit Chat UI
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Graph orchestration | LangGraph |
| LLM | GPT-4o via langchain-openai |
| Search | Tavily API |
| HTTP scraping | httpx + BeautifulSoup4 |
| UI | Streamlit |
| Config | python-dotenv |

## Intent Categories

- **job** — queries about employment, roles, hiring, remote work
- **product** — queries about buying, best-of lists, reviews, pricing
- **general** — everything else (news, how-to, factual Q&A)

## Ranking Weights

| Signal | Weight |
|--------|--------|
| Domain trust (Alexa/manual allowlist) | 40% |
| Semantic relevance to query | 40% |
| Recency (publication date) | 20% |
