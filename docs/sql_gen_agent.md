# SQL Generation Agent

Agent này là bước cuối trong pipeline NLQ → SQL. Nhiệm vụ của nó là nhận câu hỏi tự nhiên cùng schema context đã được chọn lọc, sinh câu SQL phù hợp, thực thi SQL đó trên database, rồi tự retry nếu truy vấn lỗi.

---

## Vị trí trong hệ thống

```text
User NL input
  → Guardrail Agent
  → Schema Linking Agent
  → SQL Generation Agent
  → SQL result / failed
```

---

## Pipeline

```text
initialize → generate → execute
                ↑         ↓
                └─ retry ─┘

execute → success → END
execute → failed  → END
```

| Node | Mô tả |
|---|---|
| `initialize` | Reset toàn bộ output fields trước mỗi lần chạy agent |
| `generate` | Gọi LLM để sinh SQL từ `nl_input` và `schema_context` |
| `execute` | Chạy SQL trên database đã inject qua `configurable.db` |

---

## Input / Output

**Input chính:**

```json
{
  "nl_input": "Top 5 customers by revenue",
  "schema_context": "tables, columns, joins..."
}
```

**Output** (`SqlGenState`):

| Field | Kiểu | Mô tả |
|---|---|---|
| `nl_input` | `str` | Câu hỏi gốc của user |
| `schema_context` | `str` | Context schema do schema linking trả về |
| `sql_query` | `str` | SQL do model sinh ra |
| `sql_error` | `str` | Lỗi DB của lần execute gần nhất |
| `retry_count` | `int` | Số lần execute lỗi |
| `status` | `str` | `running`, `success`, hoặc `failed` |
| `result` | `list` | Kết quả query khi thành công |
| `error_message` | `str` | Thông báo cuối khi hết retry |

---

## Logic retry

- Lần đầu, `generate` dùng `nl_input` + `schema_context` để tạo SQL.
- Nếu `execute` lỗi, agent tăng `retry_count` và đưa lại cho `generate`:
  - câu SQL vừa thử
  - lỗi DB vừa nhận
- Model sẽ tự sửa SQL ở vòng tiếp theo.
- Khi `retry_count` đạt ngưỡng `agents.sql_gen_agent.max_retries` trong config, agent dừng với `status = "failed"`.

Ví dụ thông báo cuối:

> `Không thể thực thi SQL sau 2 lần thử. Lỗi: <db_error>`

---

## Các file liên quan

| File | Vai trò |
|---|---|
| `src/core/agents/sql_gen_agent.py` | Định nghĩa graph và retry loop |
| `src/core/agents/components/nodes.py` | `node_sql_gen_initialize`, `node_sql_gen_generate`, `node_sql_gen_execute` |
| `src/core/agents/components/states.py` | `SqlGenState` TypedDict |
| `src/core/prompts/sql_gen_system.md` | System prompt cho SQL generation |
| `src/core/prompts/sql_gen_human.md` | Human prompt template |
| `src/core/workflows/nlq_workflow.py` | Gọi SQL Generation Agent trong workflow tổng |

---

## Sử dụng trực tiếp

```python
from src.core.agents.factory import AgentFactory

agent = AgentFactory.create("sql_gen_agent")
result = await agent.ainvoke(
    {
        "nl_input": "Top 5 customers by revenue",
        "schema_context": schema_context,
    },
    config={"configurable": {"db": db}},
)

# result["status"]        -> "success" | "failed"
# result["sql_query"]     -> str
# result["result"]        -> list[dict]
# result["error_message"] -> str
```

---

## Config (`config/app.yaml`)

```yaml
agents:
  sql_gen_agent:
    llm_provider: "mega_llm"
    llm_model: "openai-gpt-oss-120b"
    max_retries: 2
```

`max_retries` được đọc động từ config tại runtime, không hardcode trong node execute.