<!-- Profile README · github.com/PD-BDS -->

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/PD-BDS/PD-BDS/main/assets/readme/hero-dark.svg">
    <img src="./assets/readme/hero-light.svg" width="100%" alt="Piyal Dey, AI Engineer in Aalborg, Denmark. Designing and shipping AI applications end to end: agents, retrieval, APIs, front ends and the infrastructure they run on. MSc Business Data Science (Aalborg University), MSc Data Analytics and Design Thinking for Business (East Delta University), Microsoft Certified Azure Data Scientist Associate. Python, TypeScript, Claude Code, Azure, Hetzner, Docker, Kubernetes.">
  </picture>
</p>

<p align="center">
  <a href="https://www.linkedin.com/in/piyal-dey-711015128/"><img src="https://img.shields.io/badge/LinkedIn-Piyal%20Dey-0A66C2?style=flat-square" alt="LinkedIn"></a>
  <a href="mailto:dey.piyal97@gmail.com"><img src="https://img.shields.io/badge/Email-dey.piyal97%40gmail.com-EA4335?style=flat-square&logo=gmail&logoColor=white" alt="Email"></a>
  <img src="https://img.shields.io/badge/Open%20to-AI%20%2F%20ML%20engineering%20roles-238636?style=flat-square" alt="Open to AI / ML engineering roles">
</p>

## About

I'm an AI Engineer at [Plant Supervision](https://plant-supervision.com/) in Aalborg, Denmark, where I design and ship AI applications end to end: LLM and agent workflows, retrieval pipelines, the FastAPI services behind them, React and Next.js front ends, and the infrastructure they run on. I build with Claude Code as a core part of my workflow — custom subagents, skills, hooks and MCP integrations that keep delivery test-first and reviewable.

**Focus areas**

- Agentic systems and retrieval: CrewAI, LangGraph, LangChain, ChromaDB, OpenAI and Claude models
- AI-assisted engineering with Claude Code: agent harnesses, custom subagents and skills, hooks, MCP servers
- Applied machine learning: forecasting, classification and explainability with PyTorch, TensorFlow and scikit-learn
- Delivery: FastAPI, React and TypeScript, Docker, Kubernetes, GitHub Actions, Azure and Hetzner

**Education**

- MSc Business Data Science — Aalborg University, Denmark. Thesis: gender bias in LLM-based resume screening and how embedding strategy, prompt design and calibration affect it.
- MSc Data Analytics & Design Thinking for Business — East Delta University

**Certification**

<a href="https://learn.microsoft.com/en-us/credentials/certifications/azure-data-scientist/"><img align="left" src="https://learn.microsoft.com/media/learn/certification/badges/microsoft-certified-associate-badge.svg" width="72" alt="Microsoft Certified Associate badge"></a>

**Microsoft Certified: Azure Data Scientist Associate (DP-100)**<br>
Designing and running machine-learning solutions on Azure: data preparation, training, model management and deployment with Azure Machine Learning.

<br clear="left">

## Work at Plant Supervision

Products I have built as an AI Engineer since 2025. The code is private; I'm glad to walk through the architecture in conversation.

