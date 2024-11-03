import streamlit as st
import asyncio
import httpx
import json
import time
from rag_utility import generate_data_store, query_rag
import os
from dotenv import load_dotenv
from httpx import Timeout
import traceback

load_dotenv()

working_dir = os.path.dirname(os.path.abspath(__file__))
datapath = "docs"
if not os.path.exists(os.path.join(working_dir, datapath)):
    os.mkdir(os.path.join(working_dir, datapath))

API_URL = "http://localhost:8000/chat/stream"

if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'label_visibility' not in st.session_state:
    st.session_state.label_visibility = "visible"
if 'model_type' not in st.session_state:
    st.session_state.model_type = "openai"

if 'pdf_docs' not in st.session_state:
    st.session_state.pdf_docs = []

def find_key(data, target_key):
    if isinstance(data, dict):
        for key, value in data.items():
            if key == target_key:
                return value
            result = find_key(value, target_key)
            if result is not None:
                return result
    elif isinstance(data, list):
        for item in data:
            result = find_key(item, target_key)
            if result is not None:
                return result
    return None

def format_message(message):
    if message['role'] == 'user':
        return {
            "content": message['content'],
            "additional_kwargs": {},
            "response_metadata": {},
            "type": "human",
            "name": "string",
            "id": "string",
            "example": False,
            "additionalProp1": {}
        }
    else:
        return {
            "content": message['content'],
            "additional_kwargs": {},
            "response_metadata": {},
            "type": "ai",
            "name": "string",
            "id": "string",
            "example": False,
            "additionalProp1": {}
        }
    
