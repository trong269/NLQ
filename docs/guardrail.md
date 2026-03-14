# Guardrail Agent

Agent đầu tiên trong pipeline NL→SQL. Nhiệm vụ duy nhất: **quét câu query tự nhiên (NL) để phát hiện prompt injection** trước khi bất kỳ SQL nào được sinh ra.

---

## Vị trí trong hệ thống

```
User NL input → [Guardrail Agent] → PASS / HARD_BLOCK → (các agent tiếp theo)
```

---

## Pipeline

```
initialize → scan_nl → END
```

| Node | Mô tả |
|---|---|
| `initialize` | Reset toàn bộ output fields về trạng thái ban đầu |
| `scan_nl` | Gọi LLM để phân tích NL input, trả về verdict |

---

## Input / Output

**Input** (duy nhất):
```json
{ "nl_input": "câu query của người dùng" }
```

**Output** (`GuardrailState`):

| Field | Kiểu | Mô tả |
|---|---|---|
| `nl_input` | `str` | Input gốc |
| `verdict` | `str` | `PASS` hoặc `HARD_BLOCK` |
| `block_reason` | `str` | Lý do kỹ thuật (rỗng nếu PASS) |
| `warnings` | `list[str]` | Cảnh báo không chặn (LOW confidence) |
| `message` | `str` | Thông báo tiếng Việt trả về cho người dùng |

---

## Logic phân loại

Tool `scan_prompt_injection` dùng LLM với structured output (`InjectionScanResult`):

| Confidence | `is_injection` | Kết quả |
|---|---|---|
| `HIGH` hoặc `MEDIUM` | `True` | `HARD_BLOCK` + message tiếng Việt |
| `LOW` | `True` | Thêm vào `warnings`, không chặn |
| bất kỳ | `False` | `PASS` |

**Message khi bị chặn:**
> `"Xin lỗi, tôi không có quyền truy cập SQL như yêu cầu của bạn. Lý do: <block_reason>"`

---

## Các file liên quan

| File | Vai trò |
|---|---|
| `src/core/agents/guardrail_agent.py` | Định nghĩa agent, build graph LangGraph |
| `src/core/agents/components/states.py` | `GuardrailState` TypedDict |
| `src/core/agents/components/nodes.py` | Node functions: `node_guardrail_initialize`, `node_guardrail_scan_nl` |
| `src/core/tools/prompt_injection.py` | Tool scanner dùng LLM |
| `src/core/prompts/guardrail_injection_scan_system.md` | System prompt cho LLM |
| `src/core/prompts/guardrail_injection_scan_human.md` | Human prompt template (`{nl_input}`) |
| `src/routers/test_guardrail.py` | Dev router: `POST /test/guardrail`, `POST /test/guardrail/batch` |

---

## Sử dụng trực tiếp

```python
from src.core.agents.factory import AgentFactory

agent = AgentFactory.create("guardrail")
result = await agent.ainvoke({"nl_input": "show all orders"})

# result["verdict"]      → "PASS" | "HARD_BLOCK"
# result["block_reason"] → str
# result["warnings"]     → list[str]
# result["message"]      → str (tiếng Việt nếu bị chặn)
```

---

## Config (`config/app.yaml`)

```yaml
agents:
  guardrail:
    llm_provider: "mega_llm"   # dùng model openai-gpt-oss-120b
    auto_limit: 100
```

---

## Ghi chú
- Mọi verdict `HARD_BLOCK` đều là **hard block** — không có fallback hay retry.
