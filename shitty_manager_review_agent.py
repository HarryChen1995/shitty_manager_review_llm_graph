import streamlit as st
import tempfile
import os
from typing import TypedDict, List

from langchain_ollama import ChatOllama
from langchain.tools import tool
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
    AIMessage
)

from langgraph.graph import StateGraph, END
from langchain.agents import create_agent
from langchain_community.document_loaders import PyPDFLoader




st.set_page_config(page_title="Shitty Manager Analysis Agent", layout="centered")
st.title("🕵️‍♂️ Shitty Manager Review Agent")




model = ChatOllama(model="llama3.2", temperature=0)


@tool
def detect_manager_red_flags(review: str) -> str:
    """Detects 'DARVO' tactics, blame-shifting, and gaslighting language."""
    prompt = (
        "Role: Behavioral Analyst & Forensic Linguist\n"
        "Task: Identify markers of toxic management in the review text.\n"
        "Rubric: Look specifically for:\n"
        "1. Blame-shifting: Does the manager blame the individual for systemic/managerial failures?\n"
        "2. Ghost Feedback: Does the text use 'people are saying' or 'concerns were raised' without data?\n"
        "3. Weaponized Empathy: Using phrases like 'I want you to succeed' to mask unfair criticism.\n"
        f"Review Text: {review}"
    )
    return model.invoke(prompt).content

@tool
def fairness_assessment(review: str) -> str:
    """Checks if criticism is grounded in reality or ignores context (like leave)."""
    prompt = (
        "Role: HR Compliance Auditor\n"
        "Task: Assess if feedback is FAIR or UNFAIR.\n"
        "Rubric: Flag as UNFAIR if the manager penalizes the employee for productivity "
        "during protected leave or lack of resources. Identify if the 'Discussed' "
        "status is used as a tool for falsified documentation.\n"
        f"Review Text: {review}"
    )
    return model.invoke(prompt).content

@tool
def support_vs_control(review: str) -> str:
    """Maps the manager onto the Support-Autonomy Matrix."""
    prompt = (
        "Role: Executive Management Coach\n"
        "Task: Classify style as SUPPORTIVE, MICROMANAGING, NEGLECTFUL, or HYPOCRITICAL.\n"
        "Rubric: Use the Support-Autonomy framework. Specifically, look for high control "
        "on the employee (office hours) vs. low control on self (manager's own tardiness).\n"
        f"Review Text: {review}"
    )
    return model.invoke(prompt).content



@tool
def manager_competence_signal(review: str) -> str:
    """Distinguishes between 'Coaching' and 'Policing'."""
    prompt = (
        "Role: Leadership Consultant\n"
        "Task: Classify manager as COMPETENT or INCOMPETENT.\n"
        "Rubric: Competent managers build 'bridges' (actionable steps). Incompetent "
        "managers only point out 'gaps' and express frustration. Flag if the manager "
        "lacks the technical depth to actually evaluate the work.\n"
        f"Review Text: {review}"
    )
    return model.invoke(prompt).content

@tool
def bad_manager_verdict(review: str) -> str:
    """Synthesizes all behaviors into a final objective rating."""
    prompt = (
        "Role: Executive HR Director\n"
        "Task: Provide final verdict: NOT A BAD MANAGER, BORDERLINE, or BAD MANAGER.\n"
        "Strategy: Weigh ETHICS above all. If the meeting was falsified ('Discussed' checked "
        "with no meeting) and the manager is hypocritical, the verdict MUST be BAD MANAGER.\n"
        f"Review Text: {review}"
    )
    return model.invoke(prompt).content



tools = [detect_manager_red_flags, fairness_assessment, support_vs_control, manager_competence_signal, bad_manager_verdict]






SYSTEM_PROMPT = """You are a Senior Corporate Compliance Auditor and Technical Lead Investigator.
Your goal is to expose 'Technical Masking' and 'Administrative Sabotage'—where an incompetent manager uses vague interpersonal critiques and attendance policing to hide their own obsolescence.

Context:

1. SUBJECT: Jay Patel (Low technical competence/Software Engineer; currently on protected leave).
2. MANAGER: VP Political Appointee. NON-TECHNICAL (Cannot write code). 
3. HYPOCRISY: Manager is habitually late to the office but criticizes Jay for 'not staying long enough.'
4. TEAMWORK: Manager claims Jay can't work with the team, yet manager barely engages with the team themselves.
5. ETHICS BREACH: Falsified 'Discussed' status in the review while Jay was on leave.



use tools provided to give final verdict that if Jay is good or bad manager base on all facts in given context with all your reasoning.

Do not give me code, 
"""

agent = create_agent(model=model, tools = tools, system_prompt = SYSTEM_PROMPT)
class AgentState(TypedDict):
    messages: List[BaseMessage]

def analysis_node(state: AgentState):
    
    
    result = agent.invoke({"messages": [SystemMessage(content = SYSTEM_PROMPT)] + state["messages"]})
    return {"messages": result["messages"]}

workflow = StateGraph(AgentState)
workflow.add_node("analysis", analysis_node)
workflow.set_entry_point("analysis")
workflow.add_edge("analysis", END)
compiled_graph = workflow.compile()




def extract_text_from_pdf(uploaded_file) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name
    loader = PyPDFLoader(tmp_path)
    docs = loader.load()
    os.remove(tmp_path)
    return "\n\n".join(doc.page_content for doc in docs)




if "messages" not in st.session_state:
    st.session_state.messages = []




with st.sidebar:
    st.subheader("📄 Upload Review")
    uploaded_pdf = st.file_uploader("PDF only", type=["pdf"], label_visibility="collapsed")
    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()






for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


input_text = None

if uploaded_pdf:
    
    if not any("PDF review uploaded" in m["content"] for m in st.session_state.messages):
        with st.spinner("Extracting PDF..."):
            input_text = extract_text_from_pdf(uploaded_pdf)
            st.session_state.messages.append({"role": "user", "content": f"PDF review uploaded:\n\n{input_text[:1000]}..."})
    

user_input = st.chat_input("Ask about the manager...")
if user_input:
    input_text = user_input
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)


if input_text:
    with st.chat_message("assistant"):
        with st.spinner("Analyzing..."):
            
            history = []
            for m in st.session_state.messages:
                if m["role"] == "user":
                    history.append(HumanMessage(content=m["content"]))
                else:
                    history.append(AIMessage(content=m["content"]))
            
            result = compiled_graph.invoke({"messages": history})
            final_response = result["messages"][-1].content
            st.markdown(final_response)
            st.session_state.messages.append({"role": "assistant", "content": final_response})