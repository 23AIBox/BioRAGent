# BioRAGent

**BioRAGent** is a multi-agent biomedical assistant that integrates retrieval-augmented generation (RAG) techniques with specialized agents to enable natural language interaction for querying foundational knowledge of genes, diseases, and phenotypes, as well as their interconnections. It also supports queries about the basic properties of SNPs and proteins. This repository contains the core implementation and evaluation dataset.

---

## 📁 Repository Structure

### `agent_core/`

This folder contains the core source code of BioRAGent, including the implementation of three specialized agents and the orchestration logic that coordinates them.

**Key components:**

| File/Folder            | Description                                                  |
| :--------------------- | :----------------------------------------------------------- |
| `agent_guide.py`       | Guide agent                                                  |
| `agent_data.py`        | Retriever agent                                              |
| `agent_val.py`         | Reviewer agent                                               |
| `agent_main.py`        | Core script coordinating the interaction among the three agents. |
| `initialize_agents.py` | Initializes agent instances with appropriate configurations. |
| `streamlit_app.py`     | Streamlit-based web interface for interactive user testing.  |
| `config.py`            | Configuration file containing API keys.                      |
| `*.csv`                | Biomedical resource files (e.g., disease ontology, phenotypes). |
| `assistant.png`        | Assistant icon used in the Streamlit UI.                     |
| `user.png`             | User avatar used in the Streamlit UI.                        |

---

### `evaluation_task/`

This folder contains the evaluation dataset designed to assess the knowledge retrieval and reasoning capabilities of BioRAGent. The dataset covers a wide range of biomedical topics, including gene, protein, disease, phenotype, and SNP-related information. Each evaluation task contains 50 question-answer pairs, formatted as two fields: Question and Goldstandard.

Below are detailed descriptions of each task:

**Single_hop_Task/**

- **Gene Function**
  Questions ask about the biological function of specific genes.
- **Protein Function**
  Questions focus on the functions of specific proteins.
- **Phenotype Definition**
  Questions query the definition or characterization of specific phenotypes. Answers describe observable traits or conditions.
- **Disease Definition**
  Questions ask about specific diseases. Answers provide brief explanations of their nature, symptoms, or causes.
- **Gene Alias**
  Given a gene alias or non-standard name, the task is to return the official gene symbol.
- **Gene Location**
  Questions ask which chromosome a given gene is located on. Answers are standard chromosome identifiers (e.g., chr1, chrX).
- **SNP Location**
  Questions involve identifying the chromosome on which a specific SNP is located.
- **Gene SNP Association**
  Given an SNP ID, the task is to identify associated gene(s).
- **Gene Disease Association**
  Questions ask for genes known to be associated with specific diseases.
- **Phenotype Gene Association**
  Given a phenotype, the task is to identify associated genes.
- **Phenotype Disease Association**
  Given a phenotype, the task is to identify related diseases.

**Multi_hop_Task/**

- **SNP Gene Function**

  Questions ask for the function of genes related to a specific SNP.

- **Disease Gene Location**

  Questions ask for the chromosome locations of genes associated with a specific disease.

- **Phenotype Gene Location**

  Questions ask for chromosome locations of genes linked to a given phenotype.

---

### `evaluation_llm/`

This folder contains the code used to evaluate BioRAGent's performance against other LLMs. Each file corresponds to a specific LLM, allowing for comparative analysis. For models not represented in this folder, evaluations were performed via their respective official online platforms. Additionally, the folder includes code for assessing consistency between human judgments and LLM-generated responses.

---

### `ablation_study/`

This folder contains the code for our ablation studies. This code allows for testing BioRAGent’s performance when specific components are removed, demonstrating their contribution to the overall effectiveness of BioRAGent.

---

### `extensibility_tool/`

This folder containss newly added extensible tools and their corresponding test datasets.

---



## ⚙️ Reproducibility and Setup

We provide a `Dockerfile` to create a consistent and reproducible environment for running BioRAGent.

**Build the Docker Image:**
Navigate to the root directory of this repository and run the following command to build the Docker image:

```bash
docker build -t bioragent .
```

### Running BioRAGent

**Run Core BioRAGent :**
To query BioRAGent from your console, use the following command. Replace `"What is gene BRCA1?"` with your desired question.

```bash
docker run --rm -v $(pwd):/app bioragent python agent_core/agent_main.py "What is gene BRCA1?"
```

**Run Streamlit Web Interface:**
To launch the interactive web interface for BioRAGent, use this command:

```bash
docker run --rm -v $(pwd):/app -p 8501:8501 bioragent streamlit run /app/agent_core/streamlit_app.py --server.port=8501 --server.address=0.0.0.0
```

### Running Evaluation **Module**

**Run Comparative LLM Evaluation:**
To run an evaluation against a specific LLM, use the following command. Remember to replace `Llama-3.3.py` with the actual LLM evaluation file (e.g., `GPT-4o.py`), `Single_hop_Task/nomenclature/gene_alias.csv` with the desired input dataset path, and `llama3.3_result.csv` with your desired output file name.

```bash
docker run --rm -v $(pwd):/app bioragent python evaluation_llm/Llama-3.3.py --input evaluation_task/Single_hop_Task/nomenclature/gene_alias.csv --output evaluation_result/llama3.3_result.csv
```

**Run Ablation Study:**
To run an ablation experiment, use the following command. Replace `no_reviewer.py` with the specific ablation file you wish to run, `Single_hop_Task/nomenclature/gene_alias.csv` with the input dataset, and `no_reviewer_result.csv` with the desired output file name.

```bash
docker run --rm -v $(pwd):/app bioragent python ablation_study/no_reviewer.py --input evaluation_task/Single_hop_Task/nomenclature/gene_alias.csv --output ablation_result/no_reviewer_result.csv
```

