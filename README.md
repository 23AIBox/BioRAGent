# BioRAGent

**BioRAGent** is a multi-agent biomedical assistant that integrates retrieval-augmented generation (RAG) techniques with specialized agents to enable natural language interaction for querying foundational knowledge of genes, diseases, and phenotypes, as well as their interconnections. It also supports queries about the basic properties of SNPs and proteins. This repository contains the core implementation and evaluation dataset.

---

## 📁 Repository Structure

### `agent_core/`
This folder contains the core source code of BioRAGent, including the implementation of three specialized agents and the orchestration logic that coordinates them.

**Key components:**

| File/Folder            | Description                                                  |
| ---------------------- | ------------------------------------------------------------ |
| `agent_guide.py`       | Guide agent |
| `agent_data.py`        | Retriever agent |
| `agent_val.py`         | Reviewer agent |
| `agent_main.py`        | Core script coordinating the interaction among the three agents. |
| `initialize_agents.py` | Initializes agent instances with appropriate configurations. |
| `main_test.py`         | Test script to verify system behavior in console mode.       |
| `streamlit_app.py`     | Streamlit-based web interface for interactive user testing.  |
| `config.py`            | Configuration file containing API keys. |
| `*.csv`                | Biomedical resource files (e.g., disease ontology, phenotypes). |
| `assistant.png`        | Assistant icon used in the Streamlit UI.                     |
| `user.png`             | User avatar used in the Streamlit UI.                        |

---

### `evaluation_task/`
This folder contains the evaluation dataset designed to assess the knowledge retrieval and reasoning capabilities of BioRAGent. The dataset covers a wide range of biomedical topics, including gene, protein, disease, phenotype, and SNP-related information. Each task consists of 50 question-answer pairs.

---
