import os
import sys
from dotenv import load_dotenv
import argparse
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from evaluation_llm.evaluator import evaluate_csv  
from agent_core.agent_data import agent_data

load_dotenv()


def query_database(query: str):
    response = agent_data.invoke({"input": query})
    answer = response.get('output', None)
    return answer

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate agent on a CSV file.")
    parser.add_argument('--input', type=str, required=True, help="Input CSV file path")
    parser.add_argument('--output', type=str, required=True, help="Output CSV file path")
    args = parser.parse_args()
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    evaluate_csv(args.input, args.output, query_database)