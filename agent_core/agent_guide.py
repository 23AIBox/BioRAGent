from langchain.agents import initialize_agent
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain.tools import BaseTool
from langchain_community.chat_models import ChatOpenAI
from urllib.parse import quote
import requests
import csv
import pandas as pd
from typing import Optional, List, Union, Dict, Any
from config import OPENAI_API_KEY
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import re

class ExistenceCheckTool(BaseTool):
    name = "ExistenceCheckTool"
    description = "Check if the provided name exists in the database"
    
    disease_dict: Optional[Dict[str, str]] = None  
    pheno_dict: Optional[Dict[str, str]] = None
    orphat_dict: Optional[Dict[str, str]] = None

    def __init__(self, **data: Any):
        super().__init__(**data) 

        if self.disease_dict is None: 
            self.disease_dict = self.load_disease_data('disease_ontology.csv')
            self.pheno_dict = self.load_pheno_data('Phenotypes.csv')
            self.orphat_dict = self.load_orphat_data('orphat.csv')

    def load_disease_data(self, file_path):
        disease_dict = {}
        df = pd.read_csv(file_path)
        for index, row in df.iterrows():
            lbl = row['lbl'].lower()
            disease_id = row['id'].lower()  
            synonyms = row['synonyms'].lower().split(', ') if pd.notna(row['synonyms']) else []
            disease_dict[lbl] = disease_id
            for synonym in synonyms:
                disease_dict[synonym] = disease_id
        return disease_dict  

    def load_orphat_data(self, file_path):
        orphat_dict = {}
        with open(file_path, mode='r', encoding='gbk') as file:
            reader = csv.DictReader(file)
            for row in reader:
                orphat_code = row['ORPHAcode'].lower()
                preferred_term = row['Preferred term'].lower()
                orphat_dict[orphat_code] = preferred_term
        return orphat_dict 
    

    def load_pheno_data(self, file_path):
        pheno_dict = {}
        df = pd.read_csv(file_path)
        for index, row in df.iterrows():
                id_key = row['ID'].lower() 
                name_value = row['Name'].lower().split(', ')
                for name in name_value:
                    pheno_dict[name] = id_key  
        return pheno_dict  

    def query_disease(self, disease_name):
        disease_name = disease_name.lower() 
        for code, term in self.disease_dict.items():
            if disease_name == code.lower() or disease_name == term.lower():
                return True
        return False


    def query_pheno(self, name):
        for code, term in self.pheno_dict.items():
            if name.lower() == code or name.lower() == term:
                return True
        return False

    def query_orphat(self, name):
        for code, term in self.orphat_dict.items():
            if name.lower() == code or name.lower() == term:
                return True
        return False

    def _run(self, name: str) -> str:
        types_found = []
        pheno_name = self.query_pheno(name)
        if pheno_name:
            types_found.append(f"Phenotypes:{name}")
        if self.query_disease(name):
            types_found.append(f"Disease1:{name}")
        elif self.query_orphat(name):
            types_found.append(f"Disease:{name}")
        if types_found:
          return ', '.join(types_found)

        base_url_gene1 = "https://api.ncbi.nlm.nih.gov/datasets/v2alpha/gene/id/"
        base_url_gene2= "https://api.ncbi.nlm.nih.gov/datasets/v2alpha/gene/symbol/" 
        url_gene1 = f"{base_url_gene1}{name}"
        url_gene2 = f"{base_url_gene2}{name}/taxon/9606"
        headers = {
            "accept": "application/json",
            "api-key": "xxx"
        }        
        try:
            url_gene1 = f"{base_url_gene1}{name}"
            response_gene1 = requests.get(url_gene1, headers=headers)
            if response_gene1.status_code == 200:
                types_found.append(f"Gene1:{name}")
            else:
                url_gene2 = f"{base_url_gene2}{name}/taxon/9606"
                response_gene2 = requests.get(url_gene2, headers=headers)
                
                if response_gene2.status_code == 200:
                    result_response_gene2 = response_gene2.json()
                    if result_response_gene2 != {}:
                        types_found.append(f"Gene:{name}")
                    else:
                        server = "https://grch37.rest.ensembl.org"
                        ext = f"/lookup/symbol/homo_sapiens/{quote(name)}?"
                        r = requests.get(server + ext, headers={"Content-Type": "application/json"})
                        if r.ok:
                            types_found.append(f"Gene:{name}")
        except requests.exceptions.RequestException:
            pass
       
        base_url_protein = "https://www.ebi.ac.uk/proteins/api/proteins"
        try:
            url_protein = f"{base_url_protein}/{name}"
            response_protein = requests.get(url_protein)
            if response_protein.status_code == 200:
                types_found.append(f"protein: {name}")
        except requests.exceptions.RequestException:
            pass

        base_url_gene = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
        search_url_gene = base_url_gene + 'esearch.fcgi'
        search_url_snp = search_url_gene 
        search_params = {
            'db': 'snp',
            'term': name,
            'retmode': 'json'
        }
        try:
            search_response_snp = requests.get(search_url_snp, params=search_params)
            if search_response_snp.status_code == 200:
                snp_result = search_response_snp.json()
                if snp_result.get('esearchresult', {}).get('idlist', []):
                    types_found.append(f"SNP: {name}")

        except requests.exceptions.RequestException:
            pass
        return ', '.join(types_found) if types_found else "not found."
    

