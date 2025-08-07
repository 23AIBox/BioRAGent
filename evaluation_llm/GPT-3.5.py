from openai import OpenAI
import os
from dotenv import load_dotenv
import httpx
import argparse
from evaluator import evaluate_csv  

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("BASE_URL")

client = OpenAI(
    base_url=base_url,
    api_key=api_key,
    http_client=httpx.Client(
        base_url=base_url,
        follow_redirects=True,
    ),
)

def gpt35_model_answer(question: str) -> str:
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo-16k-0613",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": question}
        ]
    )
    return completion.choices[0].message.content.strip()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate questions using GPT-3.5-turbo-16k-0613 model.")
    parser.add_argument('--input', required=True, help="Input CSV file path")
    parser.add_argument('--output', required=True, help="Output CSV file path")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    evaluate_csv(args.input, args.output, gpt35_model_answer)