from typing import List, Union, Dict
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel


class ChatInputType(BaseModel):
    messages: List[Union[AIMessage, HumanMessage, SystemMessage]]