**HireX** · AI-assisted candidate screening<br>
*Problem:* recruiters read every CV against every job description by hand, and shortlists vary from reviewer to reviewer.<br>
*What it does:* a multi-agent pipeline parses each resume, scores it against the job requirements with written reasoning, ranks the candidates, and gives recruiters a retrieval-backed chat to ask follow-up questions about anyone on the list.<br>
*Built on:* FastAPI backend with PostgreSQL, JWT auth and rate limiting; LangGraph and CrewAI orchestration with LangSmith tracing; ChromaDB for retrieval; React front end; deployed on Azure App Service with Azure Files for persistent state. An earlier open-source version is at [PD-BDS/HireX](https://github.com/PD-BDS/HireX).<br>
`FastAPI` `PostgreSQL` `LangGraph` `CrewAI` `ChromaDB` `React` `Azure`

**Assessk** · SaaS for ISO 12100 machinery risk assessment<br>
*Problem:* risk assessments for industrial machinery are long, expert-heavy documents that safety engineers assemble by hand from standards, checklists and templates.<br>
*What it does:* a SaaS application that takes a safety engineer through the whole assessment — project setup, hazard identification, risk estimation, reduction measures and the final PDF report — with LangGraph agents that draft and check content using retrieval over the ISO and EU source texts. A desktop shell supports on-site use.<br>
*Built on:* FastAPI with async SQLAlchemy, LangGraph workflows and RAG; Next.js, React and Tailwind front end; Electron desktop shell; self-hosted on Hetzner with Docker Compose, Caddy, Prometheus and Grafana monitoring, and automated backups.<br>
`FastAPI` `LangGraph` `RAG` `Next.js` `TypeScript` `Docker` `Hetzner`

**Contractbook** · internal contract-lifecycle tool<br>
*Problem:* contracts drafted in Word and signed over email leave no reliable record of who changed or approved what.<br>
*What it does:* drafting in a rich-text editor with templates, electronic signature, PDF generation, and a hash-chained audit trail so every revision and signature is verifiable.<br>
*Built on:* FastAPI with SQLAlchemy and JWT authentication; React and TypeScript front end (Vite, TanStack Query, TipTap editor) with Tailwind.<br>
`FastAPI` `React` `TypeScript` `Vite` `Tailwind`

## Tools I use

<p align="center">
  <img src="https://skillicons.dev/icons?i=python,ts,react,nextjs,vite,tailwind,fastapi,pytorch,tensorflow,sklearn,azure,docker,kubernetes,githubactions,postgres,sqlite,r,git,linux,bash&perline=10" alt="Python, TypeScript, React, Next.js, Vite, Tailwind, FastAPI, PyTorch, TensorFlow, scikit-learn, Azure, Docker, Kubernetes, GitHub Actions, PostgreSQL, SQLite, R, Git, Linux, Bash">
</p>

| | |
|:--|:--|
| **LLMs & agents** | ![Claude Code](https://img.shields.io/badge/Claude%20Code-D97757?style=flat-square&logo=claude&logoColor=white) ![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=flat-square) ![CrewAI](https://img.shields.io/badge/CrewAI-FF5A50?style=flat-square) ![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C?style=flat-square&logo=langgraph&logoColor=white) ![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=flat-square&logo=langchain&logoColor=white) ![MCP](https://img.shields.io/badge/MCP-5B5BD6?style=flat-square) ![Transformers](https://img.shields.io/badge/Transformers-FFB000?style=flat-square) ![RAG](https://img.shields.io/badge/RAG-6E40C9?style=flat-square) ![ChromaDB](https://img.shields.io/badge/ChromaDB-FF6F61?style=flat-square) ![Pydantic](https://img.shields.io/badge/Pydantic-E92063?style=flat-square&logo=pydantic&logoColor=white) |
| **ML & deep learning** | ![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?style=flat-square&logo=pytorch&logoColor=white) ![TensorFlow](https://img.shields.io/badge/TensorFlow%20%2F%20Keras-FF6F00?style=flat-square&logo=tensorflow&logoColor=white) ![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=flat-square&logo=scikitlearn&logoColor=white) ![XGBoost](https://img.shields.io/badge/XGBoost-189FDD?style=flat-square) ![SHAP](https://img.shields.io/badge/SHAP%20%2F%20XAI-1E88E5?style=flat-square) ![BERT](https://img.shields.io/badge/BERT%20%2F%20FinBERT-4285F4?style=flat-square) ![LSTM](https://img.shields.io/badge/LSTM%20%2F%20Time%20Series-0F9D58?style=flat-square) |
| **Backend & frontend** | ![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white) ![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white) ![React](https://img.shields.io/badge/React-20232A?style=flat-square&logo=react&logoColor=61DAFB) ![Next.js](https://img.shields.io/badge/Next.js-000000?style=flat-square&logo=nextdotjs&logoColor=white) ![Vite](https://img.shields.io/badge/Vite-646CFF?style=flat-square&logo=vite&logoColor=white) ![Tailwind](https://img.shields.io/badge/Tailwind%20CSS-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white) ![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat-square&logo=streamlit&logoColor=white) |
| **Cloud & delivery** | ![Azure](https://img.shields.io/badge/Microsoft%20Azure-0078D4?style=flat-square) ![Hetzner](https://img.shields.io/badge/Hetzner-D50C2D?style=flat-square&logo=hetzner&logoColor=white) ![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white) ![Kubernetes](https://img.shields.io/badge/Kubernetes-326CE5?style=flat-square&logo=kubernetes&logoColor=white) ![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-2088FF?style=flat-square&logo=githubactions&logoColor=white) ![Render](https://img.shields.io/badge/Render-46E3B7?style=flat-square&logo=render&logoColor=black) ![Vercel](https://img.shields.io/badge/Vercel-000000?style=flat-square&logo=vercel&logoColor=white) |
| **Data** | ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white) ![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white) ![Pandas](https://img.shields.io/badge/Pandas-150458?style=flat-square&logo=pandas&logoColor=white) ![NumPy](https://img.shields.io/badge/NumPy-013243?style=flat-square&logo=numpy&logoColor=white) ![Plotly](https://img.shields.io/badge/Plotly-3F4F75?style=flat-square&logo=plotly&logoColor=white) ![Jupyter](https://img.shields.io/badge/Jupyter-F37626?style=flat-square&logo=jupyter&logoColor=white) ![R](https://img.shields.io/badge/R-276DC3?style=flat-square&logo=r&logoColor=white) |

## Open-source projects

**[Gender bias in agentic resume screening](https://github.com/PD-BDS/Test_bias)** · MSc thesis<br>
Six research questions across five layers of an LLM screening pipeline: embedding retrieval, LLM screening, input format, prompt design and writing style. Bias is measured with SPD, DI, EOD and CFG; counterfactual augmentation, debiasing and calibration are evaluated as mitigations.<br>
`Python` `ChromaDB` `RAG` `Pydantic`

**[CO₂ emission forecasting](https://github.com/PD-BDS/CO2-Emission-Render)** · MLOps<br>
An attention LSTM that forecasts Danish power-grid emissions six hours ahead. GitHub Actions re-runs the ETL every six hours and retrains the model when accuracy drops. FastAPI backend, Streamlit dashboard, hosted on Render.<br>
`PyTorch` `FastAPI` `Streamlit` `SQLite` `GitHub Actions`

**[AI agent for data analysis](https://github.com/PD-BDS/AI-Agent-for-Data-Analysis)**<br>
Upload a dataset and ask a question in plain English; a crew of agents writes the SQL, interprets the result, drafts a short report and plots it.<br>
`CrewAI` `OpenAI` `SQLite` `Plotly` `Streamlit`

**[Deciphering BTC price movement](https://github.com/PD-BDS/Deciphering-BTC-Price-Movement)** · research<br>
Does online sentiment predict Bitcoin? BERT and FinBERT read Twitter, Google Trends and the Fear & Greed Index; LSTMs forecast direction. Accuracy reached 85–86% daily and 93–94% monthly.<br>
`TensorFlow` `Transformers` `LSTM` `scikit-learn`

**[Explainable AI on customer churn](https://github.com/PD-BDS/Explainable-AI-Study-on-Identifying-Factors-Affecting-Customer-Churn)** · research<br>
Compares feature-selection approaches (PCA, filter, wrapper, embedded) across random forest, XGBoost, SVM and logistic regression, with SHAP to explain the best model. Best F1 ≈ 0.91.<br>
`scikit-learn` `XGBoost` `SHAP` `SMOTE`

<details>
<summary><b>More</b></summary>
<br>

- **[AI Trip Planner](https://github.com/PD-BDS/AI-TripPlanner)**: two CrewAI crews turn a traveller profile into a day-by-day itinerary, using Serper and TripAdvisor for research.
- **[AI Piano Learning Planner](https://github.com/PD-BDS/AI-Piano-Learning-Planner)**: a small crew that writes a practice plan from level, goals and available time.
- **[AI Resume Shortlisting](https://github.com/PD-BDS/AI-Resume-Shorlisting-app)**: LLaMA 3.3 70B (via Groq) parses a job description and ranks candidates with a reason for each pick.
- **[Mental Health Status Classifier](https://github.com/PD-BDS/Mental-Health-Classifier)**: a fine-tuned BERT model that sorts free text into seven mental-health categories.
- **[Penguins Detector](https://github.com/PD-BDS/Penguins-detector)**: a species classifier with a daily GitHub Actions job that fetches new data and publishes the prediction.

</details>

## On GitHub

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/PD-BDS/PD-BDS/main/assets/readme/activity-dark.svg">
    <img src="./assets/readme/activity-light.svg" width="100%" alt="Contributions over the last 12 months with a weekly trend chart">
  </picture>
</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/PD-BDS/PD-BDS/main/assets/readme/languages-by-repo-dark.svg">
    <img src="./assets/readme/languages-by-repo-light.svg" width="49%" alt="Top languages by repository size: Python first, then TypeScript and JavaScript, then others">
  </picture>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/PD-BDS/PD-BDS/main/assets/readme/languages-by-commit-dark.svg">
    <img src="./assets/readme/languages-by-commit-light.svg" width="49%" alt="Top languages by commits over the last year: Python first, then TypeScript and JavaScript, then others">
  </picture>
</p>

<p align="center"><sub>Rebuilt daily by a GitHub Action from public and private repositories. Notebook and generated HTML/CSS output are excluded; TypeScript and JavaScript are grouped.</sub></p>

## Contact

For roles, collaborations or a conversation about agent systems and production ML: [dey.piyal97@gmail.com](mailto:dey.piyal97@gmail.com) or [LinkedIn](https://www.linkedin.com/in/piyal-dey-711015128/).
