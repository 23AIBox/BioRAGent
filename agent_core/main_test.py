import streamlit as st
import asyncio
import logging
import re
import csv
# 从 initialize_agents.py 直接导入已初始化的对象
from initialize_agents import agent_data, agent_guide, agent_val
from agent_guide import process_input
import streamlit as st

# 设置页面配置
st.set_page_config(
    page_title="BioRAGent",
    page_icon="💬",
)
class GuideAgent:
    name: str = "GuideAgent"
    def is_medical_query(self, question: str) -> bool:       
        input_text = f" Please determine whether the following query is related to medicine: '{question}',only answer 'Yes' or 'No'"
        result =process_input("user" ,input_text)
        response = result.get('output', None)
        # 使用 strip() 清除多余空格并转换为小写
        #ans=process_evaluation_output(response)
        response = response.strip().lower()
        return "yes" in response.lower()
    
    def process_evaluation_output(self,output):
        output = output.lower()
        ans = re.findall(r'yes|no', output)
        if len(ans) == 0:
            ans = "yes"
        else:
            ans = ans[0]
        return ans
    
    def handle_query(self, query: str):
        if self.is_medical_query(query):
            input_text=f" provide the query instruction for this sentence '{query}' ,without giving a specific answer."
            instruction= process_input("instruction",input_text)
            instruction_output=instruction.get('output', None)

            MAX_ITERATIONS = 2
            num_try = 0
            hasno_flag = True
            response = DatabaseAgent.query_database(instruction_output)

            while num_try < MAX_ITERATIONS and hasno_flag:
                num_try += 1
                hasno_flag = False
                second_response=f"Please evaluate:Retrieved answer to the query '{query}' is '{response}',only answer 'Yes' or 'No'"
                evaluation = process_input("evaluation", second_response)
                evaluation_output = evaluation.get('output', None)
                final_evaluation_result = self.process_evaluation_output(evaluation_output)

                if final_evaluation_result == "no":
                    input_text2=f"Based on {response}, refine the query instruction to help retrieve a complete and accurate answer."
                    refined_query = process_input("refinded", input_text2)
                    refined_query_output = refined_query.get('output', None)
                    response = DatabaseAgent.query_database(refined_query_output)
                    hasno_flag = True  # Continue iterating if we need more information

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
        response=agent_data.invoke({"input":query})            
        answer=response.get('output', None)
        return answer
        #return f"Retrieved answer to the query '{query}': '{answer}'"
        #return f"If '{answer}' addresses '{query}', output {answer}; otherwise, please supplement the existing answer with relevant information from your knowledge base"
        #return f"Evaluate whether the '{answer}' addresses the '{query}'. If it does, output {answer}; if it does not, please supplement the existing answer with the correct answer to the query from your knowledge base at the end of {answer}."


class ValidationAgent:
    name: str = "ValidationAgent"
    @staticmethod
    def validate_answer(query: str):
            text = f"{query}. Please provide the most suitable final answer based on the given answer and question."
            response=agent_val.invoke({"input":query})         
            final_answer=response.get('output', None)    
            return final_answer

guide_agent = GuideAgent()
def main(user_question: str): 
    return guide_agent.handle_query(user_question)

def clear_chat():
    st.session_state.messages.clear()
    
    # 重新初始化 agents
    global agent_guide, agent_data, agent_val
    from initialize_agents import agent_data, agent_guide, agent_val


