<div align="center">

# 🛡️ Secure Enterprise RAG Agent

**A production-ready, highly secure Retrieval-Augmented Generation (RAG) agent featuring real-time Data Loss Prevention (DLP), an asynchronous LLM safety judge, and a live observability dashboard.**

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Gemini](https://img.shields.io/badge/Google%20Gemini-Flash%202.5-orange?style=for-the-badge&logo=google&logoColor=white)](https://deepmind.google/technologies/gemini/)
[![Chainlit](https://img.shields.io/badge/Chainlit-1.1.0%2B-F87171?style=for-the-badge)](https://github.com/Chainlit/chainlit)
[![Presidio](https://img.shields.io/badge/Microsoft-Presidio-0078D4?style=for-the-badge&logo=microsoft&logoColor=white)](https://microsoft.github.io/presidio/)

</div>

---

## 📖 Overview

While Large Language Models (LLMs) offer powerful natural language capabilities, deploying them in enterprise environments requires strict security and data privacy controls. 

This application wraps **Gemini 2.5 Flash** in a robust security pipeline, ensuring that malicious prompts are intercepted, internal database queries are authorized, and Personally Identifiable Information (PII) is dynamically redacted before reaching the client side.

---

## ✨ Key Features

* **🛑 Defense-in-Depth Guardrails:** Multi-layered security including rate-limiting, deterministic banned word filters, and a secondary "LLM Judge" (Gemini 2.5 Flash-Lite) to asynchronously evaluate and block prompt injections.
* **🕵️‍♂️ Real-Time DLP & PII Redaction:** Integrates Microsoft Presidio and spaCy NLP middleware to intercept backend database responses and automatically mask sensitive customer data (e.g., `<PERSON>`, `<LOCATION>`).
* **🗄️ Secure Tool-Calling (RAG):** Connects safely to a local SQLite database, allowing the agent to autonomously fetch real-time order statuses.
* **📊 Live Observability Dashboard:** A dynamic React-based sidebar that continuously displays real-time telemetry, including prompt volume, block rates, and PII redaction counts.
* **⚡ "Short-Circuit" Error Handling:** Utilizes a custom Python interception pattern to instantly halt LLM execution upon threat detection, displaying a clean UI alert.

---

## 🛠️ Tech Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Core Framework** | Google GenAI ADK | Agent logic and routing |
| **LLMs** | Gemini 2.5 Flash / Lite | Main agent and async safety judge |
| **Frontend UI** | Chainlit | React-based conversational interface |
| **DLP Middleware** | MS Presidio & spaCy | Real-time NLP entity recognition |
| **Database** | SQLite3 | Local mock e-commerce backend |

---

## 🏗️ System Architecture

1. **Input Interception:** User prompts are routed through deterministic guardrails.
2. **Intent Evaluation:** The Safety Judge evaluates intent. If malicious, the process short-circuits.
3. **Tool Execution:** Safe prompts reach the Main Agent, which generates a secure tool-call to the SQLite backend if data is needed.
4. **Data Redaction:** Returned database data passes through the Presidio DLP pipeline. PII is stripped and tagged.
5. **UI Rendering:** The sanitized response streams to the user, updating the Live Safety Dashboard simultaneously.

---

## 🚀 Getting Started

### 1. Prerequisites
* Python 3.10+
* Google Gemini API Key

### 2. Installation
Clone the repository and install the dependencies:
```bash
git clone [https://github.com/yourusername/secure-enterprise-agent.git](https://github.com/yourusername/secure-enterprise-agent.git)
cd secure-enterprise-agent
pip install -r requirements.txt
```

Download the required spaCy language model for the DLP pipeline:
```bash
python -m spacy download en_core_web_lg
```

### 3. Environment Setup
Create a `.env` file in the root directory and add your API credentials:
``` code snippet
GEMINI_API_KEY=your_google_api_key_here
```

### 4. Running the Application
Ensure `data/ecommerce.db` SQLite database is populated, then launch the Chainlit server:
```bash
chainlit run app.py -w
```
Navigate to `http://localhost:8000` in your browser to interact with the agent.

---

## 🔒 Security Auditing
All blocked prompts, jailbreak attempts, and system errors are logged directly to the terminal for developer auditing, while cleanly obfuscating the stack trace from the end user in the UI.

<div align="center">
<i>Built with security in mind.</i>
</div>
