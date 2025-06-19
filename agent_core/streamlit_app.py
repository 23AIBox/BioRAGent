import streamlit as st
from agent_main import main, guide_agent


def clear_chat():
    st.session_state.messages.clear()


if "messages" not in st.session_state:
    st.session_state.messages = []

st.markdown("<style>.block-container {padding-top: 1rem;}</style>", unsafe_allow_html=True)

if "greeting_shown" not in st.session_state:
    st.session_state.greeting_shown = True
    with st.container():
        st.markdown("<br><br><br>", unsafe_allow_html=True)  
        st.markdown("## Welcome to BioRAGent!")
        st.markdown("""
 I’m BioRAGent, here to assist you with biomedical queries on genetics, diseases, phenotypes, and more. You can ask questions like:
- What are genes related to Brody myopathy? 
- List chromosome locations of the genes related to Palate neoplasm. 
- What is asthma?  

Please note that I am an assistant designed to help retrieve information from biomedical databases. The information provided is not intended for clinical diagnosis, medical decision-making, or any other healthcare applications. If you experience any symptoms or feel unwell, please seek medical attention promptly.
""")

st.markdown("<br><br>", unsafe_allow_html=True)

chat_container = st.container()

user_avatar_url = "user.png"
assistant_avatar_url = "assistant.png"

with chat_container:
    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar=user_avatar_url if message["role"] == "user" else assistant_avatar_url):
            st.markdown(message["content"])

question = st.chat_input("Ask a biomedical question:")
if question:
    with st.chat_message("user", avatar=user_avatar_url):
        st.markdown(question)
    st.session_state.messages.append({"role": "user", "content": question})

    with st.spinner('Processing your query...'):
        agent_answer = main(question)

    with st.chat_message("assistant", avatar=assistant_avatar_url):
        st.markdown(agent_answer)

    st.session_state.messages.append({"role": "assistant", "content": agent_answer})

with st.sidebar:
    st.title("Agent Settings")
    st.sidebar.button("Clear chat history", on_click=clear_chat)