# GPT Researcher - Complete Documentation

## Table of Contents

- [Design Documentation](#design-documentation)
- [Main Application](#main-application)
- [Backend Server](#backend-server)
- [Multi-Agent System](#multi-agent-system)

---

## Design Documentation

### documentation/app_design.md

# GPT Researcher - Diseño de la Aplicación

## Estructura General

La aplicación sigue una arquitectura cliente-servidor con WebSocket para comunicación en tiempo real.

### 1. Frontend

El sistema multi-agente proporciona:
- Coordinación de múltiples agentes especializados
- Investigación y recopilación de información
- Generación y edición de reportes
- Revisión y mejora de contenido

### 2. Inicialización del Sistema

1. **Configuración Inicial**
   - Carga de variables de entorno (.env)
   - Creación del directorio de logs
   - Configuración del sistema de logging
   - Supresión de logs verbosos (fontTools)

2. **Servidor FastAPI**
   - Inicialización del servidor en puerto 8000
   - Configuración de CORS y middleware
   - Establecimiento de rutas y endpoints

### 3. Sistema Multi-Agente

El sistema incluye varios agentes especializados:
- Browser Agent: Navegación y búsqueda web
- Editor Agent: Edición y formato de contenido
- Researcher Agent: Investigación profunda
- Reviewer Agent: Revisión de calidad
- Revisor Agent: Mejoras y correcciones
- Writer Agent: Generación de contenido
- Publisher Agent: Formateo final y publicación

### 4. Flujo de Datos

1. **Inicio de Petición**
   - Usuario ingresa consulta en frontend
   - Se establece conexión WebSocket
   - Se envían parámetros de investigación

2. **Procesamiento Backend**
   - `main.py` recibe y valida la petición
   - `websocket_manager.py` establece streaming
   - `server_utils.py` coordina el proceso

3. **Investigación Multi-Agente**
   - Sistema multi-agente se activa
   - Agentes realizan investigación coordinada
   - Cada agente ejecuta su tarea especializada
   - Se mantiene registro detallado en logs
   - Se genera reporte según especificaciones

4. **Respuesta y Archivos**
   - Reporte se envía al frontend
   - Se generan archivos en múltiples formatos:
     - PDF
     - DOCX
     - Markdown
     - JSON (logs)
   - Usuario recibe resultados y puede descargarlos

### 5. Sistema de Logging

El sistema implementa logging comprehensivo:
- Logs detallados en `logs/app.log`
- Formato timestamp - nombre - nivel - mensaje
- Handlers para archivo y consola
- Supresión de logs innecesarios
- Tracking de investigaciones y errores

### 6. Gestión de WebSocket

El WebSocketManager proporciona:
- Conexiones en tiempo real
- Colas de mensajes asíncronas
- Gestión de tareas de envío
- Chat con agentes basado en memoria
- Streaming de resultados de investigación

### 7. Tipos de Reportes

Se soportan múltiples tipos:
- Reporte Básico (BasicReport)
- Reporte Detallado (DetailedReport)
- Reporte Multi-Agente (investigación colaborativa)

### 8. Extensibilidad

El sistema está diseñado para:
- Agregar nuevos tipos de agentes
- Implementar nuevos formatos de reporte
- Integrar fuentes adicionales de datos
- Personalizar flujos de investigación

## Notas de Implementación

- TypeScript para frontend
- FastAPI para backend
- WebSocket para comunicación en tiempo real
- Sistema modular de agentes
- Logging comprehensivo
- Manejo asíncrono de tareas

---

## Main Application

### main.py

```python
from dotenv import load_dotenv
import logging
from pathlib import Path

# Create logs directory if it doesn't exist
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        # File handler for general application logs
        logging.FileHandler('logs/app.log'),
        # Stream handler for console output
        logging.StreamHandler()
    ]
)

# Suppress verbose fontTools logging
logging.getLogger('fontTools').setLevel(logging.WARNING)
logging.getLogger('fontTools.subset').setLevel(logging.WARNING)
logging.getLogger('fontTools.ttLib').setLevel(logging.WARNING)

# Create logger instance
logger = logging.getLogger(__name__)

load_dotenv()

from backend.server.server import app

if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## Backend Server

### backend/server/server.py

```python
import json
import os
from typing import Dict, List

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, File, UploadFile, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from backend.server.websocket_manager import WebSocketManager
from backend.server.server_utils import (
    get_config_dict,
    update_environment_variables, handle_file_upload, handle_file_deletion,
    execute_multi_agents, handle_websocket_communication
)


from gpt_researcher.utils.logging_config import setup_research_logging

import logging

# Get logger instance
logger = logging.getLogger(__name__)

# Don't override parent logger settings
logger.propagate = True

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()  # Only log to console
    ]
)

# Models


class ResearchRequest(BaseModel):
    task: str
    report_type: str
    agent: str


class ConfigRequest(BaseModel):
    ANTHROPIC_API_KEY: str
    TAVILY_API_KEY: str
    LANGCHAIN_TRACING_V2: str
    LANGCHAIN_API_KEY: str
    OPENAI_API_KEY: str
    DOC_PATH: str
    RETRIEVER: str
    GOOGLE_API_KEY: str = ''
    GOOGLE_CX_KEY: str = ''
    BING_API_KEY: str = ''
    SEARCHAPI_API_KEY: str = ''
    SERPAPI_API_KEY: str = ''
    SERPER_API_KEY: str = ''
    SEARX_URL: str = ''
    XAI_API_KEY: str
    DEEPSEEK_API_KEY: str


# App initialization
app = FastAPI()

# Static files and templates
app.mount("/site", StaticFiles(directory="./frontend"), name="site")
app.mount("/static", StaticFiles(directory="./frontend/static"), name="static")
templates = Jinja2Templates(directory="./frontend")

# WebSocket manager
manager = WebSocketManager()

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
DOC_PATH = os.getenv("DOC_PATH", "./my-docs")

# Startup event


@app.on_event("startup")
def startup_event():
    os.makedirs("outputs", exist_ok=True)
    app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")
    os.makedirs(DOC_PATH, exist_ok=True)
    

# Routes


@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "report": None})


