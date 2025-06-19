from config import OPENAI_API_KEY
from langchain.tools import BaseTool
from langchain_community.chat_models import ChatOpenAI
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain.agents import initialize_agent
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing import List, Union, Dict, Any, Optional
from urllib.parse import urlencode, quote
from urllib3.exceptions import MaxRetryError, ProxyError
import requests
import json
import time
import re
import sys



def is_id(s):
            return s.startswith("HP:") and s[3:].isdigit()    

def hpo_id(phenotype_name):
    url_name = f"https://ontology.jax.org/api/hp/search?q={quote(phenotype_name)}&page=0&limit=10"    
    response = requests.get(url_name)   
    if response.status_code == 200:
        data = response.json()        
        for term in data.get('terms', []):
            name = term.get('name', '')
            synonyms = term.get('synonyms', [])           
            if phenotype_name.lower() in name.lower() or any(phenotype_name.lower() in synonym.lower() for synonym in synonyms):
                return term.get('id')
            else:
                return None

def get_phenotype_id(phenotype_term):
        if is_id(phenotype_term):
            return phenotype_term
        if phenotype_term.isdigit():
            return f"HP:{phenotype_term}"
        return hpo_id(phenotype_term)

def fetch_data(url, headers=None, params=None, max_retries=3, delay=5):
    for _ in range(max_retries):
        try:
            response = requests.get(url, headers=headers, params=params)  
            response.raise_for_status() 
            time.sleep(0.4) 
            return response.json() 
        except (MaxRetryError, ProxyError) as e:
            print(f"Connection error: {e}. Retrying...")
            time.sleep(delay)  
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            break  
    return None 

class PhenotypesInfoTool(BaseTool):
    name = "Phenotypes Info Extractor"
    description = "Use this tool to extract information from a given symptom/Phenotypes name"
    def _run(self, phenotype_term: str) -> str:
        phenotype_id=None
        phenotype_id = get_phenotype_id(phenotype_term)
        url_id = f"https://ontology.jax.org/api/hp/terms/{quote(str(phenotype_id))}"       
        data = fetch_data(url_id)
        return data if data else "Not Found"   
                   
class PhenotypesParentsTool(BaseTool):
    name = "Phenotypes Parents Extractor"
    description = "Use this tool to extract parents from a given symptom/Phenotypes name"
    def _run(self, phenotype_term: str) -> str:
        phenotype_id=None
        phenotype_id = get_phenotype_id(phenotype_term)
        url_id = f"https://ontology.jax.org/api/hp/terms/{quote(str(phenotype_id))}/parents"
        data = fetch_data(url_id)
        if data:
            result = [{'id': item['id'], 'name': item['name'], 'descendantCount': item['descendantCount']} for item in data]
            return result
        else:
            return "Not Found"

class PhenotypesChildrenTool(BaseTool):
    name = "Phenotypes Childrens Extractor"
    description = "Use this tool to extract symptom/Phenotypes children from a given symptom/Phenotypes name"
    def _run(self, phenotype_term: str) -> str:
        phenotype_id=None
        results = []
        phenotype_id = get_phenotype_id(phenotype_term)
        url_id = f"https://ontology.jax.org/api/hp/terms/{quote(str(phenotype_id))}/children"
        data = fetch_data(url_id)
        if data:
            result = [{'id': item['id'], 'name': item['name'], 'descendantCount': item['descendantCount']} for item in data]
            return result
        else:
            return "Not Found"

class PhenotypesDiseaseTool(BaseTool):
    name = "Phenotypes Disease Extractor"
    description = "Use this tool to extract diseases associated with the given phenotypes/symptom name"
    def _run(self, phenotype_term: str) -> Union[List[str], str]:
        phenotype_id=None
        phenotype_id = get_phenotype_id(phenotype_term)
        url_annotation = f"https://ontology.jax.org/api/network/annotation/{quote(str(phenotype_id))}"
        data = fetch_data(url_annotation)     
        if data and 'diseases' in data:
            return data['diseases']
        else:
            return "Not Found"

