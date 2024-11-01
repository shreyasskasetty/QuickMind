import uvicorn
import os
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from langserve import add_routes

from gen_ui_backend.agent import create_graph
from gen_ui_backend.types import ChatInputType

# Load environment variables from .env file
load_dotenv()

UPLOAD_DIRECTORY = "uploaded_pdfs"

if not os.path.exists(UPLOAD_DIRECTORY):
    os.makedirs(UPLOAD_DIRECTORY)

def start() -> None:
    app = FastAPI(
        title="QuickMind API",
        version="1.0",
        description="API Server for QuickMind",
    )

    @app.get("/")
    async def redirect_root_to_docs():
        return RedirectResponse(url="/docs")
    
    # Configure CORS
    origins = [
        "http://localhost",
        "http://localhost:3000",
    ]

    @app.post("/uploadfile/")
    async def create_upload_file(file: UploadFile = File(...)):
        file_location = os.path.join(UPLOAD_DIRECTORY, file.filename)
        with open(file_location, "wb+") as file_object:
            file_object.write(file.file.read())
        return {"info": f"file '{file.filename}' saved at '{file_location}'"}
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    graph = create_graph()

    runnable = graph.with_types(input_type=ChatInputType, output_type=dict)

    add_routes(app, runnable, path="/chat", playground_type="default")
    print("Starting server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
