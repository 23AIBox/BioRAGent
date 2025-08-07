import os
import sys
import openai
import json
import requests
from urllib.parse import quote
from typing import List, Union
from requests.exceptions import ProxyError
from urllib3.exceptions import MaxRetryError
import time
import argparse
from dotenv import load_dotenv
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from evaluation_llm.evaluator import evaluate_csv  

load_dotenv()

os.environ["HTTP_PROXY"] = os.getenv("HTTP_PROXY")
os.environ["HTTPS_PROXY"] = os.getenv("HTTPS_PROXY")

api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("BASE_URL")

client =  openai.OpenAI(
    base_url=base_url,
    api_key=api_key
)

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
            return response.json()
        except (MaxRetryError, ProxyError) as e:
            print(f"Connection error: {e}. Retrying...")
            time.sleep(delay)
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            break
    return None

def phenotypes_info_extractor(phenotype_term):
    phenotype_id = get_phenotype_id(phenotype_term)
    url_id = f"https://ontology.jax.org/api/hp/terms/{quote(str(phenotype_id))}"
    data = fetch_data(url_id)
    return data if data else "Not Found"

def phenotypes_disease_extractor(phenotype_term):
    phenotype_id = get_phenotype_id(phenotype_term)
    url_annotation = f"https://ontology.jax.org/api/network/annotation/{quote(str(phenotype_id))}"
    data = fetch_data(url_annotation)
    if data and 'diseases' in data:
        return data['diseases']
    return "Not Found"

def phenotypes_gene_extractor(phenotype_term):
        phenotype_id=None
        phenotype_id = get_phenotype_id(phenotype_term)
        url_annotation = f"https://ontology.jax.org/api/network/annotation/{quote(str(phenotype_id))}"
        data = fetch_data(url_annotation)    
        if data and 'genes' in data:
            return data['genes']
        else:
            return "Not Found"

def phenotypes_parents_extractor(phenotype_term):
        phenotype_id=None
        phenotype_id = get_phenotype_id(phenotype_term)
        url_id = f"https://ontology.jax.org/api/hp/terms/{quote(str(phenotype_id))}/parents"
        data = fetch_data(url_id)
        if data:
            result = [{'id': item['id'], 'name': item['name'], 'descendantCount': item['descendantCount']} for item in data]
            return result
        else:
            return "Not Found"
        
def phenotypes_children_extractor(phenotype_term):
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

def phenotypes_descendants_extractor(phenotype_term):
        results = []
        phenotype_id=None
        phenotype_id = get_phenotype_id(phenotype_term)
        url_id = f"https://ontology.jax.org/api/hp/terms/{quote(str(phenotype_id))}/descendants"
        data = fetch_data(url_id)
        if data:
            result = [{'id': item['id'], 'name': item['name'], 'descendantCount': item['descendantCount']} for item in data]
            return result
        else:
            return "Not Found"
        
def gene_phenotypes_extractor(gene_term):
        gene_id=None
        def is_gene_id(s):
            # 判断是否是表型ID的简单检查：以HP:开头并跟着数字
            return s.startswith("NCBIGene:") and s[9:].isdigit()
        #判断输入的是表型id还是name    
        if is_gene_id(gene_term):
            gene_id=gene_term
        elif gene_term.isdigit():
            gene_id = f"NCBIGene:{gene_term}"
        else:
            url_name = f"https://ontology.jax.org/api/network/search/gene?q={quote(gene_term)}&page=0&limit=10"
            response = fetch_data(url_name)  # 使用重试机制
            if response and 'results' in response:
                gene_id = response['results'][0]['id']    
        if gene_id is None:
            return "Not Found"   
        url_annotation = f"https://ontology.jax.org/api/network/annotation/{quote(str(gene_id))}"
        response = fetch_data(url_annotation)  # 使用重试机制
        if response and 'phenotypes' in response:
            return response['phenotypes']
        return "Not Found"    

