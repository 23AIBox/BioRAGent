import os
import re
import time
import csv
import json
import argparse
import urllib.request
from openai import OpenAI
from dotenv import load_dotenv


load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("BASE_URL")

def call_api(url):
    time.sleep(1)
    url = url.replace(' ', '+')
    print(url)

    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as response:
        call = response.read()
    return call

def get_prompt_header(mask):
    url_1 = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=gene&retmax=5&retmode=json&sort=relevance&term=LMP10'
    call_1 = call_api(url_1)

    url_2 = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=gene&retmax=5&retmode=json&id=19171,5699,8138'
    call_2 = call_api(url_2)

    url_3 = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=snp&retmax=10&retmode=json&id=1217074595'
    call_3 = call_api(url_3)

    url_4 = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=omim&retmax=20&retmode=json&sort=relevance&term=Meesmann+corneal+dystrophy'
    call_4 = call_api(url_4)

    url_5 = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=omim&retmax=20&retmode=json&id=618767,601687,300778,148043,122100'
    call_5 = call_api(url_5)

    url_6 = 'https://blast.ncbi.nlm.nih.gov/blast/Blast.cgi?CMD=Put&PROGRAM=blastn&MEGABLAST=on&DATABASE=nt&FORMAT_TYPE=XML&QUERY=ATTCTGCCTTTAGTAATTTGATGACAGAGACTTCTTGGGAACCACAGCCAGGGAGCCACCCTTTACTCCACCAACAGGTGGCTTATATCCAATCTGAGAAAGAAAGAAAAAAAAAAAAGTATTTCTCT&HITLIST_SIZE=5'
    call_6 = call_api(url_6)
    rid = re.search('RID = (.*)\n', call_6.decode('utf-8')).group(1)

    url_7 = f'https://blast.ncbi.nlm.nih.gov/blast/Blast.cgi?CMD=Get&FORMAT_TYPE=Text&RID={rid}'
    time.sleep(30)
    call_7 = call_api(url_7)

    prompt = 'Hello. Your task is to use NCBI Web APIs to answer genomic questions.\n'

    if mask[0]:
        prompt += 'You can call Eutils by: "[https://eutils.ncbi.nlm.nih.gov/entrez/eutils/{esearch|efetch|esummary}.fcgi?db={gene|snp|omim}&retmax={}&{term|id}={term|id}]".\n'
        prompt += 'esearch: input is a search term and output is database id(s).\n'
        prompt += 'efectch/esummary: input is database id(s) and output is full records or summaries that contain name, chromosome location, and other information.\n'
        prompt += 'Database: gene is for genes, snp is for SNPs, and omim is for genetic diseases.\n\n'

    if mask[1]:
        prompt += 'For DNA sequences, you can use BLAST by: "[https://blast.ncbi.nlm.nih.gov/blast/Blast.cgi?CMD={Put|Get}&PROGRAM=blastn&MEGABLAST=on&DATABASE=nt&FORMAT_TYPE={XML|Text}&QUERY={sequence}&HITLIST_SIZE={max_hit_size}]".\n'
        prompt += 'BLAST maps a specific DNA {sequence} to its chromosome location among different specices.\n'
        prompt += 'You need to first PUT the BLAST request and then GET the results using the RID returned by PUT.\n\n'

    if any(mask[2:]):
        prompt += 'Here are some examples:\n\n'

    if mask[2]:
        prompt += f'Question: What is the official gene symbol of LMP10?\n[{url_1}]->[{call_1}]\n[{url_2}]->[{call_2}]\nAnswer: PSMB10\n\n'

    if mask[3]:
        prompt += f'Question: Which gene is SNP rs1217074595 associated with?\n[{url_3}]->[{call_3}]\nAnswer: LINC01270\n\n'

    if mask[4]:
        prompt += f'Question: What are genes related to Meesmann corneal dystrophy?\n[{url_4}]->[{call_4}]\n[{url_5}]->[{call_5}]\nAnswer: KRT12, KRT3\n\n'

    if mask[5]:
        prompt += f'Question: Align the DNA sequence to the human genome: ATTCTGCCTTTAGTAATTTGATGACAGAGACTTCTTGGGAACCACAGCCAGGGAGCCACCCTTTACTCCACCAACAGGTGGCTTATATCCAATCTGAGAAAGAAAGAAAAAAAAAAAAGTATTTCTCT\n[{url_6}]->[{rid}]\n[{url_7}]->[{call_7}]\nAnswer: chr15:91950805-91950932\n\n'

    return prompt

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to input CSV file")
    parser.add_argument("--output", required=True, help="Path to output CSV file")
    args = parser.parse_args()

    str_mask = "111111"
    mask = [bool(int(x)) for x in str_mask]
    prompt_header = get_prompt_header(mask)

    client = OpenAI(
    base_url=base_url,
    api_key=api_key
    )


    output_rows = []

    with open(args.input, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            question = row["question"]
            answer = row.get("answer", "")
            prompt = prompt_header + f"Question: {question}\n"

            num_calls = 0
            while True:
                if len(prompt) > 36000:
                    prompt = prompt[-36000:]

                try:
                    time.sleep(10)
                    completion = client.chat.completions.create(
                        model="gpt-3.5-turbo-16k",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.0,
                        stop=["->", "\n\nQuestion"]
                    )
                    text = completion.choices[0].message.content
                    print(f"Model answer: {text}")
                except Exception as e:
                    print(f"Error: {e}")
                    text = "error"
                    break

                matches = re.findall(r'\[(https?://[^\[\]]+)\]', text)
                if matches:
                    url = matches[0]
                    if 'blast' in url and 'Get' in url:
                        time.sleep(30)
                    call = call_api(url)
                    if 'blast' in url and 'Put' in url:
                        rid = re.search('RID = (.*)\n', call.decode('utf-8')).group(1)
                        call = rid
                    if len(call) > 20000:
                        call = call[:20000]
                    prompt += f"{text}->[{call}]\n"
                else:
                    break

                num_calls += 1
                if num_calls >= 10:
                    text = "numError"
                    break

            output_rows.append({
                "question": question,
                "answer": answer,
                "model_answer": text
            })

    with open(args.output, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["question", "answer", "model_answer"])
        writer.writeheader()
        writer.writerows(output_rows)

if __name__ == "__main__":
    main()