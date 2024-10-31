from langchain_community.tools.tavily_search import TavilySearchResults
from composio_langgraph import Action, ComposioToolSet
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

import os

composio_toolset = ComposioToolSet()
schedule_tools = composio_toolset.get_tools(
    actions=[
        Action.GOOGLECALENDAR_FIND_FREE_SLOTS,
        Action.GOOGLECALENDAR_CREATE_EVENT,
        Action.GOOGLECALENDAR_UPDATE_EVENT,
        Action.GOOGLECALENDAR_DELETE_EVENT,
    ]
)
email_tools = composio_toolset.get_tools(actions=[Action.GMAIL_CREATE_EMAIL_DRAFT, Action.GMAIL_SEND_EMAIL])

tools = [TavilySearchResults(max_results=2), *schedule_tools, *email_tools]

def create_retriever_tool(docs):
    doc_list = [doc["content"] for  doc in docs]
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=100, chunk_overlap=50
    )
    doc_splits = text_splitter.split_documents(doc_list)

    # Add to vectorDB
    vectorstore = Chroma.from_documents(
        documents=doc_splits,
        collection_name="rag-chroma",
        embedding=OpenAIEmbeddings(),
    )
    retriever = vectorstore.as_retriever()
    retriever_tool = create_retriever_tool(
        retriever,
        "retrieve_pdfs_docs",
        "Search and return information from the pdf documents given relevant to the question"
    )
    return retriever_tool