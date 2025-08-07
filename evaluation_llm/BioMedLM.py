import os
import pandas as pd
import torch
from transformers import GPT2LMHeadModel, GPT2Tokenizer

tokenizer = GPT2Tokenizer.from_pretrained("stanford-crfm/BioMedLM")
model = GPT2LMHeadModel.from_pretrained("stanford-crfm/BioMedLM")

def inference(question):
    input_ids = tokenizer.encode(question, return_tensors="pt")
    sample_output = model.generate(input_ids, do_sample=True, max_length=150, top_k=50)
    return tokenizer.decode(sample_output[0], skip_special_tokens=True)

def evaluate_csv(input_csv, output_csv):
    df = pd.read_csv(input_csv)
    if df.shape[1] < 2:
        raise ValueError("CSV file must have at least two columns (question and gold answer)")
    question_col = df.columns[0]
    gold_col = df.columns[1]
    df['BioMedLM_answer'] = df[question_col].apply(inference)
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    df.to_csv(output_csv, index=False)
    print(f"Evaluation results saved to: {output_csv}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Batch evaluation for BioMedLM using CSV")
    parser.add_argument('--input', type=str, required=True, help="Input CSV file path")
    parser.add_argument('--output', type=str, required=True, help="Output CSV file path")
    args = parser.parse_args()
    evaluate_csv(args.input, args.output)