@app.get("/files/")
async def list_files():
    files = os.listdir(DOC_PATH)
    print(f"Files in {DOC_PATH}: {files}")
    return {"files": files}


@app.post("/api/multi_agents")
async def run_multi_agents():
    return await execute_multi_agents(manager)


@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    return await handle_file_upload(file, DOC_PATH)


@app.delete("/files/{filename}")
async def delete_file(filename: str):
    return await handle_file_deletion(filename, DOC_PATH)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        await handle_websocket_communication(websocket, manager)
    except WebSocketDisconnect:
        await manager.disconnect(websocket)

```

---

### backend/server/websocket_manager.py

```python
import asyncio
import datetime
from typing import Dict, List

from fastapi import WebSocket

from backend.report_type import BasicReport, DetailedReport
from backend.chat import ChatAgentWithMemory

from gpt_researcher.utils.enum import ReportType, Tone
from multi_agents.main import run_research_task
from gpt_researcher.actions import stream_output  # Import stream_output
from backend.server.server_utils import CustomLogsHandler


class WebSocketManager:
    """Manage websockets"""

    def __init__(self):
        """Initialize the WebSocketManager class."""
        self.active_connections: List[WebSocket] = []
        self.sender_tasks: Dict[WebSocket, asyncio.Task] = {}
        self.message_queues: Dict[WebSocket, asyncio.Queue] = {}
        self.chat_agent = None

    async def start_sender(self, websocket: WebSocket):
        """Start the sender task."""
        queue = self.message_queues.get(websocket)
        if not queue:
            return

        while True:
            message = await queue.get()
            if websocket in self.active_connections:
                try:
                    if message == "ping":
                        await websocket.send_text("pong")
                    else:
                        await websocket.send_text(message)
                except:
                    break
            else:
                break

    async def connect(self, websocket: WebSocket):
        """Connect a websocket."""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.message_queues[websocket] = asyncio.Queue()
        self.sender_tasks[websocket] = asyncio.create_task(
            self.start_sender(websocket))

    async def disconnect(self, websocket: WebSocket):
        """Disconnect a websocket."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self.sender_tasks[websocket].cancel()
            await self.message_queues[websocket].put(None)
            del self.sender_tasks[websocket]
            del self.message_queues[websocket]

    async def start_streaming(self, task, report_type, report_source, source_urls, document_urls, tone, websocket, headers=None):
        """Start streaming the output."""
        tone = Tone[tone]
        config_path = "default"
        report = await run_agent(task, report_type, report_source, source_urls, document_urls, tone, websocket, headers=headers, config_path=config_path)
        self.chat_agent = ChatAgentWithMemory(report, config_path, headers)
        return report

    async def chat(self, message, websocket):
        """Chat with the agent based message diff"""
        if self.chat_agent:
            await self.chat_agent.chat(message, websocket)
        else:
            await websocket.send_json({"type": "chat", "content": "Knowledge empty, please run the research first to obtain knowledge"})

async def run_agent(task, report_type, report_source, source_urls, document_urls, tone: Tone, websocket, headers=None, config_path=""):
    """Run the agent."""
    start_time = datetime.datetime.now()
    
    # Create logs handler for this research task
    logs_handler = CustomLogsHandler(websocket, task)
    
    # Initialize researcher based on report type
    if report_type == "multi_agents":
        report = await run_research_task(
            query=task, 
            websocket=logs_handler,  # Use logs_handler instead of raw websocket
            stream_output=stream_output, 
            tone=tone, 
            headers=headers
        )
        report = report.get("report", "")
        
    elif report_type == ReportType.DetailedReport.value:
        researcher = DetailedReport(
            query=task,
            report_type=report_type,
            report_source=report_source,
            source_urls=source_urls,
            document_urls=document_urls,
            tone=tone,
            config_path=config_path,
            websocket=logs_handler,  # Use logs_handler instead of raw websocket
            headers=headers
        )
        report = await researcher.run()
        
    else:
        researcher = BasicReport(
            query=task,
            report_type=report_type,
            report_source=report_source,
            source_urls=source_urls,
            document_urls=document_urls,
            tone=tone,
            config_path=config_path,
            websocket=logs_handler,  # Use logs_handler instead of raw websocket
            headers=headers
        )
        report = await researcher.run()

    return report

```

---

### backend/server/server_utils.py

```python
import json
import os
import re
import time
import shutil
from typing import Dict, List, Any
from fastapi.responses import JSONResponse, FileResponse
from gpt_researcher.document.document import DocumentLoader
from backend.utils import write_md_to_pdf, write_md_to_word, write_text_to_md
from pathlib import Path
from datetime import datetime
from fastapi import HTTPException
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class CustomLogsHandler:
    """Custom handler to capture streaming logs from the research process"""
    def __init__(self, websocket, task: str):
        self.logs = []
        self.websocket = websocket
        sanitized_filename = sanitize_filename(f"task_{int(time.time())}_{task}")
        self.log_file = os.path.join("outputs", f"{sanitized_filename}.json")
        self.timestamp = datetime.now().isoformat()
        # Initialize log file with metadata
        os.makedirs("outputs", exist_ok=True)
        with open(self.log_file, 'w') as f:
            json.dump({
                "timestamp": self.timestamp,
                "events": [],
                "content": {
                    "query": "",
                    "sources": [],
                    "context": [],
                    "report": "",
                    "costs": 0.0
                }
            }, f, indent=2)

    async def send_json(self, data: Dict[str, Any]) -> None:
        """Store log data and send to websocket"""
        # Send to websocket for real-time display
        if self.websocket:
            await self.websocket.send_json(data)
            
        # Read current log file
        with open(self.log_file, 'r') as f:
            log_data = json.load(f)
            
        # Update appropriate section based on data type
        if data.get('type') == 'logs':
            log_data['events'].append({
                "timestamp": datetime.now().isoformat(),
                "type": "event",
                "data": data
            })
        else:
            # Update content section for other types of data
            log_data['content'].update(data)
            
        # Save updated log file
        with open(self.log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
        logger.debug(f"Log entry written to: {self.log_file}")


class Researcher:
    def __init__(self, query: str, report_type: str = "research_report"):
        self.query = query
        self.report_type = report_type
        # Generate unique ID for this research task
        self.research_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(query)}"
        # Initialize logs handler with research ID
        self.logs_handler = CustomLogsHandler(self.research_id)
        self.researcher = GPTResearcher(
            query=query,
            report_type=report_type,
            websocket=self.logs_handler
        )

    async def research(self) -> dict:
        """Conduct research and return paths to generated files"""
        await self.researcher.conduct_research()
        report = await self.researcher.write_report()
        
        # Generate the files
        sanitized_filename = sanitize_filename(f"task_{int(time.time())}_{self.query}")
        file_paths = await generate_report_files(report, sanitized_filename)
        
        # Get the JSON log path that was created by CustomLogsHandler
        json_relative_path = os.path.relpath(self.logs_handler.log_file)
        
        return {
            "output": {
                **file_paths,  # Include PDF, DOCX, and MD paths
                "json": json_relative_path
            }
        }

def sanitize_filename(filename: str) -> str:
    # Split into components
    prefix, timestamp, *task_parts = filename.split('_')
    task = '_'.join(task_parts)
    
    # Calculate max length for task portion
    # 255 - len("outputs/") - len("task_") - len(timestamp) - len("_.json") - safety_margin
    max_task_length = 255 - 8 - 5 - 10 - 6 - 10  # ~216 chars for task
    
    # Truncate task if needed
    truncated_task = task[:max_task_length] if len(task) > max_task_length else task
    
    # Reassemble and clean the filename
    sanitized = f"{prefix}_{timestamp}_{truncated_task}"
    return re.sub(r"[^\w\s-]", "", sanitized).strip()


async def handle_start_command(websocket, data: str, manager):
    json_data = json.loads(data[6:])
    task, report_type, source_urls, document_urls, tone, headers, report_source = extract_command_data(json_data)
    
    # ... logging setup ...

    report = await manager.start_streaming(
        task, 
        report_type, 
        report_source, 
        source_urls, 
        document_urls,
        tone, 
        websocket,
        headers
    )
    report = str(report)
    file_paths = await generate_report_files(report, sanitize_filename(f"task_{int(time.time())}_{task}"))
    # Add JSON log path to file_paths
    file_paths["json"] = os.path.relpath(self.logs_handler.log_file)
    await send_file_paths(websocket, file_paths)


async def handle_human_feedback(data: str):
    feedback_data = json.loads(data[14:])  # Remove "human_feedback" prefix
    print(f"Received human feedback: {feedback_data}")
    # TODO: Add logic to forward the feedback to the appropriate agent or update the research state

async def handle_chat(websocket, data: str, manager):
    json_data = json.loads(data[4:])
    print(f"Received chat message: {json_data.get('message')}")
    await manager.chat(json_data.get("message"), websocket)

async def generate_report_files(report: str, filename: str) -> Dict[str, str]:
    pdf_path = await write_md_to_pdf(report, filename)
    docx_path = await write_md_to_word(report, filename)
    md_path = await write_text_to_md(report, filename)
    return {"pdf": pdf_path, "docx": docx_path, "md": md_path}


async def send_file_paths(websocket, file_paths: Dict[str, str]):
    await websocket.send_json({"type": "path", "output": file_paths})


def get_config_dict(
    langchain_api_key: str, openai_api_key: str, tavily_api_key: str,
    google_api_key: str, google_cx_key: str, bing_api_key: str,
    searchapi_api_key: str, serpapi_api_key: str, serper_api_key: str, searx_url: str
) -> Dict[str, str]:
    return {
        "LANGCHAIN_API_KEY": langchain_api_key or os.getenv("LANGCHAIN_API_KEY", ""),
        "OPENAI_API_KEY": openai_api_key or os.getenv("OPENAI_API_KEY", ""),
        "TAVILY_API_KEY": tavily_api_key or os.getenv("TAVILY_API_KEY", ""),
        "GOOGLE_API_KEY": google_api_key or os.getenv("GOOGLE_API_KEY", ""),
        "GOOGLE_CX_KEY": google_cx_key or os.getenv("GOOGLE_CX_KEY", ""),
        "BING_API_KEY": bing_api_key or os.getenv("BING_API_KEY", ""),
        "SEARCHAPI_API_KEY": searchapi_api_key or os.getenv("SEARCHAPI_API_KEY", ""),
        "SERPAPI_API_KEY": serpapi_api_key or os.getenv("SERPAPI_API_KEY", ""),
        "SERPER_API_KEY": serper_api_key or os.getenv("SERPER_API_KEY", ""),
        "SEARX_URL": searx_url or os.getenv("SEARX_URL", ""),
        "LANGCHAIN_TRACING_V2": os.getenv("LANGCHAIN_TRACING_V2", "true"),
        "DOC_PATH": os.getenv("DOC_PATH", "./my-docs"),
        "RETRIEVER": os.getenv("RETRIEVER", ""),
        "EMBEDDING_MODEL": os.getenv("OPENAI_EMBEDDING_MODEL", "")
    }


def update_environment_variables(config: Dict[str, str]):
    for key, value in config.items():
        os.environ[key] = value


async def handle_file_upload(file, DOC_PATH: str) -> Dict[str, str]:
    file_path = os.path.join(DOC_PATH, os.path.basename(file.filename))
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    print(f"File uploaded to {file_path}")

    document_loader = DocumentLoader(DOC_PATH)
    await document_loader.load()

    return {"filename": file.filename, "path": file_path}


async def handle_file_deletion(filename: str, DOC_PATH: str) -> JSONResponse:
    file_path = os.path.join(DOC_PATH, os.path.basename(filename))
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"File deleted: {file_path}")
        return JSONResponse(content={"message": "File deleted successfully"})
    else:
        print(f"File not found: {file_path}")
        return JSONResponse(status_code=404, content={"message": "File not found"})


async def execute_multi_agents(manager) -> Any:
    websocket = manager.active_connections[0] if manager.active_connections else None
    if websocket:
        report = await run_research_task("Is AI in a hype cycle?", websocket, stream_output)
        return {"report": report}
    else:
        return JSONResponse(status_code=400, content={"message": "No active WebSocket connection"})


async def handle_websocket_communication(websocket, manager):
    while True:
        data = await websocket.receive_text()
        if data.startswith("start"):
            await handle_start_command(websocket, data, manager)
        elif data.startswith("human_feedback"):
            await handle_human_feedback(data)
        elif data.startswith("chat"):
            await handle_chat(websocket, data, manager)
        else:
            print("Error: Unknown command or not enough parameters provided.")


def extract_command_data(json_data: Dict) -> tuple:
    return (
        json_data.get("task"),
        json_data.get("report_type"),
        json_data.get("source_urls"),
        json_data.get("document_urls"),
        json_data.get("tone"),
        json_data.get("headers", {}),
        json_data.get("report_source")
    )

```

---

## Multi-Agent System

### multi_agents/agent.py

```python
from multi_agents.agents import ChiefEditorAgent

chief_editor = ChiefEditorAgent({
  "query": "Is AI in a hype cycle?",
  "max_sections": 3,
  "follow_guidelines": False,
  "model": "gpt-4o",
  "guidelines": [
    "The report MUST be written in APA format",
    "Each sub section MUST include supporting sources using hyperlinks. If none exist, erase the sub section or rewrite it to be a part of the previous section",
    "The report MUST be written in spanish"
  ],
  "verbose": False
}, websocket=None, stream_output=None)
graph = chief_editor.init_research_team()
graph = graph.compile()
```

---

### multi_agents/agents/browser.py
*File not found*

### multi_agents/agents/editor.py

```python
from datetime import datetime
import asyncio
from typing import Dict, List, Optional

from langgraph.graph import StateGraph, END

from .utils.views import print_agent_output
from .utils.llms import call_model
from ..memory.draft import DraftState
from . import ResearchAgent, ReviewerAgent, ReviserAgent


class EditorAgent:
    """Agent responsible for editing and managing code."""

    def __init__(self, websocket=None, stream_output=None, headers=None):
        self.websocket = websocket
        self.stream_output = stream_output
        self.headers = headers or {}

    async def plan_research(self, research_state: Dict[str, any]) -> Dict[str, any]:
        """
        Plan the research outline based on initial research and task parameters.

        :param research_state: Dictionary containing research state information
        :return: Dictionary with title, date, and planned sections
        """
        initial_research = research_state.get("initial_research")
        task = research_state.get("task")
        include_human_feedback = task.get("include_human_feedback")
        human_feedback = research_state.get("human_feedback")
        max_sections = task.get("max_sections")

        prompt = self._create_planning_prompt(
            initial_research, include_human_feedback, human_feedback, max_sections)

        print_agent_output(
            "Planning an outline layout based on initial research...", agent="EDITOR")
        plan = await call_model(
            prompt=prompt,
            model=task.get("model"),
            response_format="json",
        )

        return {
            "title": plan.get("title"),
            "date": plan.get("date"),
            "sections": plan.get("sections"),
        }

    async def run_parallel_research(self, research_state: Dict[str, any]) -> Dict[str, List[str]]:
        """
        Execute parallel research tasks for each section.

        :param research_state: Dictionary containing research state information
        :return: Dictionary with research results
        """
        agents = self._initialize_agents()
        workflow = self._create_workflow()
        chain = workflow.compile()

        queries = research_state.get("sections")
        title = research_state.get("title")

        self._log_parallel_research(queries)

        final_drafts = [
            chain.ainvoke(self._create_task_input(
                research_state, query, title))
            for query in queries
        ]
        research_results = [
            result["draft"] for result in await asyncio.gather(*final_drafts)
        ]

        return {"research_data": research_results}

    def _create_planning_prompt(self, initial_research: str, include_human_feedback: bool,
                                human_feedback: Optional[str], max_sections: int) -> List[Dict[str, str]]:
        """Create the prompt for research planning."""
        return [
            {
                "role": "system",
                "content": "You are a research editor. Your goal is to oversee the research project "
                           "from inception to completion. Your main task is to plan the article section "
                           "layout based on an initial research summary.\n ",
            },
            {
                "role": "user",
                "content": self._format_planning_instructions(initial_research, include_human_feedback,
                                                              human_feedback, max_sections),
            },
        ]

    def _format_planning_instructions(self, initial_research: str, include_human_feedback: bool,
                                      human_feedback: Optional[str], max_sections: int) -> str:
        """Format the instructions for research planning."""
        today = datetime.now().strftime('%d/%m/%Y')
        feedback_instruction = (
            f"Human feedback: {human_feedback}. You must plan the sections based on the human feedback."
            if include_human_feedback and human_feedback and human_feedback != 'no'
            else ''
        )

        return f"""Today's date is {today}
                   Research summary report: '{initial_research}'
                   {feedback_instruction}
                   \nYour task is to generate an outline of sections headers for the research project
                   based on the research summary report above.
                   You must generate a maximum of {max_sections} section headers.
                   You must focus ONLY on related research topics for subheaders and do NOT include introduction, conclusion and references.
                   You must return nothing but a JSON with the fields 'title' (str) and 
                   'sections' (maximum {max_sections} section headers) with the following structure:
                   '{{title: string research title, date: today's date, 
                   sections: ['section header 1', 'section header 2', 'section header 3' ...]}}'."""

    def _initialize_agents(self) -> Dict[str, any]:
        """Initialize the research, reviewer, and reviser skills."""
        return {
            "research": ResearchAgent(self.websocket, self.stream_output, self.headers),
            "reviewer": ReviewerAgent(self.websocket, self.stream_output, self.headers),
            "reviser": ReviserAgent(self.websocket, self.stream_output, self.headers),
        }

    def _create_workflow(self) -> StateGraph:
        """Create the workflow for the research process."""
        agents = self._initialize_agents()
        workflow = StateGraph(DraftState)

        workflow.add_node("researcher", agents["research"].run_depth_research)
        workflow.add_node("reviewer", agents["reviewer"].run)
        workflow.add_node("reviser", agents["reviser"].run)

        workflow.set_entry_point("researcher")
        workflow.add_edge("researcher", "reviewer")
        workflow.add_edge("reviser", "reviewer")
        workflow.add_conditional_edges(
            "reviewer",
            lambda draft: "accept" if draft["review"] is None else "revise",
            {"accept": END, "revise": "reviser"},
        )

        return workflow

    def _log_parallel_research(self, queries: List[str]) -> None:
        """Log the start of parallel research tasks."""
        if self.websocket and self.stream_output:
            asyncio.create_task(self.stream_output(
                "logs",
                "parallel_research",
                f"Running parallel research for the following queries: {queries}",
                self.websocket,
            ))
        else:
            print_agent_output(
                f"Running the following research tasks in parallel: {queries}...",
                agent="EDITOR",
            )

    def _create_task_input(self, research_state: Dict[str, any], query: str, title: str) -> Dict[str, any]:
        """Create the input for a single research task."""
        return {
            "task": research_state.get("task"),
            "topic": query,
            "title": title,
            "headers": self.headers,
        }

