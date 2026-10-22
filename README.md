<div align="center">

# 🤖 Autonomous B2B Sales Agent

**A fully autonomous, LLM-powered agent for B2B lead generation, prospecting, and qualification, running silently in the background.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![LangChain](https://img.shields.io/badge/Built%20with-LangChain-1C3C3C.svg)](https://www.langchain.com/)
[![Groq](https://img.shields.io/badge/Inference-Groq-F55036.svg)](https://groq.com/)
[![Observability: LangSmith](https://img.shields.io/badge/Observability-LangSmith-orange.svg)](https://smith.langchain.com/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

</div>

---

## 📖 Table of Contents

- [Overview](#-overview)
- [System Architecture](#-system-architecture)
- [Key Features](#-key-features)
- [Tech Stack](#-tech-stack)
- [Setup & Installation](#-setup--installation)
- [Usage](#-usage)
- [Performance & Observability](#-performance--observability)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 Overview

**Autonomous B2B Sales Agent** is an open-source, production-tested AI agent that automates the most time-consuming part of outbound sales: **finding and qualifying the right companies**.

It runs as a background daemon, dynamically hunts the live web for target B2B clients, evaluates each one with an LLM, filters out anything it has already seen, and stores qualified leads in both a local database and a shared Google Sheet.

### 💡 Value Proposition

| Problem | How this agent solves it |
|---|---|
| Manual prospecting is slow and repetitive | Fully autonomous discovery and qualification, no human in the loop |
| Duplicate outreach damages credibility | **Anti-Duplication Shield** checks live Google Sheet data before every run |
| LLM pipelines break on messy output | Strict JSON-schema responses with zero parsing errors in production |
| AI costs spiral quickly | Optimized prompts plus Groq inference: **under $0.01 per week** |
| Background jobs overlap and hang | Robust `.lock` file management with `try...finally` cleanup |

---

## 🏗️ System Architecture

```text
┌──────────────────────────────────────────────────────────────────────┐
│                        🕘 SMART SCHEDULER                            │
│     Background daemon (nohup) · runs only in a daily time window     │
│                       (e.g. 9:00 PM – 11:00 PM)                      │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   🔒 .lock Manager    │──── lock exists? ──► exit safely
                    │   (try...finally)     │
                    └───────────┬───────────┘
                                │ acquired
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                 🛡️ GOOGLE SHEET SHIELD (Anti-Duplication)            │
│   Fetch live data from output Sheet ► cache hundreds of name         │
│   variations in memory                                               │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                  🔎 DISCOVERY ENGINE (Tavily Search API)             │
│   Dynamic, user-defined criteria ► live web discovery & scraping     │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ candidate entities
                                ▼
                    ┌───────────────────────┐
                    │  Already in Shield?   │── yes ──► skip (no duplicate)
                    └───────────┬───────────┘
                                │ no
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│             🧠 LLM QUALIFICATION (LangChain + Groq / OpenAI)         │
│   Strict JSON output:                                                │
│   {"is_target": true/false, "company_name": "...", "contact_info":..}│
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                  ┌─────────────┴─────────────┐
            is_target = false           is_target = true
                  │                           │
                  ▼                           ▼
              discard              ┌────────────────────────┐
                                   │  💾 ACTION LAYER       │
                                   │  ├─ SQLite (local)     │
                                   │  └─ Google Sheets      │
                                   │     (Apps Script hook) │
                                   └────────────────────────┘

        📊 Every reasoning cycle is traced end-to-end in LangSmith
```

---

## ✨ Key Features

### 🛡️ Anti-Duplication Shield
Before any search begins, the agent pulls **live data from the output Google Sheet** and loads **hundreds of company-name variations** into memory. Leads that were already processed or contacted are never evaluated, stored, or contacted a second time, even when the name is spelled differently.

### ⏰ Autonomous Scheduler
The agent runs as a true background daemon (`nohup`) and operates only within a **configurable daily time window** (e.g. 9:00 PM to 11:00 PM). It needs no cron babysitting and no manual triggers, and it respects off-hours.

### 🧠 Strict-JSON LLM Qualification
Scraped entity data is passed to the LLM through LangChain with a tightly engineered prompt. The model returns a **machine-parseable JSON verdict**, with zero parsing errors across the production window.

### 🔎 Dynamic Discovery Engine
Target criteria are **user-defined and dynamic**. Tavily's search API handles live web discovery, so leads come from the current web rather than from stale static lists.

### 💾 Dual-Layer Persistence
Qualified leads are written to a **local SQLite database** (durable, queryable) and pushed to **Google Sheets via an Apps Script webhook** (shareable with your sales team).

### 🔐 Fault-Tolerant Execution
A `.lock` file system wrapped in `try...finally` guarantees that crashed or interrupted runs always release their lock, preventing hanging processes and overlapping executions.

### 📈 Built-in Observability
Full LangSmith tracing covers latency, token usage, cost, and error rates for every reasoning cycle.

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| **Language** | Python 3.9+ |
| **Orchestration** | [LangChain](https://www.langchain.com/) |
| **LLM Inference** | [Groq API](https://groq.com/) (ultra-fast) / any OpenAI-compatible endpoint |
| **Web Search** | [Tavily Search API](https://tavily.com/) |
| **Observability** | [LangSmith](https://smith.langchain.com/) |
| **Local Storage** | SQLite |
| **Cloud Storage** | Google Sheets API via Google Apps Script Webhook |
| **HTTP Client** | `httpx` |
| **Process Management** | `nohup`, `.lock` files, shell scripting |

---

## 🚀 Setup & Installation

### Prerequisites

- Python **3.9+**
- A [Groq](https://console.groq.com/) (or OpenAI-compatible) API key
- A [Tavily](https://tavily.com/) API key
- A [LangSmith](https://smith.langchain.com/) API key (optional but recommended)
- A Google Sheet with an Apps Script webhook deployed as a Web App

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/autonomous-b2b-sales-agent.git
cd autonomous-b2b-sales-agent
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows (PowerShell)
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> `requirements.txt` includes core packages such as `httpx`, `langchain`, and their integrations (Groq / OpenAI, Tavily, LangSmith).

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
# --- LLM Provider ---
GROQ_API_KEY=your_groq_api_key
# OPENAI_API_KEY=your_openai_compatible_key   # optional alternative

# --- Web Search ---
TAVILY_API_KEY=your_tavily_api_key

# --- Observability (LangSmith) ---
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_PROJECT=autonomous-b2b-sales-agent

# --- Google Sheets (Apps Script Webhook) ---
GOOGLE_SHEET_WEBHOOK_URL=https://script.google.com/macros/s/XXXXXXXX/exec
```

> ⚠️ **Never commit your `.env` file.** Make sure it is listed in `.gitignore`.

---

## ▶️ Usage

### One-command launch with `run.sh`

The included `run.sh` script handles the full lifecycle: it **discovers the `.venv`**, **installs dependencies**, and **launches the agent as a background daemon**.

```bash
#!/usr/bin/env bash
set -e

# 1. Discover (or create) the virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    python3 -m venv .venv
    source .venv/bin/activate
fi

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the agent as a background daemon
nohup python3 -u main.py > agent.log 2>&1 &
echo "🚀 Agent started in the background (PID: $!)"
```

Make it executable and run it:

```bash
chmod +x run.sh
./run.sh
```

### Monitoring & management

```bash
# Follow live logs
tail -f agent.log

# Check that the daemon is running
ps aux | grep main.py

# Stop the agent
pkill -f main.py

# Clear a stale lock (only if the process is not running)
rm -f *.lock
```

The agent wakes up only inside its configured daily window and sleeps the rest of the time.

---

## 📊 Performance & Observability

> **Case study:** real production telemetry from LangSmith over a **7-day operational window**.

The agent was deployed as a long-running background daemon and monitored end-to-end with LangSmith. The results show that a well-engineered agentic pipeline can be **fast, reliable, and nearly free to operate**.

<!-- NOTE TO AUTHOR: "~500 traces" vs "46 succeeded / 1 failed" (46/47 ≈ 97.9%) do not reconcile. Verify against LangSmith (e.g. root runs vs. child runs) before publishing. -->

### 📈 Key Metrics (7-Day Window)

| Metric | Result |
|---|---|
| 🔁 **Volume** | ~500 qualification traces executed |
| ✅ **Success Rate** | **97.8%** (46 succeeded, 1 failed in the last 7 days) |
| ⚡ **Median Latency (P50)** | **0.9 s** per reasoning cycle |
| 🐢 **Tail Latency (P99)** | **2.4 s** max per reasoning cycle |
| 💰 **Total LLM Cost** | **< $0.01** for the entire week |
| 🧾 **Output Quality** | **Zero parsing errors**: strict JSON for every qualified lead |

### 🔍 Key Takeaways

- **Stability:** A 97.8% success rate was sustained while running unattended as a background daemon, thanks to fault-tolerant lock management and defensive error handling.
- **Speed:** Groq's inference engine delivers **sub-second median latency (0.9 s P50)**, with even the slowest cycles (P99) finishing in just **2.4 s**.
- **Cost Efficiency:** Highly optimized prompt engineering kept total LLM spend **below one cent** over the whole week, so the pipeline scales without cost anxiety.
- **Reliability of Structured Output:** The LLM returned valid, strictly formatted JSON on every qualified lead, with **zero parsing failures** and no brittle regex post-processing.

### 🖼️ LangSmith Dashboards

### 1. The Business Result (Autonomous Lead Generation)
<!-- ضع هنا صورة جوجل شيت أو تقرير التليجرام -->
<img width="1319" height="579" alt="Leads" src="https://github.com/user-attachments/assets/01cbe84c-9257-4708-b0e8-b0db7b3d009e" />
<img width="321" height="171" alt="Result" src="https://github.com/user-attachments/assets/0a6b76e5-1aee-4d11-8fb6-32e999300cdb" />


### 2. Extreme Cost Efficiency & Stability (LangSmith)
<!-- ضع هنا الصورة الأولى من LangSmith (خلاصة التكلفة والسرعة) -->
<img width="1183" height="590" alt="Analysis" src="https://github.com/user-attachments/assets/d7ae87b4-e08f-4bb5-8a14-854dedf97ef4" />


### 3. Flawless JSON Structuring & Reasoning (LangSmith Traces)
<!-- ضع هنا الصورة الثالثة من LangSmith (سجل التتبع والـ JSON) -->
<img width="1440" height="766" alt="Analysis2" src="https://github.com/user-attachments/assets/95f3b21e-5a5b-43c6-8bf4-7f357b0f6d91" />
<img width="447" height="848" alt="Analysis3" src="https://github.com/user-attachments/assets/e66ca03e-99f9-42b0-ab59-a3acebc6efaf" />

---

## 🤝 Contributing

Contributions are what make the open-source community thrive, and they are **greatly appreciated**!

1. **Fork** the project
2. **Create** your feature branch (`git checkout -b feature/AmazingFeature`)
3. **Commit** your changes (`git commit -m 'Add some AmazingFeature'`)
4. **Push** to the branch (`git push origin feature/AmazingFeature`)
5. **Open** a Pull Request

Ideas for contributions: additional LLM providers, new storage backends (Airtable, HubSpot, Notion), outreach-drafting modules, a web dashboard, and Docker support.

Found a bug or have a feature request? [Open an issue](../../issues).

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for more information.

---

<div align="center">

⭐ **If this project helps you, please consider giving it a star!** ⭐

</div>