def gene_diseases_extractor(gene_term):
        gene_id=None
        def is_gene_id(s):
            # 判断是否是表型ID的简单检查：以HP:开头并跟着数字
            return s.startswith("NCBIGene:") and s[9:].isdigit()
        #判断输入的是表型id还是name    
        if is_gene_id(gene_term):
            gene_id=gene_term
        elif gene_term.isdigit():
            gene_id = f"NCBIGene:{gene_term}"
        else:
            url_name = f"https://ontology.jax.org/api/network/search/gene?q={quote(gene_term)}&page=0&limit=10"
            response = fetch_data(url_name)  # 使用重试机制
            if response and 'results' in response:
                gene_id = response['results'][0]['id']
        if gene_id is None:
            return "Not Found"       
        url_annotation = f"https://ontology.jax.org/api/network/annotation/{quote(str(gene_id))}"
        response = fetch_data(url_annotation)  # 使用重试机制
        if response and 'diseases' in response:
            return response['diseases']
        return "Not Found"

def disease_phenotypes_extractor(disease_term):
            disease_id=None
            def is_disease_id(s):
                # 判断是否是表型ID的简单检查：以HP:开头并跟着数字
                 return (s.startswith("OMIM:") and s[5:].isdigit()) or (s.startswith("ORPHA:") and s[6:].isdigit())
            #判断输入的是表型id还是name 
            if not disease_term.isdigit():
                if is_disease_id(disease_term):
                    disease_id=disease_term
                else:
                    url_name = f"https://ontology.jax.org/api/network/search/disease?q={quote(str(disease_id))}&page=0&limit=10"
                    response = fetch_data(url_name)  # 使用重试机制
                    if response and 'results' in response:
                        disease_name = response['results'][0]['name']
                        if disease_name.lower() == disease_term.lower():
                            disease_id = response['results'][0]['id']                                       
                if disease_id is None:
                    return "Not Found"
                url_annotation = f"https://ontology.jax.org/api/network/annotation/{quote(str(disease_id))}"
                response = fetch_data(url_annotation)  # 使用重试机制
                if response and 'categories' in response:
                    return response['categories']
                else:
                    return "Not Found"
            else:
                # 如果输入的是数字，尝试OMIM或ORPHA
                disease_id = f"OMIM:{disease_term}"
                url_annotation = f"https://ontology.jax.org/api/network/annotation/{quote(disease_id)}"
                response = fetch_data(url_annotation)  # 使用重试机制
                if response and 'categories' in response:
                    return response['categories']
                else:
                    disease_id = f"ORPHA:{disease_term}"
                    url_annotation = f"https://ontology.jax.org/api/network/annotation/{quote(disease_id)}"
                    response = fetch_data(url_annotation)  # 使用重试机制
                    if response and 'categories' in response:
                        return response['categories']
                    else:
                        return "Not Found"