```

---

### multi_agents/agents/researcher.py

```python
from gpt_researcher import GPTResearcher
from colorama import Fore, Style
from .utils.views import print_agent_output


class ResearchAgent:
    def __init__(self, websocket=None, stream_output=None, tone=None, headers=None):
        self.websocket = websocket
        self.stream_output = stream_output
        self.headers = headers or {}
        self.tone = tone

    async def research(self, query: str, research_report: str = "research_report",
                       parent_query: str = "", verbose=True, source="web", tone=None, headers=None):
        # Initialize the researcher
        researcher = GPTResearcher(query=query, report_type=research_report, parent_query=parent_query,
                                   verbose=verbose, report_source=source, tone=tone, websocket=self.websocket, headers=self.headers)
        # Conduct research on the given query
        await researcher.conduct_research()
        # Write the report
        report = await researcher.write_report()

        return report

    async def run_subtopic_research(self, parent_query: str, subtopic: str, verbose: bool = True, source="web", headers=None):
        try:
            report = await self.research(parent_query=parent_query, query=subtopic,
                                         research_report="subtopic_report", verbose=verbose, source=source, tone=self.tone, headers=None)
        except Exception as e:
            print(f"{Fore.RED}Error in researching topic {subtopic}: {e}{Style.RESET_ALL}")
            report = None
        return {subtopic: report}

    async def run_initial_research(self, research_state: dict):
        task = research_state.get("task")
        query = task.get("query")
        source = task.get("source", "web")

        if self.websocket and self.stream_output:
            await self.stream_output("logs", "initial_research", f"Running initial research on the following query: {query}", self.websocket)
        else:
            print_agent_output(f"Running initial research on the following query: {query}", agent="RESEARCHER")
        return {"task": task, "initial_research": await self.research(query=query, verbose=task.get("verbose"),
                                                                      source=source, tone=self.tone, headers=self.headers)}

    async def run_depth_research(self, draft_state: dict):
        task = draft_state.get("task")
        topic = draft_state.get("topic")
        parent_query = task.get("query")
        source = task.get("source", "web")
        verbose = task.get("verbose")
        if self.websocket and self.stream_output:
            await self.stream_output("logs", "depth_research", f"Running in depth research on the following report topic: {topic}", self.websocket)
        else:
            print_agent_output(f"Running in depth research on the following report topic: {topic}", agent="RESEARCHER")
        research_draft = await self.run_subtopic_research(parent_query=parent_query, subtopic=topic,
                                                          verbose=verbose, source=source, headers=self.headers)
        return {"draft": research_draft}
