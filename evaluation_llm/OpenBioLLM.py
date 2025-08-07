import os
import csv
import argparse
from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer


parser = argparse.ArgumentParser()
parser.add_argument("--input", required=True, help="Path to the input CSV file")
parser.add_argument("--output", required=True, help="Path to the output CSV file")
args = parser.parse_args()
input_csv = args.input
output_csv = args.output

cache_dir = "/app/evaluation_llm"
os.environ["HF_HOME"] = cache_dir
os.makedirs(cache_dir, exist_ok=True)

model = AutoModelForCausalLM.from_pretrained("aaditya/OpenBioLLM-Llama3-8B", cache_dir=cache_dir)
tokenizer = AutoTokenizer.from_pretrained("aaditya/OpenBioLLM-Llama3-8B", cache_dir=cache_dir)

text_gen_pipeline = pipeline("text-generation", model=model, tokenizer=tokenizer)

rows = []
with open(input_csv, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        question = row["question"]
        goldstandard = row["Goldstandard"]

        prompt = tokenizer.decode(
            tokenizer.encode(f"Question: {question}\nAnswer:", add_special_tokens=False),
            skip_special_tokens=True
        )

        outputs = text_gen_pipeline(
            prompt,
            max_new_tokens=256,
            do_sample=True,
            temperature=0.6,
            top_p=0.9
        )
        model_answer = outputs[0]["generated_text"][len(prompt):].strip()

        rows.append({
            "question": question,
            "Goldstandard": goldstandard,
            "ModelAnswer": model_answer
        })

with open(output_csv, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["question", "Goldstandard", "ModelAnswer"])
    writer.writeheader()
    writer.writerows(rows)