async def chat_with_bot(user_input):
    messages = list(map(format_message, st.session_state.messages)) if st.session_state.messages else []
    # messages.append({
    #       "content": user_input,
    #         "additional_kwargs": {},
    #         "response_metadata": {},
    #         "type": "ai",
    #         "name": "string",
    #         "id": "string",
    #         "example": False,
    #         "additionalProp1": {}
    # })

    input_json = {
                "input": {
                "messages": messages,
            },
            "config": {
                "configurable": {
                "model_name":st.session_state.model_type,
                }
            },
            "kwargs": {}
    }

    timeout = Timeout(10.0, read=300.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            async with client.stream("POST", API_URL, json=input_json) as response:
                if response.status_code == 200:
                    full_response = ""
                    with st.chat_message("assistant"):
                        message_placeholder = st.empty()
                        full_response = ""
                        last_event = None
                        
                        async for line in response.aiter_lines():
                            if line and line.startswith("event: "):
                                event_type = line.replace("event: ", "").strip()
                                continue
                            
                            if line and line.startswith("data: "):
                                chunk_json = json.loads(line[6:])
                                last_event = chunk_json  # Store the current event
                                
                                # Handle intent node
                                if "intent_node" in chunk_json:
                                    intent = chunk_json["intent_node"]["intent"]
                                    with st.expander("🎯 Intent", expanded=True):
                                        st.markdown(f"`{intent}`")
                                        st.session_state.messages.append({"role": "assistant", "content": intent, "type": "expander", "title":"🎯 Intent"})
                                
                                # Handle search node
                                elif "search_node" in chunk_json:
                                    messages = chunk_json["search_node"].get("messages", [])
                                    for msg in messages:
                                        if msg.get("tool_calls"):
                                            tool_call = msg["tool_calls"][0]
                                            if "function" in tool_call:
                                                tool_args = json.loads(tool_call["function"]["arguments"])
                                                with st.expander("🔍 Web Search Query", expanded=True):
                                                    st.markdown(f"`{tool_args.get('query', '')}`")
                                                    st.session_state.messages.append({"role": "assistant", "content": tool_args.get('query', ''), "type": "expander", "title":"🔍 Web Search Query"})
                                        else:
                                            with st.expander("🔍 Search Summary", expanded=True):
                                                st.markdown(f"`{msg.get('content', '')}`")
                                                st.session_state.messages.append({"role": "assistant", "content": msg.get('content', ''), "type": "expander", "title":"🔍 Search Summary"})
                                                

                                # Handle email send node
                                elif "email_send_node" in chunk_json:
                                    email_messages = chunk_json["email_send_node"].get("messages", [])
                                    for msg in email_messages:
                                        if msg.get("tool_calls"):
                                            tool_call = msg["tool_calls"][0]
                                            if "function" in tool_call:
                                                tool_args = json.loads(tool_call["function"]["arguments"])
                                                with st.expander("📧 Email Details", expanded=True):
                                                    email_details = f"""
                                                        **To:** {tool_args.get('recipient_email', 'N/A')}
                                                        **Subject:** {tool_args.get('subject', 'N/A')}
                                                        **Content:** {tool_args.get('body', 'N/A')}
                                                    """
                                                    st.markdown(email_details)
                                                st.session_state.messages.append({"role": "assistant", "content": email_details, "type": "expander", "title": "📧 Email Details"})
                                                
                                        else:
                                            with st.expander("📧 Email Information", expanded=True):
                                                response = msg.get('content', '').replace('FINAL ANSWER', '')
                                                st.markdown(response)
                                                st.session_state.messages.append({"role": "assistant", "content": response, "type": "expander", "title": "📧 Email Information"})
                                                

                                # Handle scheduler node
                                elif "scheduler_node" in chunk_json:
                                    scheduler_messages = chunk_json["scheduler_node"].get("messages", [])
                                    for msg in scheduler_messages:
                                        if msg.get("tool_calls"):
                                            tool_call = msg["tool_calls"][0]
                                            if "function" in tool_call:
                                                tool_args = json.loads(tool_call["function"]["arguments"])
                                                with st.expander("📅 Meeting Request", expanded=True):
                                                    meeting_details = f"""
                                                        **Title:** {tool_args.get('title', 'N/A')}
                                                        **Time:** {tool_args.get('time', 'N/A')}
                                                        **Duration:** {tool_args.get('duration', 'N/A')}
                                                        **Attendees:** {', '.join(tool_args.get('attendees', ['N/A']))}
                                                    """
                                                    st.markdown(meeting_details)
                                                    st.session_state.messages.append({"role": "assistant", "content": meeting_details, "type": "expander", "title": "📅 Meeting Request"})
                                                
                                        else:
                                            with st.expander("📅 Scheduler Response", expanded=True):
                                                response = msg.get('content')
                                                response = response.replace("FINAL ANSWER", "")
                                                st.markdown(response)
                                                st.session_state.messages.append({"role": "assistant", "content": response, "type": "expander", "title": "📅 Scheduler Response"})
                                                

                                # Handle tool node
                                elif "tool_node" in chunk_json:
                                    tool_messages = chunk_json["tool_node"].get("messages", [])
                                    for msg in tool_messages:
                                        if msg.get("type") == "tool":
                                            tool_name = msg.get("name", "unknown")
                                            tool_content = msg.get("content", "")
                                            if "email" in tool_name.lower():
                                                try:
                                                    response_data = json.loads(tool_content)
                                                    if "draft" in tool_name.lower() and response_data.get("successful"):
                                                        with st.expander("📧 Email Draft Created", expanded=True):
                                                            message = "Email draft created successfully!"
                                                            st.success(message)
                                                            st.session_state.messages.append({"role": "assistant", "content": message, "type": "expander-success", "title": "📧 Email Draft Created"})        
                                                    elif "send" in tool_name.lower():
                                                        response_data = json.loads(tool_content)
                                                        if response_data.get("successfull"):
                                                            with st.expander("📧 Email Tool Result", expanded=True):
                                                                message = "Email sent successfully!"
                                                                st.success(message)
                                                                st.session_state.messages.append({"role": "assistant", "content": message, "type": "expander-success", "title": "📧 Email Tool Result"})        
                                                        else:
                                                            with st.expander("📧 Email Tool Result", expanded=True):
                                                                message ="Failed to send email."
                                                                st.error(message)
                                                                st.session_state.messages.append({"role": "assistant", "content": message, "type": "expander-error", "title": "📧 Email Tool Result"})        
               
                                                except Exception as e:
                                                    print(e)
                                                    with st.expander("📧 Email Tool Result", expanded=True):
                                                        st.markdown(tool_content)
                                            elif "schedule" in tool_name.lower():
                                                try:
                                                    # Parse the response data
                                                    response_data = json.loads(tool_content)
                                                    if response_data.get("successfull") and response_data.get("data", {}).get("response_data"):
                                                        event = response_data["data"]["response_data"]
                                                        # Format the datetime strings
                                                        start_time = event["start"]["dateTime"]
                                                        end_time = event["end"]["dateTime"]
                                                        
                                                        # Format attendees list
                                                        attendees = ", ".join([att["email"] for att in event.get("attendees", [])])
                                                        
                                                        with st.expander("📅 Meeting Scheduled!", expanded=True):
                                                            message = f"""
                                                                    ✅ **Meeting Successfully Scheduled**
                                                                    
                                                                    **Title:** {event.get('summary')}
                                                                    **Date:** {start_time} to {end_time}
                                                                    **Attendees:** {attendees}
                                                                    **Organizer:** {event.get('organizer', {}).get('email')}
                                                                    
                                                                    [View in Calendar]({event.get('htmlLink')})
                                                                    """
                                                            st.markdown(message)
                                                            st.session_state['messages'].append({"role": "assistant", "content": message.strip(), "type": "expander", "title": "📅 Success"})
                                                    else:
                                                        with st.expander("📅 Error", expanded=True):
                                                            message = "Failed to schedule the meeting. Please try again."
                                                            st.error(message)
                                                        st.session_state['messages'].append({"role": "assistant", "content": message.strip(), "type": "expander-error", "title": "📅 Error"})
                                                except json.JSONDecodeError:
                                                    with st.expander("📅 Error", expanded=True):
                                                        message = "Failed to process scheduler response."
                                                        st.error(message)
                                                    st.session_state['messages'].append({"role": "assistant", "content": message.strip(), "type": "expander-error", "title": "📅 Error"})
                                            elif "search" in tool_name.lower():
                                                try:
                                                    # results = json.loads(tool_content)
                                                    with st.expander("🔍 Search Results", expanded=True):
                                                        st.markdown(
                                                            f'<div style="max-height: 300px; overflow-y: auto;">{tool_content}</div>',
                                                            unsafe_allow_html=True
                                                        )
                                                    st.session_state['messages'].append({"role": "assistant", "content": tool_content.strip(), "type": "expander", "title": "🔍 Search Results"})
                                                except Exception as e:
                                                    with st.expander("🔍 Search Results", expanded=True):
                                                        message = "failed to process search results"
                                                        st.error(message)
                                                        st.session_state['messages'].append({"role": "assistant", "content": message.strip(), "type": "expander-error", "title": "🔍 Search Results"})
                                else:
                                    # Handle regular content (LLM response)
                                    output_content = find_key(chunk_json, "content")
                                    if output_content is not None and output_content.strip():
                                        full_response += output_content
                                        if not any(node in last_event for node in ["intent_node", "search_node", "email_send_node", "scheduler_node", "tool_node"]):
                                            message_placeholder.markdown(full_response + "▌")
                                        else:
                                            with st.expander("🤖 Intermediate Response", expanded=True):
                                                st.markdown(full_response)
                                                st.session_state['messages'].append({"role": "assistant", "content": full_response.strip(), "type": "chat", "title": "🔍 Search Results"})
                        # Final message display (always in message_placeholder)
                        full_response = full_response.replace("FINAL ANSWER", "")
                        message_placeholder.markdown(full_response.strip())
                    
                    st.session_state['messages'].append({"role": "assistant", "content": full_response.strip(), "type": "chat"})
                else:
                    error_message = await response.aread()
                    st.error(f"Error: {error_message}")
        except httpx.ReadTimeout:
            st.error("ReadTimeout: The request took too long to process.")
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            traceback.print_exc()

# Add custom CSS at the top of the file
st.markdown("""
    <style>
    .stRadio [role=radiogroup] {
        padding: 10px;
        border-radius: 8px;
        background-color: #f0f2f6;
    }
    
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    .stTitle {
        font-size: 2.5rem;
        font-weight: 600;
        color: #0f52ba;
    }
    </style>
""", unsafe_allow_html=True)


st.title("🤖 QuickMind")
st.markdown("##### Your Personal AI Assistant")

with st.sidebar:
    st.markdown("### 📄 Upload Documents")
    

    uploaded_files = st.file_uploader(
        "Upload your PDFs",
        type=['pdf'],
        accept_multiple_files=True,
        label_visibility= st.session_state.label_visibility
    )

    if uploaded_files:
        if st.button("Upload Selected Files"):
            all_successful = False
            for uploaded_file in uploaded_files:
                try:
                    # files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                    # response = httpx.post("http://localhost:8000/uploadfile/", files=files)
                    
                    # if response.status_code == 200:
                    
                    pdf_info = {
                        "name": uploaded_file.name,
                        "content": ""
                    }
                    bytes_data = uploaded_file.read()
                    file_name = pdf_info["name"]
                    file_path = os.path.join(working_dir, datapath, file_name)
                    with open(file_path, "wb") as f:
                        f.write(bytes_data)
                    if pdf_info not in st.session_state.pdf_docs:
                        st.session_state.pdf_docs.append(pdf_info)
                    alert  = st.success(f"Successfully uploaded {uploaded_file.name}")
                    time.sleep(2) # Wait for 2 seconds
                    alert.empty() # Clear the alert
                    all_successful = True                        
                except Exception as e:
                    st.error(f"Error uploading {uploaded_file.name}: {str(e)}")
            if all_successful:
                generate_data_store()

    # Display uploaded PDFs
    if st.session_state.pdf_docs:
        st.markdown("### 📚 Uploaded Documents")
        for doc in st.session_state.pdf_docs:
            st.markdown(f"- {doc['name']}")
            
    st.markdown("---")
    model_type = st.radio(
        "**Select Model Type:**",
        options=["openai", "llama"],
        index=0,
        key="model_type",
        help="Choose between local (Llama) or cloud (OpenAI) model",
        format_func=lambda x: "🦙 Local Llama" if x == "llama" else "☁️ OpenAI"
    )
    st.markdown("---")
    st.markdown("*Made with ❤️ by Shreyas")

    # Add PDF mode toggle here
    st.markdown("### 🔍 Query Mode")
    if 'pdf_mode' not in st.session_state:
        st.session_state.pdf_mode = False
    
    pdf_mode = st.toggle(
        "Query uploaded documents",
        value=st.session_state.pdf_mode,
        help="Toggle this to query your uploaded PDFs instead of general chat"
    )
    
    if pdf_mode != st.session_state.pdf_mode:
        st.session_state.pdf_mode = pdf_mode
    
    # Show active mode indicator
    if st.session_state.pdf_mode:
        st.markdown("**Active Mode:** 📚 Document Query")
        if not st.session_state.pdf_docs:
            st.warning("⚠️ No documents uploaded yet!")
    else:
        st.markdown("**Active Mode:** 💭 General Chat")
    
    st.markdown("---")

# Remove the subheader and replace with a cleaner prompt
st.markdown("#### Start chatting below 💭")

for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        content = message['content']  # Simplified content assignment
        if "expander" in message["type"]:
            with st.expander(message["title"], expanded=True):
                # Add a scroll box for the expander content

                if "success" in message["type"]:
                    st.success(content)
                elif "error" in message["type"]:
                    st.error(content)
                else:
                    st.markdown(
                    f"""
                    <div style="max-height: 300px; overflow-y: auto;">
                        {content}
                    </div>
                    """, 
                    unsafe_allow_html=True
                    )
        else:
            st.write(content)

if prompt := st.chat_input("You:"):
    # Add PDF context to the message if PDF mode is enabled
    st.session_state['messages'].append({"role": "user", "content": prompt, "type": "chat"})
    with st.chat_message("user"):
        st.markdown(prompt)
    if st.session_state.pdf_mode and st.session_state.pdf_docs:
        # prompt = f"Using the context from the upload PDF documents, please answer: {prompt}"
        formatted_response, response_text  = query_rag(prompt)
        with st.chat_message("assistant"):
            st.markdown(formatted_response["response"])
        st.session_state['messages'].append({"role": "assistant", "content": formatted_response["response"], "type": "chat"})
    elif st.session_state.pdf_mode and not st.session_state.pdf_docs:
        st.error("Please upload documents first to use document query mode!")
        st.stop()
    else:
        asyncio.run(chat_with_bot(prompt))
