from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import ToolNode
from gen_ui_backend.utils.graphs.RAGGraph.nodes import AgentState, grade_documents, \
                                  agent, rewrite, generate, read_all_pdfs
from gen_ui_backend.utils.tools import create_retriever_tool
from langgraph.graph.graph import CompiledGraph
from langgraph.prebuilt import tools_condition


def create_rag_graph() -> CompiledGraph:
    # Define a new graph
    workflow = StateGraph(AgentState)
    docs = read_all_pdfs("/Users/shreyasskasetty/Desktop/github_projects/quick-mind-v1/backend/uploaded_pdfs")
    retriever_tool = create_retriever_tool(list(docs.values()))
    # Define the nodes we will cycle between
    workflow.add_node("agent", agent)  # agent
    retrieve = ToolNode([retriever_tool])
    workflow.add_node("retrieve", retrieve)  # retrieval
    workflow.add_node("rewrite", rewrite)  # Re-writing the question
    workflow.add_node(
        "generate", generate
    )  # Generating a response after we know the documents are relevant
    # Call agent node to decide to retrieve or not
    workflow.add_edge(START, "agent")

    # Decide whether to retrieve
    workflow.add_conditional_edges(
        "agent",
        # Assess agent decision
        tools_condition,
        {
            # Translate the condition outputs to nodes in our graph
            "tools": "retrieve",
            END: END,
        },
    )

    # Edges taken after the `action` node is called.
    workflow.add_conditional_edges(
        "retrieve",
        # Assess agent decision
        grade_documents,
    )
    workflow.add_edge("generate", END)
    workflow.add_edge("rewrite", "agent")

    # Compile
    graph = workflow.compile()
    return graph