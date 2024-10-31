from typing import TypedDict, Literal

from langgraph.graph import StateGraph, END, START
from langgraph.graph.graph import CompiledGraph
from gen_ui_backend.utils.graphs.SuperGraph.nodes import detect_intent, route_from_call_tool, \
                                                        send_email_router, send_email_agent, \
                                                        tool_node, schedule_meeting_agent, \
                                                        llm_answer,continue_search, route_to_agent, \
                                                        search_agent, scheduler_router
from gen_ui_backend.utils.states import SuperGraphState
# from gen_ui_backend.rag_agent import create_rag_graph

# Define the config
class GraphConfig(TypedDict):
    #model_name: Literal["anthropic", "openai"]
    model_name: Literal["openai", "llama"]

def create_graph() -> CompiledGraph:
    # Define a new graph
    workflow = StateGraph(SuperGraphState, config_schema=GraphConfig)
    # subgraph = create_rag_graph()
    # Define the two nodes we will cycle between
    workflow.add_node("intent_node", detect_intent)
    workflow.add_node("llm_node", llm_answer)
    workflow.add_node("search_node", search_agent)
    workflow.add_node("tool_node", tool_node)
    workflow.add_node("scheduler_node", schedule_meeting_agent)
    workflow.add_node("send_email_node", send_email_agent)
    # workflow.add_node("rag_node", subgraph)
    # Set the entrypoint as `agent`
    # This means that this node is the first one called
    workflow.add_edge(START, "intent_node")
    workflow.add_edge('llm_node', END)
    workflow.add_conditional_edges(
        "intent_node",
        route_to_agent,
        {
            "llm_agent": "llm_node",
            "search_agent": "search_node",
            "scheduler_meeting_agent": "scheduler_node",
            "send_email_agent": "send_email_node",
            # "document_query_agent": "rag_node",
            END: END,
        },
    )
    # workflow.add_edge("rag_node", END)
    workflow.add_conditional_edges(
        "send_email_node",
        send_email_router,
        {
            "continue": "send_email_node",
            "call_tool": "tool_node",
            END: END,
        }
    )

    workflow.add_conditional_edges(
        "scheduler_node",
        scheduler_router,
        {
            "continue": "scheduler_node",
            "call_tool": "tool_node",
            END: END,
        }
    )

    # We now add a conditional edge
    workflow.add_conditional_edges(
        # First, we define the start node. We use `agent`.
        # This means these are the edges taken after the `agent` node is called.
        "search_node",
        # Next, we pass in the function that will determine which node is called next.
        continue_search,
        # Finally we pass in a mapping.
        # The keys are strings, and the values are other nodes.
        # END is a special node marking that the graph should finish.
        # What will happen is we will call `continue_search`, and then the output of that
        # will be matched against the keys in this mapping.
        # Based on which one it matches, that node will then be called.
        {
            # If `tools`, then we call the tool node.
            "continue": "tool_node",
            # Otherwise we finish.
            "end": END,
        },
    )

    workflow.add_conditional_edges(
        "tool_node", 
        route_from_call_tool,
        {
            "search_node": "search_node",
            "scheduler_node": "scheduler_node",
            "send_email_node": "send_email_node",
            "end": END
        }
    )

    # We now add a normal edge from `tools` to `agent`.
    # This means that after `tools` is called, `agent` node is called next.
    # workflow.add_edge("action", "agent")

    # Finally, we compile it!
    # This compiles it into a LangChain Runnable,
    # meaning you can use it as you would any other runnable
    graph = workflow.compile()
    return graph

graph = create_graph()