def protein_information_extractor(term):
            url = f'https://rest.uniprot.org/uniprotkb/search?query={term}'
            base_url = "https://www.ebi.ac.uk/proteins/api/proteins"

            # Send request to Uniprot API with retry mechanism
            response = fetch_data(url)

            if response:
                # Iterate through the results
                for entry in response.get('results', []):
                    primary_accession = entry.get('primaryAccession', '')
                    uni_protkb_id = entry.get('uniProtkbId', '')
                    recommended_name = entry.get('proteinDescription', {}).get('recommendedName', {}).get('fullName', {}).get('value', '')
                    alternative_names = [name.get('fullName', {}).get('value', '') for name in entry.get('proteinDescription', {}).get('alternativeNames', [])]

                    if (term.lower() in (primary_accession.lower(), *[name.lower() for name in alternative_names]) or
                        f"{term}_HUMAN".lower() == uni_protkb_id.lower()):
                        protein_id = primary_accession
                        print(protein_id)
                        url_protein = f"{base_url}/{protein_id}"

                        # Send GET request to get protein data with retry mechanism
                        response_protein = fetch_data(url_protein)

                        if response_protein:
                            # Extract comments
                            function_comments = []
                            subunit_comments = []
                            interaction_comments = []
                            tissue_comments = []
                            mass_comments = []
                            disease_comments = []
                            polymorphism_comments = []
                            miscellaneous_comments = []
                            similarity_comments = []
                            caution_comments = []
                            ptm_comments = []

                            for comment in response_protein.get('comments', []):
                                comment_type = comment.get('type')
                                text_list = [text.get('value', '') for text in comment.get('text', []) if isinstance(text, dict)]

                                if comment_type == 'FUNCTION':
                                    function_comments.extend(text_list)
                                elif comment_type == 'PTM':
                                    ptm_comments.extend(text_list)
                                elif comment_type == 'SUBUNIT':
                                    subunit_comments.extend(text_list)
                                elif comment_type == 'INTERACTION':
                                    interaction_comments.extend(comment.get('interactions', []))
                                elif comment_type == 'TISSUE_SPECIFICITY':
                                    tissue_comments.extend(text_list)
                                elif comment_type == 'MASS_SPECTROMETRY':
                                    mass_info = {
                                        "type": comment.get('type'),
                                        "molecule": comment.get('molecule'),
                                        "method": comment.get('method'),
                                        "mass": comment.get('mass'),
                                        "error": comment.get('error')
                                    }
                                    mass_comments.append(mass_info)
                                elif comment_type == 'DISEASE':
                                    disease_info = {
                                        "type": comment.get('type'),
                                        "diseaseId": comment.get('diseaseId'),
                                        "acronym": comment.get('acronym'),
                                        "dbReference": comment.get('dbReference'),
                                        "description": {"value": comment.get('description', {}).get('value', '')}
                                    }
                                    disease_comments.append(disease_info)
                                elif comment_type == 'POLYMORPHISM':
                                    polymorphism_comments.extend(text_list)
                                elif comment_type == 'MISCELLANEOUS':
                                    miscellaneous_comments.extend(text_list)
                                elif comment_type == 'SIMILARITY':
                                    similarity_comments.extend(text_list)
                                elif comment_type == 'CAUTION':
                                    caution_comments.extend(text_list)

                            output = {
                                "id": response_protein.get("id"),
                                "accession": response_protein.get("accession"),
                                "secondaryAccession": response_protein.get("secondaryAccession"),
                                "protein": response_protein.get("protein"),
                                "alternativeName": response_protein.get("alternativeName"),
                                "gene": response_protein.get("gene"),
                                "comments": {
                                    "FUNCTION": function_comments,
                                    "SUBUNIT": subunit_comments,
                                    "INTERACTION": interaction_comments,
                                    "TISSUE_SPECIFICITY": tissue_comments,
                                    "PTM_SPECIFICITY": ptm_comments,
                                    "MASS_SPECTROMETRY": mass_comments,
                                    "DISEASE": disease_comments,
                                    "POLYMORPHISM": polymorphism_comments,
                                    "MISCELLANEOUS": miscellaneous_comments,
                                    "SIMILARITY": similarity_comments,
                                    "CAUTION": caution_comments,
                                    "sequence": response_protein.get("sequence", {}).get("sequence", "")
                                }
                            }

                            return json.dumps(output, indent=4)

                        else:
                            print(f"Error: {response_protein.status_code}")
                    else:
                        print(f"No matching protein found for '{term}'")
                else:
                    print("No results found in Uniprot.")
            
            else:
                print(f"Error: Unable to fetch data from Uniprot.")

            return None

