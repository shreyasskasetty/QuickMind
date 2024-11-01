from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage, HumanMessage
from typing import TypedDict, Annotated, Sequence, Optional, List
from enum import Enum
from pydantic import BaseModel

class IntentEnum(str, Enum):
    GREETING = "greeting"
    DOCUMENT_QUERY = "document_query"
    SCHEDULE_MEETING = "schedule_meeting"
    SEND_EMAIL = "send_email"
    SEARCH_INTERNET = "search_internet"
    FOLLOW_UP_QUESTION = "follow_up_question"
    
class Intent(BaseModel):
    intent: IntentEnum
    
class SuperGraphState(TypedDict, total=False):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    sender: Optional[str]
    intent: Optional[Intent]

class RagGraphState(TypedDict):
    rag_result: str
    question: str