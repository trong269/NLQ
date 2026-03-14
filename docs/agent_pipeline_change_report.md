# Agent Pipeline Change Report

Ngày cập nhật: 2026-03-14

## 1) Tóm tắt thay đổi theo commit

### d06ace7 feat(all): init, base, factory, abstract class,...
- Khởi tạo khung dự án: base/factory cho agents, workflows, tools, prompts.
- Chưa có pipeline agent nghiệp vụ cụ thể.

### 02eadb6 [feat] adding guardrail agent
- Thêm Guardrail Agent và test router.
- Thêm prompt scan injection và tool `prompt_injection`.
- Cập nhật state/node dùng cho guardrail.
- Cập nhật config agent `guardrail` trong `config/app.yaml`.

### 27bdb48 feat: add schema linking agent for NLQ-SQL pipeline
- Thêm `SchemaLinkingAgent`.
- Đăng ký agent mới trong `AgentFactory`.
- Thêm prompt `schema_linking.md`.
- Cập nhật config `schema_linking_agent` trong `config/app.yaml`.

### b41a9d4 update config/app.yaml
- Điều chỉnh cấu hình app/agent liên quan pipeline (không thêm agent mới).

## 2) Trạng thái pipeline agent hiện tại (code thực tế)

## 2.1 Agent đang có trong registry
- `guardrail`
- `schema_linking_agent`

Nguồn: `src/core/agents/factory.py`

## 2.2 Guardrail pipeline hiện tại
- Graph: `initialize -> scan_nl -> END`
- Input chính: `nl_input`
- Kết quả:
  - `PASS`
  - `HARD_BLOCK` (kèm `block_reason` + `message` tiếng Việt)
- LOW confidence injection: không chặn, chỉ thêm `warnings`.

Nguồn:
- `src/core/agents/guardrail_agent.py`
- `src/core/agents/components/nodes.py`
- `src/core/agents/components/states.py`
- `src/core/tools/prompt_injection.py`

## 2.3 Schema Linking pipeline hiện tại
- Graph: 1 node `call_llm`, sau đó `END`.
- Hỗ trợ 2 dạng input:
  - `messages` (workflow generic)
  - `user_query` + `database_schema` (direct invoke)
- Vai trò: chọn table/column liên quan, KHÔNG generate SQL.

Nguồn:
- `src/core/agents/schema_linking_agent.py`
- `src/core/prompts/schema_linking.md`

## 2.4 Workflow orchestration hiện tại
- `WORKFLOW_REGISTRY` đang rỗng.
- `workflows.default` trong config đang `null`.
- Nghĩa là chưa có workflow tổng điều phối nhiều agent ở runtime.

Nguồn:
- `src/core/workflows/factory.py`
- `config/app.yaml`

## 2.5 API/Router hiện tại
- Đang expose test endpoint cho guardrail:
  - `POST /test/guardrail`
  - `POST /test/guardrail/batch`
- Chưa có endpoint orchestration pipeline đầy đủ (guardrail -> schema linking -> ...).

Nguồn:
- `src/routers/test_guardrail.py`
- `src/routers/__init__.py`

## 3) Delta quan trọng so với hướng NLQ->SQL đầy đủ

- Đã có 2 agent đơn lẻ (`guardrail`, `schema_linking_agent`), nhưng chưa được nối thành workflow chính.
- Guardrail hiện chỉ quét NL input (đúng với scope hiện tại), chưa có các phase SQL guardrail cũ.
- Tool registry hiện rỗng, `SchemaLinkingAgent` chạy LLM-only (không tool).

## 4) Kết luận nhanh

Pipeline agent đã chuyển từ giai đoạn chỉ có guardrail sang giai đoạn có thêm schema linking, nhưng orchestration layer vẫn chưa bật. Hệ thống hiện phù hợp để test từng agent độc lập; chưa sẵn sàng chạy end-to-end workflow NLQ->SQL nhiều bước.