def gene_information_extractor(search_term):
            gene_id = None
            base_url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
            search_url = base_url + 'esearch.fcgi'
            summary_url = base_url + 'esummary.fcgi'
            base_url_gene = "https://api.ncbi.nlm.nih.gov/datasets/v2alpha/gene/symbol/"
            headers = {
                "accept": "application/json",
                "api-key": "b27855b4a18aa2aa178fc22083d0c07ee308"
            }

            # Split the search_term by comma and strip any extra spaces
            search_terms = [term.strip() for term in search_term.split(',')]
            gene_information_dict = {}

            def is_numeric(s):
                return s.isdigit()

            # When there's only one search term
            if len(search_terms) == 1:
                if is_numeric(search_term):
                    gene_id = search_term
                else:
                    url = f"{base_url_gene}{search_term}/taxon/9606"
                    response = fetch_data(url, headers=headers)
                    if response and 'reports' in response:  # Directly use the dictionary returned by fetch_data
                        gene_id = response['reports'][0]['gene']['gene_id']

                search_params = {
                    'db': 'gene',
                    'term': gene_id,
                    'retmode': 'json'
                }
                search_response = fetch_data(search_url, params=search_params)
                if search_response:
                    search_results = search_response  # Already a dictionary, no need to call .json()
                    if 'esearchresult' in search_results and 'idlist' in search_results['esearchresult']:
                        gene_ids = search_results['esearchresult']['idlist']
                        summary_params = {
                            'db': 'gene',
                            'id': ','.join(gene_ids),
                            'retmode': 'json'
                        }
                        summary_response = fetch_data(summary_url, params=summary_params)
                        if summary_response:
                            summary_results = summary_response  # Already a dictionary, no need to call .json()
                            gene_information_dict[search_term] = summary_results

                if not gene_information_dict:
                    server = "https://grch37.rest.ensembl.org"
                    ext = f"/lookup/symbol/homo_sapiens/{search_term}?"
                    r = fetch_data(server + ext, headers={"Content-Type": "application/json"})
                    if r:  # Directly use the dictionary returned by fetch_data
                        gene_information_dict[search_term] = repr(r)

                if not gene_information_dict:
                    return "Not Found"
                else:
                    return json.dumps(gene_information_dict, indent=4)

            # When there are multiple search terms
            else:
                for term in search_terms:
                    if is_numeric(term):
                        gene_id = term
                    else:
                        url = f"{base_url_gene}{term}/taxon/9606"
                        response = fetch_data(url, headers=headers)
                        if response and 'reports' in response:  # Directly use the dictionary returned by fetch_data
                            gene_id = response['reports'][0]['gene']['gene_id']

                    search_params = {
                        'db': 'gene',
                        'term': gene_id,
                        'retmode': 'json'
                    }
                    search_response = fetch_data(search_url, params=search_params)
                    if search_response:
                        search_results = search_response  # Already a dictionary, no need to call .json()
                        if 'esearchresult' in search_results and 'idlist' in search_results['esearchresult']:
                            gene_ids = search_results['esearchresult']['idlist']
                            summary_params = {
                                'db': 'gene',
                                'id': ','.join(gene_ids),
                                'retmode': 'json'
                            }
                            summary_response = fetch_data(summary_url, params=summary_params)
                            if summary_response:
                                summary_results = summary_response  # Already a dictionary, no need to call .json()
                                gene_data = summary_results['result'][gene_id]

                                # Prepare gene information
                                extracted_info = {
                                    'name': gene_data['name'],
                                    'gene_id': gene_data['uid'],
                                    'description': gene_data['description'],
                                    'chromosome': gene_data['chromosome'],
                                    'maplocation': gene_data['maplocation'],
                                    'otheraliases': gene_data['otheraliases'],
                                    'otherdesignations': gene_data['otherdesignations'],
                                    'nomenclaturesymbol': gene_data['nomenclaturesymbol'],
                                    'nomenclaturename': gene_data['nomenclaturename'],
                                    'summary': gene_data['summary']
                                }
                                gene_information_dict[term] = extracted_info
                    if not gene_information_dict:
                        server = "https://grch37.rest.ensembl.org"
                        ext = f"/lookup/symbol/homo_sapiens/{term}?"
                        r = fetch_data(server + ext, headers={"Content-Type": "application/json"})
                        if r:  # Directly use the dictionary returned by fetch_data
                            gene_information_dict[term] = repr(r)

                values_only = [json.dumps(value, indent=4) for value in gene_information_dict.values()]
                result_string = '\n'.join(values_only)
                if not values_only:
                    return "Not Found"
                else:
                    print(result_string)
                    return result_string



        