```

---

### multi_agents/agents/reviewer.py

```python
from .utils.views import print_agent_output
from .utils.llms import call_model

TEMPLATE = """You are an expert research article reviewer. \
Your goal is to review research drafts and provide feedback to the reviser only based on specific guidelines. \
"""


class ReviewerAgent:
    def __init__(self, websocket=None, stream_output=None, headers=None):
        self.websocket = websocket
        self.stream_output = stream_output
        self.headers = headers or {}

    async def review_draft(self, draft_state: dict):
        """
        Review a draft article
        :param draft_state:
        :return:
        """
        task = draft_state.get("task")
        guidelines = "- ".join(guideline for guideline in task.get("guidelines"))
        revision_notes = draft_state.get("revision_notes")

        revise_prompt = f"""The reviser has already revised the draft based on your previous review notes with the following feedback:
{revision_notes}\n
Please provide additional feedback ONLY if critical since the reviser has already made changes based on your previous feedback.
If you think the article is sufficient or that non critical revisions are required, please aim to return None.
"""

        review_prompt = f"""You have been tasked with reviewing the draft which was written by a non-expert based on specific guidelines.
Please accept the draft if it is good enough to publish, or send it for revision, along with your notes to guide the revision.
If not all of the guideline criteria are met, you should send appropriate revision notes.
If the draft meets all the guidelines, please return None.
{revise_prompt if revision_notes else ""}

Guidelines: {guidelines}\nDraft: {draft_state.get("draft")}\n
"""
        prompt = [
            {"role": "system", "content": TEMPLATE},
            {"role": "user", "content": review_prompt},
        ]

        response = await call_model(prompt, model=task.get("model"))

        if task.get("verbose"):
            if self.websocket and self.stream_output:
                await self.stream_output(
                    "logs",
                    "review_feedback",
                    f"Review feedback is: {response}...",
                    self.websocket,
                )
            else:
                print_agent_output(
                    f"Review feedback is: {response}...", agent="REVIEWER"
                )

        if "None" in response:
            return None
        return response

    async def run(self, draft_state: dict):
        task = draft_state.get("task")
        guidelines = task.get("guidelines")
        to_follow_guidelines = task.get("follow_guidelines")
        review = None
        if to_follow_guidelines:
            print_agent_output(f"Reviewing draft...", agent="REVIEWER")

            if task.get("verbose"):
                print_agent_output(
                    f"Following guidelines {guidelines}...", agent="REVIEWER"
                )

            review = await self.review_draft(draft_state)
        else:
            print_agent_output(f"Ignoring guidelines...", agent="REVIEWER")
        return {"review": review}

