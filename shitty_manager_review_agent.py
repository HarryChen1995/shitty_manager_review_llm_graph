from typing import TypedDict, List
from langchain_community.llms import Ollama
from langchain_experimental.llms.ollama_functions import OllamaFunctions
from langchain.tools import tool
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langchain.agents import create_agent
import streamlit as st



llm = Ollama(model="llama3.2", temperature=0)


def cot_stream(tool_name: str, reasoning: str):
    """Helper to display tool reasoning in the Streamlit UI."""
    with st.status(f"Tool: {tool_name}", expanded=False):
        st.write(f"**Thinking:** {reasoning}")

@tool
def detect_manager_red_flags(review: str) -> str:
    """Detect red flags indicating poor or toxic management behavior."""
    reasoning = "Identifying language patterns that suggest blame-shifting or lack of concrete support."
    cot_stream("Red Flag Detector", reasoning)
    return llm.invoke(f"Analyze the review for manager red flags (vague criticism, shifting blame). Review: {review}")

@tool
def fairness_assessment(review: str) -> str:
    """Assess if the manager feedback is fair, justified, and proportional."""
    reasoning = "Comparing performance claims against the timeline provided (review written during leave)."
    cot_stream("Fairness Evaluator", reasoning)
    return llm.invoke(f"Assess if feedback is FAIR or UNFAIR: {review}")

@tool
def support_vs_control(review: str) -> str:
    """Classify the manager's style as Supportive, Micromanaging, Controlling, or Neglectful."""
    reasoning = "Evaluating the tone for signs of micromanagement vs. lack of involvement."
    cot_stream("Style Classifier", reasoning)
    return llm.invoke(f"Classify manager style (Supportive/Controlling) with reason: {review}")

@tool
def manager_competence_signal(review: str) -> str:
    """Evaluate competence in people management."""
    reasoning = "Checking for coaching mindset and accountability traits."
    cot_stream("Competence Analyzer", reasoning)
    return llm.invoke(f"Classify manager as COMPETENT or INCOMPETENT: {review}")

@tool
def bad_manager_verdict(review: str) -> str:
    """Final verdict: NOT A BAD MANAGER, BORDERLINE, or BAD MANAGER."""
    reasoning = "Synthesizing all behavioral data for a final objective rating."
    cot_stream("Final Verdict Engine", reasoning)
    return llm.invoke(f"Provide final verdict: {review}")

tools = [detect_manager_red_flags, fairness_assessment, support_vs_control, manager_competence_signal, bad_manager_verdict]




from langchain_ollama import ChatOllama

model = ChatOllama(model="llama3.2", temperature=0)


model_with_tools = model.bind_tools(tools)


system_message = """You are an objective management analyst. 
Context: Jay Patel is on leave. The manager is a VP promoted via politics. 
Review was marked 'discussed' without a meeting. Analyze based on these facts. 
Output ONLY the tool call when using tools. Respond in Markdown."""

agent = create_agent(
    model=model_with_tools, 
    tools=tools, 
    system_prompt=system_message
)

class AgentState(TypedDict):
    messages: List[BaseMessage]

def analysis_node(state: AgentState):
    result = agent.invoke(state)
    return {"messages": result["messages"]}

workflow = StateGraph(AgentState)
workflow.add_node("analysis", analysis_node)
workflow.set_entry_point("analysis")
workflow.add_edge("analysis", END)
compiled_graph = workflow.compile()



st.set_page_config(page_title="Manager Analysis Agent")
st.title("🕵️‍♂️ Shitty Manager Review")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display all past messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


user_input = st.chat_input("Paste review text and press Enter...")

if user_input:

    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)


    with st.spinner("Thinking..."):
     
        initial_state = {"messages": [HumanMessage(content=user_input)]}
        outputs = list(compiled_graph.stream(initial_state))


    last_output = outputs[-1]
    analysis_output = last_output.get("analysis", {})
    
    if analysis_output:
        final_messages = analysis_output.get("messages", [])
        if final_messages:
            final_text = final_messages[-1].content
            # Append assistant response to chat history
            st.session_state.messages.append({"role": "assistant", "content": final_text})
            with st.chat_message("assistant"):
                st.markdown(final_text)