def disease_information_extractor(disease_name):
        def get_bioontology_info(disease_name):
            api_key = 'bd2f8372-cac9-4ed6-8f56-7e24b5c87e85'
            headers = {'Authorization': f'apikey token={api_key}'}
            url = f'https://data.bioontology.org/search?q={disease_name}'
            combined_info = {
                'prefLabel': '',
                'synonym': set(),
                'definition': set()
            }
            response = fetch_data(url, headers=headers)
            if response:  # Directly use the dictionary returned by fetch_data
                collection = response.get('collection', [])
                for item in collection:
                    pref_label = item.get('prefLabel', '').lower()
                    synonyms = [syn.lower() for syn in item.get('synonym', [])]
                    definitions = [defn for defn in item.get('definition', [])]
                    if disease_name.lower() == pref_label or disease_name.lower() in synonyms:
                        if not combined_info['prefLabel']:
                            combined_info['prefLabel'] = pref_label
                        combined_info['synonym'].update(synonyms)
                        combined_info['definition'].update(definitions)

                combined_info['synonym'] = list(combined_info['synonym'])
                combined_info['definition'] = list(combined_info['definition'])
                if not combined_info['prefLabel'] and not combined_info['synonym'] and not combined_info['definition']:
                    return None
                else:
                    return combined_info
            return None

        def get_orpha_info(disease_name):
            orpha_url = f"https://api.orphadata.com/rd-cross-referencing/orphacodes/names/{quote(disease_name)}?lang=en"
            response = fetch_data(orpha_url)
            if response:  # Directly use the dictionary returned by fetch_data
                if "data" in response and "results" in response["data"]:
                    data = response["data"]["results"]
                    summary_info = data.get("SummaryInformation", [])
                    if summary_info:
                        filtered_result = {
                            "ORPHAcode": data.get("ORPHAcode", ""),
                            "preferredTerm": data.get("Preferred term", ""),
                            "summary": summary_info[0].get("Definition", ""),
                            "Synonym": data.get("Synonym", [])
                        }
                        return filtered_result
            return None

        def get_hpo_info(disease_name):
            hpo_url = f"https://ontology.jax.org/api/network/search/disease?q={quote(disease_name)}&page=0&limit=10"
            response = fetch_data(hpo_url)
            if response:  # Directly use the dictionary returned by fetch_data
                if response["results"]:
                    data = response["results"][0]
                    disease_result = {
                        "id": data.get("id", ""),
                        "name": data.get("name", ""),
                        "mondoId": data.get("mondoId", ""),
                        "description": data.get("description", [])
                    }
                    return disease_result
            return None
        # Collecting results from each source
        #def get_combined_disease_info(disease_name):
        bioontology_info = get_bioontology_info(disease_name)
        orpha_info = get_orpha_info(disease_name)
        hpo_info = get_hpo_info(disease_name)

        combined_result = {}
        if bioontology_info:
            combined_result['Bioontology'] = bioontology_info
        if orpha_info:
            combined_result['Orpha'] = orpha_info
        if hpo_info:
            combined_result['HPO'] = hpo_info

        if not combined_result:
            return "Not Found"
        return combined_result