def evaluate_medical_agent(dataset_file, output_file):
    """
    评估医学代理在给定数据集上的性能，并输出每个问题的评估分数

    参数:
    - agent (MedicalAgent): 已经训练好的医学代理对象
    - dataset_file (str): 包含数据集的 CSV 文件路径
    """
    encodings_to_try = ['utf-8', 'latin-1', 'ISO-8859-1', 'Windows-1252']

    for encoding in encodings_to_try:
        try:
            # Open input and output CSV files
            with open(dataset_file, 'r', encoding=encoding) as csvfile, \
                 open(output_file, 'w', newline='', encoding="utf-8") as outputcsvfile:
                reader = csv.reader(csvfile)
                writer = csv.writer(outputcsvfile)
                writer.writerow(['Question', 'Standard Answer', 'Agent Answer'])

                # 遍历每一行
                for row in reader:
                    print("hi")
                    print(f"Row: {row}")

                    # 清除每行的空白字符并删除空字符串
                    row = [item.strip() for item in row if item.strip()]  # 去除空白字符和空列
                    # 每一行应该是一个列表，包含两个元素：问题和标准答案
                    if len(row) == 2:  # 确保每一行有两个元素
                        print("hello")
                        question = row[0].strip()  # 第一个元素为问题
                        standard_answer = row[1].strip()  # 第二个元素为标准答案
                        print(f"问题: {question}")
                        print(f"标准答案: {standard_answer}")
                        #agent_output1=agent_guide.invoke({"input": question})
                        #agent_output2=agent_output1.get('output', None)
                        answer = main(question)  # Get answer from the Guide Agent

                        # 计算分数           
                        writer.writerow([question, standard_answer, answer])

                        # 输出每个问题的评估分数
                        print(f"Question: {question}")
                        print(f"Agent Answer: {answer}")
                        print(f"Standard Answer: {standard_answer}")
                        print("---")
            break  # Successfully processed the file, exit the loop
        except UnicodeDecodeError:
            print(f"Failed to decode using {encoding} encoding. Trying next encoding...")
            continue  # If decoding fails, continue to the next encoding
        except Exception as e:
            print(f"An error occurred: {e}")
            break  # Exit loop on other types of errors
                        



# 测试评估代码
#if __name__ == "__main__":
    # 初始化医学代理
    #medical_agent = agent_data

    # 准备数据集文件路径
    #dataset_file = 'D:/source/gpt4_test.csv'
    #output_file='D:/source/result_gpt4_test.csv'
    # 进行评估并输出每个问题的评估分数
    
    #evaluate_medical_agent(dataset_file,output_file)
    #print(main('What is the function of the gene BRCA1?'))
#if __name__ == "__main__":
#    print(main("LList chromosome locations of the genes related to Hot flashes. "))

# import streamlit as st

import streamlit as st

# 初始化 session_state 变量
if "messages" not in st.session_state:
    st.session_state.messages = []

# 创建上方的占位符，使聊天框尽量靠上
st.markdown("<style>.block-container {padding-top: 1rem;}</style>", unsafe_allow_html=True)

# 显示欢迎消息，并使其稍微下移
if "greeting_shown" not in st.session_state:
    st.session_state.greeting_shown = True
    with st.container():
        st.markdown("<br><br><br>", unsafe_allow_html=True)  # 让欢迎消息稍微下移
        st.markdown("## Welcome to BioRAGent!")
        st.markdown("""
 I’m BioRAGent, here to assist you with biomedical queries on genetics, diseases, phenotypes, and more. You can ask questions like:
- What are genes related to Brody myopathy? 
- List chromosome locations of the genes related to Palate neoplasm. 
- What is asthma?  

Please note that I am an assistant designed to help retrieve information from biomedical databases. The information provided is not intended for clinical diagnosis, medical decision-making, or any other healthcare applications. If you experience any symptoms or feel unwell, please seek medical attention promptly.
""")


st.markdown("<br><br>",unsafe_allow_html=True)
# **聊天窗口（上移）**
chat_container = st.container()

# 设置自定义头像
user_avatar_url = "user.png"
assistant_avatar_url = "assistant.png"


with chat_container:
    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar= user_avatar_url if message["role"] == "user" else assistant_avatar_url):
            st.markdown(message["content"])

# **输入框紧贴聊天窗口**
question = st.chat_input("Ask a biomedical question:")
if question:
    with st.chat_message("user", avatar=user_avatar_url):
        st.markdown(question)
    st.session_state.messages.append({"role": "user", "content": question})

    with st.spinner('Processing your query...'):
        agent_answer = main(question)  # 替换为你的 `main(question)`

    with st.chat_message("assistant", avatar=assistant_avatar_url):
        st.markdown(agent_answer)

    st.session_state.messages.append({"role": "assistant", "content": agent_answer})

# **侧边栏设置**
with st.sidebar:
    st.title("Agent Settings")
    st.sidebar.button("Clear chat history", on_click=clear_chat)