class PhenotypesGeneTool(BaseTool):
    name = "Phenotypes Gene Extractor"
    description = "Use this tool to extract genes associated with a given phenotypes/symptom name."
    def _run(self, phenotype_term: str) -> Union[List[str], str]:
        phenotype_id=None
        phenotype_id = get_phenotype_id(phenotype_term)
        url_annotation = f"https://ontology.jax.org/api/network/annotation/{quote(str(phenotype_id))}"
        data = fetch_data(url_annotation)    
        if data and 'genes' in data:
            return data['genes']
        else:
            return "Not Found"

class GenePhenotypesTool(BaseTool):
    name = "Gene Phenotypes Extractor"
    description = "Use this tool to extract Phenotypes associated with a gene for a given term"
    def _run(self, gene_term: str) -> Union[List[str], str]:
        gene_id = None

        def is_gene_id(s):
            return s.startswith("NCBIGene:") and s[9:].isdigit()
        if is_gene_id(gene_term):
            gene_id = gene_term
        elif gene_term.isdigit():
            gene_id = f"NCBIGene:{gene_term}"
        else:
            url_name = f"https://ontology.jax.org/api/network/search/gene?q={quote(gene_term)}&page=0&limit=10"
            response = fetch_data(url_name)
            if response and 'results' in response and len(response['results']) > 0:
                gene_id = response['results'][0]['id']
            else:
                return "Not Found"
        if gene_id is None:
            return "Not Found"
        url_annotation = f"https://ontology.jax.org/api/network/annotation/{quote(str(gene_id))}"
        response = fetch_data(url_annotation)
        if response and 'phenotypes' in response:
            return response['phenotypes']

        return "Not Found"   
    
class GeneDiseaseTool(BaseTool):
    name = "Gene Diseases Extractor"
    description = "Use this tool to extract Diseases associated with a gene for a given term"
    def _run(self, gene_term: str) -> Union[List[str], str]:        
        gene_id = None
        def is_gene_id(s):
            return s.startswith("NCBIGene:") and s[9:].isdigit()

        if is_gene_id(gene_term):
            gene_id = gene_term
        elif gene_term.isdigit():
            gene_id = f"NCBIGene:{gene_term}"
        else:
            url_name = f"https://ontology.jax.org/api/network/search/gene?q={quote(gene_term)}&page=0&limit=10"
            response = fetch_data(url_name)
            if response and 'results' in response and len(response['results']) > 0:
                gene_id = response['results'][0]['id']
            else:
                return "Not Found" 
        if gene_id is None:
            return "Not Found"
        url_annotation = f"https://ontology.jax.org/api/network/annotation/{quote(str(gene_id))}"
        response = fetch_data(url_annotation)
        if response and 'diseases' in response:
            return response['diseases']
        return "Not Found"

class DiseasePhenotypesTool(BaseTool):
    name = "Disease Phenotypes Extractor"
    description = "Use this tool to extract the phenotypes associated with the given disease name."
    def _run(self, disease_term: str) -> Union[str, None]:
            disease_id=None
            def is_disease_id(s):
                 return (s.startswith("OMIM:") and s[5:].isdigit()) or (s.startswith("ORPHA:") and s[6:].isdigit())
            if not disease_term.isdigit():
                if is_disease_id(disease_term):
                    disease_id=disease_term
                else:
                    url_name = f"https://ontology.jax.org/api/network/search/disease?q={quote(str(disease_id))}&page=0&limit=10"
                    response = fetch_data(url_name) 
                    if response and 'results' in response:
                        disease_name = response['results'][0]['name']
                        if disease_name.lower() == disease_term.lower():
                            disease_id = response['results'][0]['id']                                       
                if disease_id is None:
                    return "Not Found"
                url_annotation = f"https://ontology.jax.org/api/network/annotation/{quote(str(disease_id))}"
                response = fetch_data(url_annotation) 
                if response and 'categories' in response:
                    return response['categories']
                else:
                    return "Not Found"
            else:
                disease_id = f"OMIM:{disease_term}"
                url_annotation = f"https://ontology.jax.org/api/network/annotation/{quote(disease_id)}"
                response = fetch_data(url_annotation)  
                if response and 'categories' in response:
                    return response['categories']
                else:
                    disease_id = f"ORPHA:{disease_term}"
                    url_annotation = f"https://ontology.jax.org/api/network/annotation/{quote(disease_id)}"
                    response = fetch_data(url_annotation) 
                    if response and 'categories' in response:
                        return response['categories']
                    else:
                        return "Not Found"                 
               
