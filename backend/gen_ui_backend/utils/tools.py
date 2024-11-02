from composio_langgraph import Action, ComposioToolSet
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_community import GoogleSearchAPIWrapper
from langchain_core.tools import Tool

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

search = GoogleSearchAPIWrapper()
google_search_tool = Tool(
    name="google_search",
    description="Search Google for recent results.",
    func=search.run,
)

email_tools = composio_toolset.get_tools(actions=[Action.GMAIL_CREATE_EMAIL_DRAFT, Action.GMAIL_SEND_EMAIL])

tools = [google_search_tool, *schedule_tools, *email_tools]

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