```

---

### multi_agents/agents/writer.py

```python
from datetime import datetime
import json5 as json
from .utils.views import print_agent_output
from .utils.llms import call_model

sample_json = """
{
  "table_of_contents": A table of contents in markdown syntax (using '-') based on the research headers and subheaders,
  "introduction": An indepth introduction to the topic in markdown syntax and hyperlink references to relevant sources,
  "conclusion": A conclusion to the entire research based on all research data in markdown syntax and hyperlink references to relevant sources,
  "sources": A list with strings of all used source links in the entire research data in markdown syntax and apa citation format. For example: ['-  Title, year, Author [source url](source)', ...]
}
"""


class WriterAgent:
    def __init__(self, websocket=None, stream_output=None, headers=None):
        self.websocket = websocket
        self.stream_output = stream_output
        self.headers = headers

    def get_headers(self, research_state: dict):
        return {
            "title": research_state.get("title"),
            "date": "Date",
            "introduction": "Introduction",
            "table_of_contents": "Table of Contents",
            "conclusion": "Conclusion",
            "references": "References",
        }

    async def write_sections(self, research_state: dict):
        query = research_state.get("title")
        data = research_state.get("research_data")
        task = research_state.get("task")
        follow_guidelines = task.get("follow_guidelines")
        guidelines = task.get("guidelines")

        prompt = [
            {
                "role": "system",
                "content": "You are a research writer. Your sole purpose is to write a well-written "
                "research reports about a "
                "topic based on research findings and information.\n ",
            },
            {
                "role": "user",
                "content": f"Today's date is {datetime.now().strftime('%d/%m/%Y')}\n."
                f"Query or Topic: {query}\n"
                f"Research data: {str(data)}\n"
                f"Your task is to write an in depth, well written and detailed "
                f"introduction and conclusion to the research report based on the provided research data. "
                f"Do not include headers in the results.\n"
                f"You MUST include any relevant sources to the introduction and conclusion as markdown hyperlinks -"
                f"For example: 'This is a sample text. ([url website](url))'\n\n"
                f"{f'You must follow the guidelines provided: {guidelines}' if follow_guidelines else ''}\n"
                f"You MUST return nothing but a JSON in the following format (without json markdown):\n"
                f"{sample_json}\n\n",
            },
        ]

        response = await call_model(
            prompt,
            task.get("model"),
            response_format="json",
        )
        return response

    async def revise_headers(self, task: dict, headers: dict):
        prompt = [
            {
                "role": "system",
                "content": """You are a research writer. 
Your sole purpose is to revise the headers data based on the given guidelines.""",
            },
            {
                "role": "user",
                "content": f"""Your task is to revise the given headers JSON based on the guidelines given.
You are to follow the guidelines but the values should be in simple strings, ignoring all markdown syntax.
You must return nothing but a JSON in the same format as given in headers data.
Guidelines: {task.get("guidelines")}\n
Headers Data: {headers}\n
""",
            },
        ]

        response = await call_model(
            prompt,
            task.get("model"),
            response_format="json",
        )
        return {"headers": response}

    async def run(self, research_state: dict):
        if self.websocket and self.stream_output:
            await self.stream_output(
                "logs",
                "writing_report",
                f"Writing final research report based on research data...",
                self.websocket,
            )
        else:
            print_agent_output(
                f"Writing final research report based on research data...",
                agent="WRITER",
            )

        research_layout_content = await self.write_sections(research_state)

        if research_state.get("task").get("verbose"):
            if self.websocket and self.stream_output:
                research_layout_content_str = json.dumps(
                    research_layout_content, indent=2
                )
                await self.stream_output(
                    "logs",
                    "research_layout_content",
                    research_layout_content_str,
                    self.websocket,
                )
            else:
                print_agent_output(research_layout_content, agent="WRITER")

        headers = self.get_headers(research_state)
        if research_state.get("task").get("follow_guidelines"):
            if self.websocket and self.stream_output:
                await self.stream_output(
                    "logs",
                    "rewriting_layout",
                    "Rewriting layout based on guidelines...",
                    self.websocket,
                )
            else:
                print_agent_output(
                    "Rewriting layout based on guidelines...", agent="WRITER"
                )
            headers = await self.revise_headers(
                task=research_state.get("task"), headers=headers
            )
            headers = headers.get("headers")

        return {**research_layout_content, "headers": headers}