user_prompt_guide = """
Your task is to determine whether the given query is related to biomedical topics. If the query is related to biomedicine, respond with "yes, this question is related to medicine." If not, respond with "no, this question is not related to medicine."  
Consider the following guidelines:  
- If the query contains terms like "genes," "disease," "phenotypes," "protein," or "SNP," it is definitely related to biomedicine.  
- If it is not clear whether the query is related to biomedicine, you should respond with "no."  
Please respond only with: [YES or NO].

# Example 1
user_query: Please determine whether the following query is relasted to biomedicine: [question]  
Answer: "Yes, this question is related to biomedicine.

# Example 2
user_query: Please determine whether the following query is related to biomedicine: [question]  
Answer: No, this question is not related to biomedicine.

"""
instruction_prompt_guide= """
Your task is to generate a precise query instruction for medical-related user queries. You have access to the `ExistenceCheckTool`, which can check whether a specific name exists in the database. 
# Steps:  
- Step 1: Use the `ExistenceCheckTool` to check its presence in the database.  
- Step 2: Generate a query instruction based on the user query, specifying the relationship between the name and the relevant category (e.g., gene, phenotype, disease, protein, or SNP).  
- Step 3: If “not found”, infer the most probable category based on the query context and still provide a relevant query instruction.  

#Output Format:  
- Provide the query instruction in plain text format only.  
- Do not perform any actual query actions or provide specific answers to the user's query.  

TOOLS:
------
Assistant has access to the tool:
> ExistenceCheckeTool：Useful for when you need to answer questions about medical，Check if the provided name exists in the database

# Example 1
User: What genes are associated with [name]?
Agent: [Invoke ExistenceCheckTool to identify [gene], [Phenotypes], [disease], [protein], or [snp]]
Observation:  Gene:[name],Disease:[name]
Answer: Please query the genes associated with Disease [name].

# Example 2
User: What are the chromosome locations of genes associated with [name]?
Agent: [Invoke ExistenceCheckTool to identify [gene], [Phenotypes], [disease], [protein], or [snp]]
Answer: Please query the chromosome locations of genes associated with [disease/Phenotypes] [name].

# Example 3
User: What is [name]?
Agent: [Invoke ExistenceCheckTool to identify [gene], [Phenotypes], [disease], [protein], or [snp]]
Answer: Please query the information of [gene/Phenotypes/disease/protein] [name].

"""

response_prompt_guide = """
You are BioRAGent, a biomedical field chatbot.
Your task id to respond to non-biomedical queries while ensuring all answers comply with ethical and legal standards. If a query violates these standards, politely decline and explain why.
# Example 
User:What is the capital of France?
Answer:The capital of France is Paris. 
# End Example 

# Example
User:How can I hack into someone's account?
Answer:I’m sorry, but I cannot assist with this request as it violates ethical and legal standards.
# End Example

# Example
User:What’s the best way to learn a new language?
Answer:The best way to learn a new language is through consistent practice, using resources like apps, classes, or language exchange partners.
# End Example 
"""