def disease_gene_extractor(disease_term):
            disease_id = None
            annotation_result = []

            def is_disease_id(s):
                """Check if the string is a disease ID (OMIM or ORPHA)."""
                return (s.startswith("OMIM:") and s[5:].isdigit()) or (s.startswith("ORPHA:") and s[6:].isdigit())

            # 判断输入的是表型ID还是名称
            if disease_term.isdigit():
                disease_id = f"OMIM:{disease_term}"
                url_annotation = f"https://ontology.jax.org/api/network/annotation/{quote(disease_id)}"
                # 发送请求
                response = fetch_data(url_annotation)
                if response:
                    annotation_result = response.get('genes', [])
                    return annotation_result
                else:
                    disease_id = f"ORPHA:{disease_term}"
                    url_annotation = f"https://ontology.jax.org/api/network/annotation/{quote(disease_id)}"
                    # 发送请求
                    response = fetch_data(url_annotation)
                    if response:
                        annotation_result = response.get('genes', [])
                        return annotation_result
            else:
                if is_disease_id(disease_term):
                    disease_id = disease_term
                else:
                    url_name = f"https://ontology.jax.org/api/network/search/disease?q={quote(disease_term)}&page=0&limit=10"
                    response = fetch_data(url_name)
                    if response:
                        if 'results' in response:
                            if response['results']:
                                disease_name = response['results'][0]['name']
                                if disease_name.lower() == disease_term.lower():
                                    disease_id = response['results'][0]['id']
                                else:
                                    results_disease = []
                                    for item in response['results']:
                                        disease_id1 = item["id"]
                                        url = f"https://ontology.jax.org/api/network/annotation/{disease_id1}"
                                        response = fetch_data(url)
                                        if response:
                                            gene_result = response.get('genes', [])
                                            annotation_result.append(gene_result)

                if disease_id is not None:
                    url_annotation = f"https://ontology.jax.org/api/network/annotation/{quote(disease_id)}"
                    # 发送请求
                    response = fetch_data(url_annotation)
                    if response:
                        annotation_result = response.get('genes', [])
                        if annotation_result:
                            return annotation_result

                if disease_id is None or not annotation_result:
                    base_url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
                    search_url = base_url + 'esearch.fcgi'
                    summary_url = base_url + 'esummary.fcgi'
                    # Step 1: Perform an esearch to retrieve gene IDs
                    search_params = {
                        'db': 'omim',
                        'term': disease_term,
                        'retmode': 'json'
                    }
                    search_response = fetch_data(search_url, params=search_params)
                    if search_response:
                        if 'esearchresult' in search_response and 'idlist' in search_response['esearchresult']:
                            gene_ids = search_response['esearchresult']['idlist']
                        # Step 2: Perform esummary to get summaries of the retrieved gene IDs
                        summary_params = {
                            'db': 'omim',
                            'id': ','.join(gene_ids),
                            'retmode': 'json'
                        }
                        summary_response = fetch_data(summary_url, params=summary_params)
                        if summary_response:
                            if 'result' in summary_response and 'uids' in summary_response['result']:
                                uids = summary_response['result']['uids']
                                relevant_uids = []
                                # Iterate through each uid and check the oid
                                for uid in uids:
                                    if 'oid' in summary_response['result'][uid]:
                                        oid = summary_response['result'][uid]['oid']
                                        if oid.startswith('*'):
                                            relevant_uids.append(uid)
                                # Iterate through each relevant uid to extract the abbreviation
                                for uid in relevant_uids:
                                    title = summary_response['result'][uid]['title']
                                    # Find the part after the last semicolon
                                    parts = title.split(';')
                                    if len(parts) > 1:
                                        annotation = parts[-1].strip()
                                        annotation_result.append(annotation)
                                return annotation_result
                    return "Not Found"

