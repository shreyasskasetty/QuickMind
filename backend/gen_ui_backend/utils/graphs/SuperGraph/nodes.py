
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode
from langgraph.graph import END
from langchain import hub
from langchain_core.messages import AIMessage, HumanMessage
from functools import lru_cache
from gen_ui_backend.utils.states import Intent
from gen_ui_backend.utils.tools import tools
from gen_ui_backend.utils.states import SuperGraphState
from datetime import datetime
from typing import Optional, Any, Literal
import os
DATE_TIME: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
TIMEZONE: Optional[Any] = datetime.now().astimezone().tzinfo

DATE_TIME = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

## Utility helper functions
@lru_cache(maxsize=4)
def _get_model(model_name: str, bind_tools=False):
    if model_name == "openai":
        model = ChatOpenAI(temperature=0, model_name="gpt-4o")
    elif model_name == "llama":
        model = ChatOpenAI(api_key="ollama", model="llama3.2", base_url="http://localhost:11434/v1")
    else:
        raise ValueError(f"Unsupported model type: {model_name}")
    
    if bind_tools:
        model = model.bind_tools(tools = tools)
    return model


def _setup_intent_detection(config):
    prompt = hub.pull("quick-mind/intent")
    model_name = config.get('configurable', {}).get("model_name", "openai")
    llm = _get_model(model_name)
    llm_with_tools = llm.bind_tools(tools=[Intent])
    return prompt | llm_with_tools


def _setup_meeting_scheduler(config):
    prompt = hub.pull("quick-mind/scheduler")
    model_name = config.get('configurable', {}).get("model_name", "openai")
    llm = _get_model(model_name, bind_tools=True)
    return prompt | llm


def _setup_email_sender(config):
    prompt = hub.pull("quick-mind/email")
    model_name = config.get('configurable', {}).get("model_name", "openai")
    llm = _get_model(model_name, bind_tools=True)
    return prompt | llm


def _setup_search_agent(config):
    prompt = hub.pull("quick-mind/search")
    model_name = config.get('configurable', {}).get("model_name", "openai")
    llm = _get_model(model_name, bind_tools=True)
    return prompt | llm


## Define Node Functions
def search_agent(state, config):
    messages = state["messages"]
    model = _setup_search_agent(config)
    response = model.invoke({"question": messages[-1].content, "chat_history": messages[:-1], "DATE_TIME":DATE_TIME, "TIMEZONE":TIMEZONE})
    print(response)
    # We return a list, because this will get added to the existing list
    return {"messages": [response], "sender": "search_agent"}


def send_email_agent(state: SuperGraphState, config):
    messages = state["messages"]
    question = messages[-1].content
    chat_history = messages[:-1]
    email_sender = _setup_email_sender(config)
    response = email_sender.invoke({"chat_history": chat_history, "question": question})
    return {"messages": [response], "sender": "email_sender_agent"}


def send_email_router(state: SuperGraphState):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "call_tool"
    
    if "FINAL ANSWER" in last_message.content:
        return "__end__"
    return "continue"


def schedule_meeting_agent(state: SuperGraphState, config):
    messages = state["messages"]
    question = messages[-1].content
    chat_history = messages[:-1]
    meeting_scheduler = _setup_meeting_scheduler(config)
    response = meeting_scheduler.invoke({"chat_history": chat_history, "question": question, "DATE_TIME":DATE_TIME, "TIMEZONE":TIMEZONE})
    return {"messages": [response], "sender": "meeting_scheduler_agent"} 
 

def detect_intent(state: SuperGraphState, config):
    messages = state["messages"]
    question = messages[-1].content
    chat_history = messages[:-1]
    intent_detection = _setup_intent_detection(config)
    response = intent_detection.invoke({"chat_history": chat_history, "question": question})
    print(f"Intent detection response: {response['intent']}")
    return {"intent": response['intent']}


def llm_answer(state :SuperGraphState, config):
    messages = state["messages"]
    model_name = config.get('configurable', {}).get("model_name", "openai")
    llm = _get_model(model_name)
    response = llm.invoke(messages)
    response = AIMessage(content=response.content)
    return {"messages": response}

## Define Edge Functions
def route_to_agent(state: SuperGraphState, config):
    intent = state["intent"]
    if intent is None:
        return END
    elif intent == "greeting":
        return "llm_agent"
    elif intent == "follow_up_question":
        return "llm_agent"
    elif intent == "search_internet":
        return "search_agent"
    elif intent == "schedule_meeting":
        return "scheduler_meeting_agent"
    elif intent == "send_email":
        return "send_email_agent"
    else:
        return "llm_agent"
    # elif intent == "document_query":
    #     return "document_query_agent"




# Define the function that determines whether to continue or not
def continue_search(state: SuperGraphState):
    messages = state["messages"]
    last_message = messages[-1]
    # If there are no tool calls, then we finish
    if not last_message.tool_calls:
        return "end"
    # Otherwise if there is, we continue
    else:
        return "continue"

def route_from_call_tool(state: SuperGraphState):
    if "sender" in state:
        sender = state["sender"]
        if sender == "search_agent":
            return "search_node"
        elif sender == "meeting_scheduler_agent":
            return "scheduler_node"
        elif sender == "email_sender_agent":
            return "send_email_node"
    else:
        return "end"
    
# Router function for scheduler
def scheduler_router(state) -> Literal["call_tool", "__end__", "continue"]:
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "call_tool"
    if "FINAL ANSWER" in last_message.content:
        return "__end__"
    return "continue"

# Define the function to execute tools
tool_node = ToolNode(tools)