class ProteinInfoTool(BaseTool):
    name = "Protein Information Extractor"
    description = "Use this tool to extract protein information from UniProt API"

    def _run(self, term: str) -> Optional[str]:
        search_url = f'https://rest.uniprot.org/uniprotkb/search?query={term}'
        base_url = "https://www.ebi.ac.uk/proteins/api/proteins"
        search_response = fetch_data(search_url)
        if not search_response:
            print(f"Error: Unable to fetch data from UniProt.")
            return None

        for entry in search_response.get('results', []):
            primary_accession = entry.get('primaryAccession', '')
            uni_protkb_id = entry.get('uniProtkbId', '')
            recommended_name = entry.get('proteinDescription', {}).get('recommendedName', {}).get('fullName', {}).get('value', '')
            alternative_names = [
                name.get('fullName', {}).get('value', '') 
                for name in entry.get('proteinDescription', {}).get('alternativeNames', [])
            ]

            if term.lower() in (primary_accession.lower(), *map(str.lower, alternative_names)) or \
               f"{term}_HUMAN".lower() == uni_protkb_id.lower():
                protein_id = primary_accession
                protein_url = f"{base_url}/{protein_id}"

                protein_response = fetch_data(protein_url)
                if not protein_response:
                    print(f"Error: Unable to fetch detailed protein information for '{protein_id}'.")
                    return None
                comment_types = {
                    "FUNCTION": [],
                    "PTM": [],
                    "SUBUNIT": [],
                    "INTERACTION": [],
                    "TISSUE_SPECIFICITY": [],
                    "MASS_SPECTROMETRY": [],
                    "DISEASE": [],
                    "POLYMORPHISM": [],
                    "MISCELLANEOUS": [],
                    "SIMILARITY": [],
                    "CAUTION": []
                }

                for comment in protein_response.get('comments', []):
                    comment_type = comment.get('type')
                    if comment_type in comment_types:
                        if comment_type == "INTERACTION":
                            comment_types[comment_type].extend(comment.get('interactions', []))
                        elif comment_type == "MASS_SPECTROMETRY":
                            comment_types[comment_type].append({
                                "type": comment.get('type'),
                                "molecule": comment.get('molecule'),
                                "method": comment.get('method'),
                                "mass": comment.get('mass'),
                                "error": comment.get('error')
                            })
                        elif comment_type == "DISEASE":
                            comment_types[comment_type].append({
                                "type": comment.get('type'),
                                "diseaseId": comment.get('diseaseId'),
                                "acronym": comment.get('acronym'),
                                "dbReference": comment.get('dbReference'),
                                "description": comment.get('description', {}).get('value', '')
                            })
                        else:
                            comment_types[comment_type].extend(
                                text.get('value', '') for text in comment.get('text', []) if isinstance(text, dict)
                            )

                output = {
                    "id": protein_response.get("id"),
                    "accession": protein_response.get("accession"),
                    "secondaryAccession": protein_response.get("secondaryAccession"),
                    "protein": protein_response.get("protein"),
                    "alternativeName": protein_response.get("alternativeName"),
                    "gene": protein_response.get("gene"),
                    "comments": comment_types,
                    "sequence": protein_response.get("sequence", {}).get("sequence", "")
                }
                return json.dumps(output, indent=4)

        print(f"No matching protein found for '{term}'.")
        return None
    