```

---

### multi_agents/agents/publisher.py

```python
from .utils.file_formats import \
    write_md_to_pdf, \
    write_md_to_word, \
    write_text_to_md

from .utils.views import print_agent_output


class PublisherAgent:
    def __init__(self, output_dir: str, websocket=None, stream_output=None, headers=None):
        self.websocket = websocket
        self.stream_output = stream_output
        self.output_dir = output_dir
        self.headers = headers or {}
        
    async def publish_research_report(self, research_state: dict, publish_formats: dict):
        layout = self.generate_layout(research_state)
        await self.write_report_by_formats(layout, publish_formats)

        return layout

    def generate_layout(self, research_state: dict):
        sections = '\n\n'.join(f"{value}"
                                 for subheader in research_state.get("research_data")
                                 for key, value in subheader.items())
        references = '\n'.join(f"{reference}" for reference in research_state.get("sources"))
        headers = research_state.get("headers")
        layout = f"""# {headers.get('title')}
#### {headers.get("date")}: {research_state.get('date')}

## {headers.get("introduction")}
{research_state.get('introduction')}

## {headers.get("table_of_contents")}
{research_state.get('table_of_contents')}

{sections}

## {headers.get("conclusion")}
{research_state.get('conclusion')}

## {headers.get("references")}
{references}
"""
        return layout

    async def write_report_by_formats(self, layout:str, publish_formats: dict):
        if publish_formats.get("pdf"):
            await write_md_to_pdf(layout, self.output_dir)
        if publish_formats.get("docx"):
            await write_md_to_word(layout, self.output_dir)
        if publish_formats.get("markdown"):
            await write_text_to_md(layout, self.output_dir)

    async def run(self, research_state: dict):
        task = research_state.get("task")
        publish_formats = task.get("publish_formats")
        if self.websocket and self.stream_output:
            await self.stream_output("logs", "publishing", f"Publishing final research report based on retrieved data...", self.websocket)
        else:
            print_agent_output(output="Publishing final research report based on retrieved data...", agent="PUBLISHER")
        final_research_report = await self.publish_research_report(research_state, publish_formats)
        return {"report": final_research_report}

```

---

