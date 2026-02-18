# 🚀 Get Started – Multi-Agent Project Template

Tài liệu này hướng dẫn cách **clone, cài đặt, mở rộng** và **quy ước code** khi làm việc với repo template này.

---

## 📑 Mục lục

1. [Yêu cầu hệ thống](#1-yêu-cầu-hệ-thống)
2. [Clone & cài đặt](#2-clone--cài-đặt)
3. [Cấu hình môi trường](#3-cấu-hình-môi-trường)
4. [Cấu trúc thư mục](#4-cấu-trúc-thư-mục)
5. [Hướng dẫn mở rộng](#5-hướng-dẫn-mở-rộng)
   - 5.1 [Thêm Agent mới](#51-thêm-agent-mới)
   - 5.2 [Thêm Tool mới](#52-thêm-tool-mới)
   - 5.3 [Thêm Workflow mới](#53-thêm-workflow-mới)
   - 5.4 [Thêm LLM Provider mới](#54-thêm-llm-provider-mới)
   - 5.5 [Thêm Database mới](#55-thêm-database-mới)
   - 5.6 [Thêm API Router mới](#56-thêm-api-router-mới)
6. [Checklist khi tạo tính năng mới](#6-checklist-khi-tạo-tính-năng-mới)

---

## 1. Yêu cầu hệ thống

| Công cụ | Phiên bản tối thiểu |
|---------|-------------------|
| Python  | 3.11+             |
| pip / uv | latest           |
| Git     | 2.x+             |

---

## 2. Clone & cài đặt

```bash
# Bước 1 – Clone repo về máy
git clone <repo-url>
cd <project-name>

# Bước 2 – Tạo virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows

# Bước 3 – Cài đặt dependencies
pip install -r requirements.txt

# Bước 4 – Cấu hình biến môi trường (xem mục 3)
cp .env.example .env

# Bước 5 – Chạy server
bash start.sh
# hoặc trực tiếp:
# uvicorn main:app --reload
```

Sau khi chạy, truy cập:
- **API docs**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/health

---

## 3. Cấu hình môi trường

### File `.env`
Chứa **API keys** và **secrets** – **không commit file này lên git**.

```env
# LLM Providers – điền key của provider bạn đang dùng
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dbname

# App
APP_ENV=development       # development | staging | production
LOG_LEVEL=INFO
PORT=8000
```

### File `config/app.yaml`
Chứa **cấu hình phi-secret**: tên model, số workers, loại database, danh sách agent...  
Đây là file duy nhất bạn cần sửa khi muốn đổi model hoặc thêm agent vào workflow.

```yaml
llm:
  default_provider: "openai"
  default_model: "gpt-4o-mini"

agents:
  researcher:
    llm_provider: "openai"
    tools: ["web_search"]
```

> **Quy tắc:** Secret → `.env` | Cấu hình logic → `config/app.yaml`

---

## 4. Cấu trúc thư mục

```
.
├── main.py                          # Entry point – tạo FastAPI app
├── start.sh                         # Script khởi động server
├── requirements.txt                 # Python dependencies
├── .env.example                     # Template biến môi trường
├── config/
│   └── app.yaml                     # Cấu hình trung tâm (model, db, agents...)
├── docs/
│   └── get_started.md               # Tài liệu này
└── src/
    ├── core/                        # Toàn bộ business logic AI
    │   ├── agents/                  # Định nghĩa các AI Agent
    │   │   ├── base.py              #   └─ Abstract BaseAgent
    │   │   ├── factory.py           #   └─ AgentFactory.create(name)
    │   │   └── components/
    │   │       ├── states.py        #      └─ TypedDict AgentState
    │   │       └── nodes.py         #      └─ Node functions cho graph
    │   ├── workflows/               # Điều phối các Agent (LangGraph)
    │   │   ├── base.py              #   └─ Abstract BaseWorkflow
    │   │   ├── factory.py           #   └─ WorkflowFactory.create(name)
    │   │   └── components/
    │   │       ├── states.py        #      └─ TypedDict WorkflowState
    │   │       └── nodes.py         #      └─ Orchestration node functions
    │   ├── llm/
    │   │   └── factory.py           # LLMFactory.create(provider, model)
    │   ├── prompts/
    │   │   ├── factory.py           # PromptFactory.render(name, **vars)
    │   │   └── *.md                 # File prompt (1 file = 1 prompt)
    │   └── tools/
    │       ├── base.py              # Abstract ProjectBaseTool
    │       └── factory.py           # ToolFactory.get_tools([names])
    ├── databases/
    │   ├── base.py                  # Abstract BaseDatabase
    │   └── factory.py               # DatabaseFactory.create(type)
    ├── routers/
    │   └── __init__.py              # register_routers(app) – gắn tất cả routers
    └── utils/
        └── __init__.py              # load_config(), helpers dùng chung
```

---

## 5. Hướng dẫn mở rộng

### 5.1 Thêm Agent mới

**Bước 1** – Tạo file `src/core/agents/my_agent.py`:

```python
from langgraph.graph import StateGraph, END
from langgraph.graph.graph import CompiledGraph

from src.core.agents.base import BaseAgent
from src.core.agents.components.states import AgentState
from src.core.agents.components.nodes import node_call_llm, route_after_llm
from src.core.llm.factory import LLMFactory
from src.core.tools.factory import ToolFactory


class MyAgent(BaseAgent):
    def build_graph(self) -> CompiledGraph:
        llm = LLMFactory.create(
            provider=self.config.get("llm_provider"),
            model=self.config.get("llm_model"),
        )
        tools = ToolFactory.get_tools(self.config.get("tools", []))
        llm_with_tools = llm.bind_tools(tools)

        graph = StateGraph(AgentState)
        graph.add_node("call_llm", node_call_llm)
        graph.add_node("run_tools", node_run_tools)

        graph.set_entry_point("call_llm")
        graph.add_conditional_edges("call_llm", route_after_llm, {
            "run_tools": "run_tools",
            "__end__": END,
        })
        graph.add_edge("run_tools", "call_llm")

        return graph.compile()
```

**Bước 2** – Đăng ký vào `src/core/agents/factory.py`:

```python
from src.core.agents.my_agent import MyAgent

AGENT_REGISTRY: dict[str, type[BaseAgent]] = {
    "my_agent": MyAgent,   # ← thêm dòng này
}
```

**Bước 3** – Thêm config vào `config/app.yaml`:

```yaml
agents:
  my_agent:
    llm_provider: "openai"
    llm_model: "gpt-4o-mini"
    tools: ["web_search"]
```

---

### 5.2 Thêm Tool mới

**Bước 1** – Tạo file `src/core/tools/my_tool.py`:

```python
from src.core.tools.base import ProjectBaseTool


class MyTool(ProjectBaseTool):
    name: str = "my_tool"
    description: str = "Mô tả rõ ràng để LLM biết khi nào dùng tool này."

    async def _arun(self, query: str) -> str:
        # Implement logic
        result = f"Kết quả cho: {query}"
        return result

    def _run(self, query: str) -> str:
        raise NotImplementedError("Dùng _arun")
```

**Bước 2** – Đăng ký vào `src/core/tools/factory.py`:

```python
from src.core.tools.my_tool import MyTool

TOOL_REGISTRY: dict[str, BaseTool] = {
    "my_tool": MyTool(),   # ← thêm dòng này
}
```

---

### 5.3 Thêm Workflow mới

**Bước 1** – Tạo file `src/core/workflows/my_workflow.py`:

```python
from langgraph.graph import StateGraph, END
from langgraph.graph.graph import CompiledGraph

from src.core.workflows.base import BaseWorkflow
from src.core.workflows.components.states import WorkflowState
from src.core.workflows.components.nodes import node_initialize, route_by_next


class MyWorkflow(BaseWorkflow):
    def build_graph(self) -> CompiledGraph:
        graph = StateGraph(WorkflowState)

        graph.add_node("initialize", node_initialize)
        graph.add_node("supervisor", node_run_agent("supervisor"))
        graph.add_node("researcher", node_run_agent("researcher"))

        graph.set_entry_point("initialize")
        graph.add_conditional_edges("supervisor", route_by_next, {
            "researcher": "researcher",
            "FINISH": END,
        })
        graph.add_edge("researcher", "supervisor")

        return graph.compile()
```

**Bước 2** – Đăng ký vào `src/core/workflows/factory.py`:

```python
from src.core.workflows.my_workflow import MyWorkflow

WORKFLOW_REGISTRY: dict[str, type[BaseWorkflow]] = {
    "my_workflow": MyWorkflow,   # ← thêm dòng này
}
```

**Bước 3** – Thêm config vào `config/app.yaml`:

```yaml
workflows:
  default: "my_workflow"
  my_workflow:
    agents: ["supervisor", "researcher"]
    checkpointer: true
```

---

### 5.4 Thêm LLM Provider mới

Mở `src/core/llm/factory.py`, thêm `case` mới vào hàm `create()`:

```python
case "my_provider":
    from langchain_myprovider import ChatMyProvider
    return ChatMyProvider(model=model, temperature=temperature, **kwargs)
```

Thêm vào `config/app.yaml`:

```yaml
llm:
  providers:
    my_provider:
      model: "my-model-name"
```

---

### 5.5 Thêm Database mới

**Bước 1** – Tạo `src/databases/my_database.py`:

```python
from src.databases.base import BaseDatabase


class MyDatabase(BaseDatabase):
    async def connect(self) -> None:
        # Khởi tạo connection pool
        self._client = await create_connection(self.config["url"])
        self._connected = True

    async def disconnect(self) -> None:
        await self._client.close()
        self._connected = False

    async def execute(self, query: str, params: dict | None = None):
        return await self._client.run(query, params or {})
```

**Bước 2** – Đăng ký vào `src/databases/factory.py`:

```python
from src.databases.my_database import MyDatabase

DATABASE_REGISTRY = {
    "my_db": MyDatabase,   # ← thêm dòng này
}
```

---

### 5.6 Thêm API Router mới

**Bước 1** – Tạo `src/routers/chat.py`:

```python
from fastapi import APIRouter
from src.core.workflows.factory import WorkflowFactory

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/")
async def chat(payload: dict):
    workflow = WorkflowFactory.create()
    result = await workflow.ainvoke({"messages": [payload["message"]]})
    return {"answer": result["final_answer"]}
```

**Bước 2** – Đăng ký vào `src/routers/__init__.py`:

```python
from fastapi import FastAPI
from src.routers.chat import router as chat_router


def register_routers(app: FastAPI) -> None:
    app.include_router(chat_router)
    # thêm router khác ở đây
```

---


## 6. Checklist khi tạo tính năng mới

Trước khi tạo Pull Request, hãy đảm bảo:

- [ ] **Class** kế thừa đúng abstract base class (`BaseAgent`, `BaseWorkflow`, `BaseTool`, `BaseDatabase`)
- [ ] **Đăng ký** vào Registry tương ứng trong `factory.py`
- [ ] **Config** được thêm vào `config/app.yaml` (không hardcode)
- [ ] **Secret / API key** được thêm vào `.env.example` (không vào `app.yaml`)
- [ ] **Prompt** được lưu vào file `.md` riêng (không hardcode trong Python)
- [ ] **State** được định nghĩa bằng `TypedDict` (không dùng `dict` tự do)
- [ ] **Node function** và I/O đều là `async def`
- [ ] Chạy thử `bash start.sh` và kiểm tra `/docs` không có lỗi