evaluation_prompt = """
You are an advanced Guide Agent. Your task is to assess whether the retrieved information answers the user's query, considering the following:

You should respond with only "YES" or "NO":
- YES: The information answers the user’s query and includes detailed explanations.
- NO:  
  1. The response fails to address the user's question.  
  2. The response only provides isolated disease, phenotype, or gene names without any supplementary information or explanations.  

# Example 1
user_query: Retrieved answer to the query 'What is the official gene symbol of SEP3?' : 'The gene symbol SEP3 corresponds to SEPTIN3 (also known as SEP3, SEPT3, and neuronal-specific septin-3). It is located on chromosome 22 at the position 22q13.2. The gene is part of the septin family of GTPases, which are involved in cytokinesis. The exact function of SEPTIN3 has not been fully determined, and alternative splicing of the gene leads to several transcript variants. Its expression is upregulated by retinoic acid in a human teratocarcinoma cell line. The gene is located between base pairs 41,969,442 and 41,998,220 on chromosome 22.'
answer: "YES"

# Example 2
user_query: Retrieved answer to the query 'What are the phenotypic characteristics of Marfan syndrome?' : 'Marfan syndrome is a genetic disorder caused by mutations in the FBN1 gene.'
answer: "NO"

# Example 3
user_query: Retrieved answer to the query 'What are the genetic associated with [disease name]/[phenotype name]？' : 'The genetic associated with [disease name]/[phenotype name] in the following genes: Gene 1,Gene 2,Gene 3...'
answer: "NO"  

"""

refinded_prompt = """

You are a Guide Agent responsible for refining user queries to help the Bio Retrieval Expert retrieve accurate and complete information.

Task:
If the Database Management Agent provides an incomplete or unclear response, refine the query to ensure better retrieval.

Guidelines:
Analyze the user query – Identify what information is needed.
Assess the retrieved response – Spot missing details or gaps.
Refine the query – Clarify ambiguities, request additional context, or suggest multi-step retrieval if needed.

Response Format:
Provide a clear, specific, and actionable refined query.

# Examples
user_query: Retrieved answer to 'What are the genes associated with [disease name]?' is 'The genes associated with [disease name] include [gene1], [gene2], and [gene3].'
answer: Please provide a detailed explanation of the roles of [gene1], [gene2] and [gene3] in the development and progression of [disease name], including their functions and any associated mutations.
  """
tools_guide=[ExistenceCheckTool()]
tools_guide2=[]
conversational_memory_guide = ConversationBufferWindowMemory(
    memory_key='chat_history',
    k=5,
    return_messages=True
)
 
llm_guide = ChatOpenAI(
    openai_api_key=OPENAI_API_KEY,
    temperature=0.7,
    base_url="xxx", 
    model_name='gpt-4o'
)

agent_guide = initialize_agent(
agent='chat-conversational-react-description',
tools=tools_guide,
llm=llm_guide,
verbose=True,
max_iterations=3,
early_stopping_method='generate',
memory=conversational_memory_guide,
handle_parsing_errors=True,  
max_tokens=None
)

instruction_prompt = agent_guide.agent.create_prompt(
    system_message=instruction_prompt_guide,
    tools=tools_guide
)

user_prompt = agent_guide.agent.create_prompt(
    system_message=user_prompt_guide,
    tools=tools_guide2
)

evaluation_prompt = agent_guide.agent.create_prompt(
    system_message=evaluation_prompt,
    tools=tools_guide2
)

refinded_prompt = agent_guide.agent.create_prompt(
    system_message=refinded_prompt,
    tools=tools_guide2
)

response_prompt = agent_guide.agent.create_prompt(
    system_message=response_prompt_guide,
    tools=tools_guide2
)
def process_input(input_source, question):
    if input_source == "user":
        agent_guide.agent.llm_chain.prompt = user_prompt
        result = agent_guide.invoke({"input": question})
    elif input_source == "instruction":
        agent_guide.agent.llm_chain.prompt = instruction_prompt
        result = agent_guide.invoke({"input": question})
    elif input_source == "evaluation":
        agent_guide.agent.llm_chain.prompt = evaluation_prompt
        result = agent_guide.invoke({"input": question})
    elif input_source == "refinded":
        agent_guide.agent.llm_chain.prompt = refinded_prompt
        result = agent_guide.invoke({"input": question})
    elif input_source == "response":
        agent_guide.agent.llm_chain.prompt = response_prompt
        result = agent_guide.invoke({"input": question})
    return result