class GeneInfoTool(BaseTool):
    name = "Gene Information Tool"
    description = "Use this tool to fetch gene information with given gene name."
    def _run(self, search_term: Union[str, List[str]]) -> str:
        base_url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
        search_url = base_url + 'esearch.fcgi'
        summary_url = base_url + 'esummary.fcgi'
        base_url_gene = "https://api.ncbi.nlm.nih.gov/datasets/v2alpha/gene/symbol/"
        headers = {
            "accept": "application/json",
            "api-key": "b27855b4a18aa2aa178fc22083d0c07ee308"
        }
        if isinstance(search_term, list):
            search_term = ','.join(search_term)
        search_terms = [term.strip() for term in search_term.split(',')]
        gene_information_dict = {}

        def fetch_gene_id(term: str) -> Optional[str]:
            """Fetch gene ID for a given term."""
            if term.isdigit():
                return term
            url = f"{base_url_gene}{term}/taxon/9606"
            response = fetch_data(url, headers=headers)
            if response and 'reports' in response:
                return response['reports'][0]['gene']['gene_id']
            return None

        def fetch_gene_info(gene_id: str) -> Optional[dict]:
            """Fetch detailed gene information using gene ID."""
            search_params = {'db': 'gene', 'term': gene_id, 'retmode': 'json'}
            search_response = fetch_data(search_url, params=search_params)
            if search_response and 'esearchresult' in search_response:
                gene_ids = search_response['esearchresult'].get('idlist', [])
                if gene_ids:
                    summary_params = {'db': 'gene', 'id': ','.join(gene_ids), 'retmode': 'json'}
                    summary_response = fetch_data(summary_url, params=summary_params)
                    if summary_response and 'result' in summary_response:
                        return summary_response['result']
            return None
        for term in search_terms:
            gene_id = fetch_gene_id(term)
            if gene_id:
                gene_info = fetch_gene_info(gene_id)
                if gene_info:
                    gene_information_dict[term] = gene_info
                else:
                    server = "https://grch37.rest.ensembl.org"
                    ext = f"/lookup/symbol/homo_sapiens/{term}?"
                    response = fetch_data(server + ext, headers={"Content-Type": "application/json"})
                    if response:
                        gene_information_dict[term] = response
        if not gene_information_dict:
            return "Not Found"
        return json.dumps(gene_information_dict, indent=4)


class DiseaseInfoTool(BaseTool):
    name = "Disease Information Extractor"
    description = "Use this tool to extract detailed disease information in JSON format for a given term"
    def _run(self, disease_name: str) -> Union[str, None]:
        def fetch_bioontology_info(disease_name):
            url = f'https://data.bioontology.org/search?q={disease_name}'
            headers = {'Authorization': 'apikey token=bd2f8372-cac9-4ed6-8f56-7e24b5c87e85'}
            response = fetch_data(url, headers=headers)
            if response:
                collection = response.get('collection', [])
                for item in collection:
                    if disease_name.lower() in [item.get('prefLabel', '').lower()] + \
                            [syn.lower() for syn in item.get('synonym', [])]:
                        return {
                            'prefLabel': item.get('prefLabel', ''),
                            'synonym': item.get('synonym', []),
                            'definition': item.get('definition', [])
                        }
            return None

        def fetch_orpha_info(disease_name):
            url = f"https://api.orphadata.com/rd-cross-referencing/orphacodes/names/{quote(disease_name)}?lang=en"
            response = fetch_data(url)
            if response and "data" in response and "results" in response["data"]:
                data = response["data"]["results"]
                return {
                    "ORPHAcode": data.get("ORPHAcode", ""),
                    "preferredTerm": data.get("Preferred term", ""),
                    "summary": data.get("SummaryInformation", [{}])[0].get("Definition", ""),
                    "Synonym": data.get("Synonym", [])
                }
            return None

        def fetch_hpo_info(disease_name):
            url = f"https://ontology.jax.org/api/network/search/disease?q={quote(disease_name)}&page=0&limit=10"
            response = fetch_data(url)
            if response and response.get("results"):
                data = response["results"][0]
                return {
                    "id": data.get("id", ""),
                    "name": data.get("name", ""),
                    "mondoId": data.get("mondoId", ""),
                    "description": data.get("description", [])
                }
            return None
        combined_result = {
            'Bioontology': fetch_bioontology_info(disease_name),
            'Orpha': fetch_orpha_info(disease_name),
            'HPO': fetch_hpo_info(disease_name)
        }
        combined_result = {key: value for key, value in combined_result.items() if value}
        return combined_result if combined_result else "Not Found"

