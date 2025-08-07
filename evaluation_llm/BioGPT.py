import os
import pandas as pd
from transformers import pipeline

pipe_biogpt = pipeline("text-generation", model="microsoft/BioGPT-Large-PubMedQA")

def inference(question):
    return pipe_biogpt(question, max_length=500)[0]["generated_text"]

def evaluate_csv(input_csv, output_csv):
    df = pd.read_csv(input_csv)
    df.columns = ['question', 'Goldstandard']
    df['BioGPT_answer'] = df['question'].apply(inference)
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    df.to_csv(output_csv, index=False)
    print(f"Evaluation results saved to: {output_csv}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Batch evaluation for BioGPT using CSV")
    parser.add_argument('--input', type=str, required=True, help="Input CSV file path")
    parser.add_argument('--output', type=str, required=True, help="Output CSV file path")
    args = parser.parse_args()
    evaluate_csv(args.input, args.output)