def snp_information_extractor(snp_term):
            base_url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
            search_url = base_url + 'esearch.fcgi'
            #summary_url = base_url + 'esummary.fcgi'
            efetch_url = base_url + 'efetch.fcgi'
            search_params = {
                'db': 'snp',
                'term': snp_term,
                'retmode': 'json'
            }
            
            search_response = fetch_data(search_url, params=search_params)
            if not search_response:
                return "Request failed or no results found"
            
            if 'esearchresult' in search_response and 'idlist' in search_response['esearchresult']:
                snp_ids = search_response['esearchresult']['idlist']
            else:
                print(f"No results found for '{snp_term}'.")
                return None
            
            efetch_params = {
                'db': 'snp',
                'id': ','.join(snp_ids),
                'rettype':'json',
                'retmode':'text'
            }
            efetch_response = fetch_data(efetch_url, params=efetch_params)
            if not efetch_response:
                print("Failed to retrieve SNP efetch information.")
                return None

            
            efetch_results = efetch_response
            return efetch_results


tools = [
    {
        "type": "function",
        "function": {
            "name": "phenotypes_info_extractor",
            "description": "Use this tool to extract information from a given symptom/Phenotypes name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "phenotype_term": {
                        "type": "string",
                        "description": "The name or ID of the phenotype, e.g., 'HP:0004322' or 'Muscle weakness'"
                    }
                },
                "required": ["phenotype_term"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "phenotypes_disease_extractor",
            "description": "Use this tool to extract diseases associated with the given phenotypes/symptom name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "phenotype_term": {
                        "type": "string",
                        "description": "The name or ID of the phenotype, e.g., 'HP:0004322' or 'Muscle weakness'"
                    }
                },
                "required": ["phenotype_term"]
            }
        }
    },
    {"type": "function", "function": {
        "name": "phenotypes_gene_extractor",
        "description": "Use this tool to extract genes associated with a given phenotypes/symptom name.",
        "parameters": {"type": "object", "properties": {"phenotype_term": {"type": "string", "description": "The phenotype name or ID."}}, "required": ["phenotype_term"]}
    }},
    {"type": "function", "function": {
        "name": "phenotypes_parents_extractor",
        "description": "Use this tool to extract parents from a given symptom/Phenotypes name",
        "parameters": {"type": "object", "properties": {"phenotype_term": {"type": "string", "description": "The phenotype name or ID."}}, "required": ["phenotype_term"]}
    }},
    {"type": "function", "function": {
        "name": "phenotypes_children_extractor",
        "description": "Use this tool to extract symptom/Phenotypes children from a given symptom/Phenotypes name.",
        "parameters": {"type": "object", "properties": {"phenotype_term": {"type": "string", "description": "The phenotype name or ID."}}, "required": ["phenotype_term"]}
    }},
    {"type": "function", "function": {
        "name": "phenotypes_descendants_extractor",
        "description": "Use this tool to extract symptom/Phenotypes descendants from a given symptom/Phenotypes name.",
        "parameters": {"type": "object", "properties": {"phenotype_term": {"type": "string", "description": "The phenotype name or ID."}}, "required": ["phenotype_term"]}
    }},
    {
        "type": "function",
        "function": {
            "name": "gene_phenotypes_extractor",
            "description": "Use this tool to extract phenotypes associated with a given gene.",
            "parameters": {
                "type": "object",
                "properties": {
                    "gene_term": {
                        "type": "string",
                        "description": "The name or ID of the gene, e.g., 'NCBIGene:1017' or 'BRCA1'"
                    }
                },
                "required": ["gene_term"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gene_diseases_extractor",
            "description": "Use this tool to extract diseases associated with a given gene.",
            "parameters": {
                "type": "object",
                "properties": {
                    "gene_term": {
                        "type": "string",
                        "description": "The name or ID of the gene, e.g., 'NCBIGene:1017' or 'BRCA1'"
                    }
                },
                "required": ["gene_term"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "disease_phenotypes_extractor",
            "description": "Use this tool to extract phenotypes associated with a given disease.",
            "parameters": {
                "type": "object",
                "properties": {
                    "disease_term": {
                        "type": "string",
                        "description": "The name or ID of the disease, e.g., 'OMIM:101600' or 'Cystic Fibrosis'"
                    }
                },
                "required": ["disease_term"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "protein_information_extractor",
            "description": "Use this tool to extract protein information from UniProt API.",
            "parameters": {
                "type": "object",
                "properties": {
                    "term": {
                        "type": "string",
                        "description": "The protein name or UniProt ID, e.g., 'P53' or 'P04637'."
                    }
                },
                "required": ["term"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gene_information_extractor",
            "description": "Use this tool to fetch gene information with a given gene name or ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "search_term": {
                        "type": "string",
                        "description": "The gene name or ID, e.g., 'BRCA1' or '672'."
                    }
                },
                "required": ["search_term"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "disease_information_extractor",
            "description": "Use this tool to fetch disease information with a given disease name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "disease_name": {
                        "type": "string",
                        "description": "The disease name, e.g., 'Alzheimer's disease' or 'Diabetes Mellitus'."
                    }
                },
                "required": ["disease_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "disease_gene_extractor",
            "description": "Use this tool to extract genes associated with a given disease.",
            "parameters": {
                "type": "object",
                "properties": {
                    "disease_term": {
                        "type": "string",
                        "description": "The disease name or ID, e.g., 'Diabetes' or 'OMIM:222100'."
                    }
                },
                "required": ["disease_term"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "snp_information_extractor",
            "description": "Use this tool to fetch SNP information using a given SNP ID or term.",
            "parameters": {
                "type": "object",
                "properties": {
                    "snp_term": {
                        "type": "string",
                        "description": "The SNP ID or search term, e.g., 'rs12345'."
                    }
                },
                "required": ["snp_term"]
            }
        }
    }
]


def ask_gpt(user_input):
    messages = [
        {"role": "user", "content": user_input}
    ]

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )

    response_message = response.choices[0].message

    if response_message.tool_calls:
        for tool_call in response_message.tool_calls:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)

            if function_name == "phenotypes_info_extractor":
                function_response = phenotypes_info_extractor(**arguments)
            elif function_name == "phenotypes_disease_extractor":
                function_response = phenotypes_disease_extractor(**arguments)
            elif function_name == "phenotypes_gene_extractor":
                function_response = phenotypes_gene_extractor(**arguments)
            elif function_name == "phenotypes_parents_extractor":
                function_response = phenotypes_parents_extractor(**arguments)
            elif function_name == "phenotypes_children_extractor":
                function_response = phenotypes_children_extractor(**arguments)
            elif function_name == "phenotypes_descendants_extractor":
                function_response = phenotypes_descendants_extractor(**arguments)
            elif function_name == "gene_phenotypes_extractor":
                function_response = gene_phenotypes_extractor(**arguments)
            elif function_name == "gene_diseases_extractor":
                function_response = gene_diseases_extractor(**arguments)
            elif function_name == "disease_phenotypes_extractor":
                function_response = disease_phenotypes_extractor(**arguments)
            elif function_name == "protein_information_extractor":
                function_response = protein_information_extractor(**arguments)
            elif function_name == "gene_information_extractor":
                function_response = gene_information_extractor(**arguments)
            elif function_name == "disease_information_extractor":
                function_response = disease_information_extractor(**arguments)
            elif function_name == "disease_gene_extractor":
                function_response = disease_gene_extractor(**arguments)
            elif function_name == "snp_information_extractor":
                function_response = snp_information_extractor(**arguments)
            else:
                function_response = "Invalid function call"

            messages.append(response_message)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": function_name,
                "content": json.dumps(function_response)
            })

            final_response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages
            )
            return final_response.choices[0].message.content

    return response_message.content


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate medical agent on a CSV file.")
    parser.add_argument('--input', type=str, required=True, help="Input CSV file path")
    parser.add_argument('--output', type=str, required=True, help="Output CSV file path")
    args = parser.parse_args()
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    evaluate_csv(args.input, args.output,ask_gpt)