class DiseaseGeneTool(BaseTool):
    name = "Disease Gene Extractor"
    description = "Use this tool to extract genes associated with a given disease."

    def _run(self, disease_term: str) -> Union[str, None]:
        def is_disease_id(s: str) -> bool:
            """Check if the string is a disease ID (OMIM or ORPHA)."""
            return (s.startswith("OMIM:") and s[5:].isdigit()) or (s.startswith("ORPHA:") and s[6:].isdigit())

        def fetch_genes_by_id(disease_id: str) -> Optional[List[str]]:
            """Fetch genes associated with a disease ID."""
            url_annotation = f"https://ontology.jax.org/api/network/annotation/{quote(disease_id)}"
            response = fetch_data(url_annotation)
            return response.get('genes', []) if response else None

        def fetch_disease_id_by_name(disease_name: str) -> Optional[str]:
            """Fetch disease ID by name."""
            url_name = f"https://ontology.jax.org/api/network/search/disease?q={quote(disease_name)}&page=0&limit=10"
            response = fetch_data(url_name)
            if response and 'results' in response and response['results']:
                for item in response['results']:
                    if item['name'].lower() == disease_name.lower():
                        return item['id']
            return None
        
        annotation_result = []
        if disease_term.isdigit():
            disease_id = f"OMIM:{disease_term}"
            genes = fetch_genes_by_id(disease_id)
            if genes:
                return genes
            disease_id = f"ORPHA:{disease_term}"
            genes = fetch_genes_by_id(disease_id)
            if genes:
                return genes
        elif is_disease_id(disease_term):
            genes = fetch_genes_by_id(disease_term)
            if genes:
                return genes
        else:
            disease_id = fetch_disease_id_by_name(disease_term)
            if disease_id:
                genes = fetch_genes_by_id(disease_id)
                if genes:
                    return genes

        base_url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
        search_url = base_url + 'esearch.fcgi'
        summary_url = base_url + 'esummary.fcgi'
        search_params = {'db': 'omim', 'term': disease_term, 'retmode': 'json'}
        search_response = fetch_data(search_url, params=search_params)
        if search_response and 'esearchresult' in search_response and 'idlist' in search_response['esearchresult']:
            gene_ids = search_response['esearchresult']['idlist']
            summary_params = {'db': 'omim', 'id': ','.join(gene_ids), 'retmode': 'json'}
            summary_response = fetch_data(summary_url, params=summary_params)
            if summary_response and 'result' in summary_response and 'uids' in summary_response['result']:
                for uid in summary_response['result']['uids']:
                    title = summary_response['result'][uid]['title']
                    parts = title.split(';')
                    if len(parts) > 1:
                        annotation_result.append(parts[-1].strip())
                return annotation_result
        return "Not Found"


class SNPInfoTool(BaseTool):
    name = "SNP Information Extractor"
    description = "Use this tool to extract detailed SNP information in JSON format for a given term"
    def _run(self, snp_term: str) -> Union[dict, None]:
        base_url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
        search_url = base_url + 'esearch.fcgi'
        summary_url = base_url + 'esummary.fcgi'
        search_params = {
            'db': 'snp',
            'term': snp_term,
            'retmode': 'json'
        }
        search_response = fetch_data(search_url, params=search_params)
        if not search_response:
            return "Request failed or no results found"

        snp_ids = search_response.get('esearchresult', {}).get('idlist', [])
        if not snp_ids:
            print(f"No results found for '{snp_term}'.")
            return None
        summary_params = {
            'db': 'snp',
            'id': ','.join(snp_ids),
            'retmode': 'json'
        }
        summary_response = fetch_data(summary_url, params=summary_params)
        if not summary_response:
            print("Failed to retrieve SNP summary information.")
            return None
        return summary_response
   
