from initialize_agents import agent_data, agent_guide, agent_val
from agent_guide import process_input
import re

class GuideAgent:
    name: str = "GuideAgent"

    def is_medical_query(self, question: str) -> bool:
        input_text = f" Please determine whether the following query is related to medicine: '{question}',only answer 'Yes' or 'No'"
        result = process_input("user", input_text)
        response = result.get('output', None)
        response = response.strip().lower()
        return "yes" in response.lower()

    def process_evaluation_output(self, output):
        output = output.lower()
        ans = re.findall(r'yes|no', output)
        return ans[0] if ans else "yes"

    def handle_query(self, query: str):
        if self.is_medical_query(query):
            input_text = f" provide the query instruction for this sentence '{query}' ,without giving a specific answer."
            instruction = process_input("instruction", input_text)
            instruction_output = instruction.get('output', None)

            MAX_ITERATIONS = 2
            num_try = 0
            hasno_flag = True
            response = DatabaseAgent.query_database(instruction_output)

            while num_try < MAX_ITERATIONS and hasno_flag:
                num_try += 1
                hasno_flag = False
                second_response = f"Please evaluate:Retrieved answer to the query '{query}' is '{response}',only answer 'Yes' or 'No'"
                evaluation = process_input("evaluation", second_response)
                evaluation_output = evaluation.get('output', None)
                final_evaluation_result = self.process_evaluation_output(evaluation_output)

                if final_evaluation_result == "no":
                    input_text2 = f"Based on {response}, refine the query instruction to help retrieve a complete and accurate answer."
                    refined_query = process_input("refinded", input_text2)
                    refined_query_output = refined_query.get('output', None)
                    response = DatabaseAgent.query_database(refined_query_output)
                    hasno_flag = True

            final_answer = f'The answer to "{query}" is {response}.'
            validation_response = ValidationAgent.validate_answer(final_answer)
        else:
            instruction = process_input("response", query)
            validation_response = instruction.get('output', None)

        return validation_response


class DatabaseAgent:
    name: str = "DatabaseAgent"
    @staticmethod
    def query_database(query: str):
        response = agent_data.invoke({"input": query})
        answer = response.get('output', None)
        return answer


class ValidationAgent:
    name: str = "ValidationAgent"
    @staticmethod
    def validate_answer(query: str):
        text = f"{query}. Please provide the most suitable final answer based on the given answer and question."
        response = agent_val.invoke({"input": query})
        final_answer = response.get('output', None)
        return final_answer

guide_agent = GuideAgent()

def main(user_question: str):
    return guide_agent.handle_query(user_question)