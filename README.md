# Autonomous B2B AI Sales Agent (Outbound Engine) 🤖

An enterprise-grade, autonomous multi-agent system designed to handle the entire B2B outbound sales pipeline: from intelligent lead generation and qualification to drafting hyper-personalized emails, with zero data duplication.

*Disclaimer: This repository contains a sanitized, white-labeled version of a production system. All proprietary business logic, specific search taxonomies, and company data have been removed or mocked for open-source sharing.*

## 🌟 Key Architectural Features

1. **Three-Layer Idempotency (Zero Duplication):**
   - **SQLite State Ledger:** Atomic process locking and reservation to prevent processing the same lead twice.
   - **IMAP Reconciliation:** Verifies the `Drafts` folder in the mail server before LLM invocation to recover safely from mid-process crashes.
   - **CRM Status Machine:** Google Sheets API integration with fail-closed logic to update lead states.

2. **Predatory Dorking & AI Qualification:**
   - Uses the `Tavily API` to execute dynamic, time-boxed search queries.
   - Leverages `Groq (LLaMA/Mixtral)` to qualify leads based on strict continuity indicators (Confidence > 85%).

3. **Anti-Hallucination Guardrails:**
   - Constrains LLM output using strict JSON Schema validation.
   - Injects a one-line hyper-personalized AI hook into a statically approved HTML email template to prevent pricing/offer hallucinations.

4. **Headless Cron Reliability:**
   - Implements `sys.stdout.isatty()` checks to prevent zombie processes during missing CRM authentications.
   - Uses `Tenacity` for exponential backoff against API rate limits (HTTP 429/5xx).

## 🛠️ Tech Stack
- **Python 3.10+**
- **LLM & Tooling:** LangChain, Groq API, Tavily Search API
- **Data & State:** SQLite, Google Sheets API v4
- **Infrastructure:** IMAP/SMTP, MacOS `osascript` (Observability), `FileLock`

## ⚙️ Setup & Execution
1. Clone the repository:
   ```bash
   git clone [https://github.com/string-MFathi/autonomous-b2b-sales-agent.git](https://github.com/string-MFathi/autonomous-b2b-sales-agent.git)
   cd autonomous-b2b-sales-agent
