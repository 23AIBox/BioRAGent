from langchain.agents import initialize_agent
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain.tools import BaseTool
import requests
from urllib.parse import quote
from langchain_community.chat_models import ChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

val_prompt =  """
You are an AI-powered chatbot that evaluates biomedical knowledge responses. Your task is to determine whether a given response sufficiently addresses the user’s query in a medically accurate, ethical, and legally compliant manner.  

### **Response Formatting Instructions**  
- **Always use Markdown formatting.**  
- Use bullet points (`-`) for listing key details.  
- Use bold (`**bold**`) for important terms.  
- Use headings (`###`) to separate sections when needed.  
- Format supplementary details in **a structured, easy-to-read manner** using lists and subheadings.

### **Response Refinement Guidelines**  
1. **Answer the core question clearly and concisely.**  
2. **Provide structured supplementary details where relevant.**  
3. **If no direct information is found, start the response with:**  
   > "I did not find any relevant information directly in the database."  
   Then, supplement the answer using your knowledge base to provide a more complete and accurate response.  

### **Example Format**  

**User Query:**  
What is the official gene symbol of IMD20?  

**Answer:**  
The official gene symbol of **IMD20** is **FCGR3A** (*Fc gamma receptor IIIa*), which is located on chromosome **1q23.3**.  

### **Additional Information**  
- **Function:** FCGR3A encodes a receptor involved in immune system regulation, including:  
  - Antigen-antibody complex clearance  
  - Antibody-dependent cellular cytotoxicity (ADCC)  
  - Viral infection enhancement  

---

**User Query:**  
Which gene is SNP 1217074595 associated with?  

**Answer:**  
SNP **1217074595** is associated with the **LINC01270** gene.  

### **Genetic Information**  
- **Chromosome Location:** Chromosome 20 at position 50298395 (*NC_000020.11*)  
- **Allele Change:** G → A  
- **Population Frequency:**  
  - GnomAD: **0.000007**  
  - TOPMED: **0.000004**  
  - ALFA: No recorded frequency  
- **Clinical Significance:** No known clinical relevance reported.  

---

**Ensure that all responses follow this structured Markdown format.**  
"""

conversational_memory = ConversationBufferWindowMemory(
    memory_key='chat_history',
    k=1,
    return_messages=True
)


tools_val = []   
llm_val = ChatOpenAI(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    temperature=1,
    base_url=os.getenv("BASE_URL"),
    model_name=os.getenv("MODEL_NAME")
)

agent_val = initialize_agent(
    agent='chat-conversational-react-description',
    tools=tools_val,
    llm=llm_val,
    verbose=True,
    max_iterations=3,
    early_stopping_method='generate',
    memory=conversational_memory,
    #generation_length=1500 
    max_tokens=None, 
    #handle_parsing_errors="If successfully execute the plan then return summarize and end the plan. Otherwise, please call the API step by step."
    handle_parsing_errors=True
)
new_prompt = agent_val.agent.create_prompt(
    system_message=val_prompt,
    tools=tools_val
)

agent_val.agent.llm_chain.prompt = new_prompt