sys_msg =  """
You are an AI database administrator supported by the Human Phenotype Ontology ,UniProt and NCBI database. 
You can perform queries based on specified statements. You are an assistant equipped with the following set of tools. Please use the tools to answer questions and do not attempt to answer on your own.
Here are the names and descriptions of each tool:
Phenotypes Info Extractor:Use this tool to extract symptom/Phenotypes information from a given symptom/Phenotypes name.
Phenotypes Parents Extractor:Use this tool to extract symptom/Phenotypes parents from a given symptom/Phenotypes name.
Phenotypes Childrens Extractor:"Use this tool to extract symptom/Phenotypes children from a given symptom/Phenotypes name.
Phenotypes Disease Extractor:Use this tool to extract diseases associated with the given phenotypes/symptom name.
Phenotypes Gene Extractor:Use this tool to extract genes associated with a given phenotypes/symptom name.
Gene Information Tool:Use this tool to fetch gene information with given gene name.
Gene Phenotypes Extractor:Use this tool to extract Phenotypes associated with a gene for a given term.
Gene Diseases Extractor:Use this tool to extract Diseases associated with a gene for a given term.
Disease Phenotypes Extractor:Use this tool to extract the phenotypes associated with the given disease name.
Disease Information Extractor:Use this tool to extract detailed disease information in JSON format for a given term.
Disease Gene Extractor:"Use this tool to extract genes associated with a given disease.
Protein Information Extractor:Use this tool to extract protein information from UniProt API.
SNP Information Extractor:Use this tool to extract detailed SNP information in JSON format for a given term.

1.When a user's question cannot be answered directly using a single tool, please attempt to use two or more tools and integrate the outputs of all tools to provide an answer.
When there are multiple gene names, instead of querying the tools one by one, all gene names should be input together into the tool (e.g., as a list or comma-separated string) to retrieve the information in a single step.
###example
User: What are the chromosome locations of the genes related to [disease name]?
Agent: [Invoke DiseaseGeneTool to identify [gene name] or [gene id] related to [disease name]].The genes related to [disease name] are [gene1,gene2,gene3...]..
Agent: [Invoke GeneInfoTool to query the information of [gene1,gene2,gene3...]]
answer:List chromosome locations of the genes related to [disease name]:
gene1:location1;gene2:location2...
###end of example 

2.When inquiring about genes and phenotype information related to a disease, if no answer is found, the [DiseaseInfoTool] can be used to retrieve basic information about the disease as an additional supplement to the response.
###example
User: Please query the genes/symptom/Phenotypes related to [disease name].
Agent:[Invoke [DiseaseGeneTool]/[DiseasePhenotypesTool]]
when answer:Not Found
Agent:[Invoke [DiseaseInfoTool] to retrieve information about the [disease name]]
answer:

3.When querying for genes associated with a disease/symptom/Phenotypes, invoke the GeneInfoTool to supplement the response with detailed gene information, ensuring a more comprehensive answer.

###end of example 

If no relevant information is found using the tools or if the answer cannot be resolved through available resources, please do not attempt to answer the question on your own. Instead, respond with:
"Sorry, I could not find relevant information to answer query."
"""
   
llm = ChatOpenAI(
    openai_api_key=OPENAI_API_KEY,
    temperature=0,
    base_url="xxx", 
    model_name='gpt-4o'
)

conversational_memory = ConversationBufferWindowMemory(
    memory_key='chat_history',
    k=5,
    return_messages=True
)
# 初始化工具列表
tools = [PhenotypesInfoTool(),PhenotypesParentsTool(),PhenotypesChildrenTool(),PhenotypesDiseaseTool(),PhenotypesGeneTool(),GenePhenotypesTool(),GeneDiseaseTool(),GeneInfoTool(),DiseasePhenotypesTool(),DiseaseInfoTool(),DiseaseGeneTool(),ProteinInfoTool(),SNPInfoTool()]
# 初始化 agent with tools
agent_data = initialize_agent(
    agent='chat-conversational-react-description',
    tools=tools,
    llm=llm,
    verbose=True,
    max_iterations=3,
    early_stopping_method='generate',
    memory=conversational_memory,
    max_tokens=None, 
    handle_parsing_errors=True
)
new_prompt = agent_data.agent.create_prompt(
    system_message=sys_msg,
    tools=tools
)
agent_data.agent.llm_chain.prompt = new_prompt
