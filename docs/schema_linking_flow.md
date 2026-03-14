# Schema Linking Flow

Tài liệu này mô tả ngắn gọn cách `SchemaLinkingAgent` hoạt động trong hệ thống NLQ->SQL.

## Mục tiêu

`SchemaLinkingAgent` dùng để ánh xạ câu hỏi ngôn ngữ tự nhiên sang tập bảng/cột liên quan.

Agent này:
- Chỉ chọn schema element (table/column) liên quan.
- Không sinh SQL.
- Trả về reasoning để agent downstream dùng tiếp.

## Vị trí trong pipeline

Luồng mong muốn (khi có orchestration đầy đủ):

`User NL input -> Guardrail -> Schema Linking -> SQL Generation`

Trạng thái hiện tại:
- Guardrail và Schema Linking đã có riêng lẻ.
- Workflow tổng chưa bật (`workflows.default: null`).

## Luồng thực thi bên trong SchemaLinkingAgent

### 1) Nhận input

Agent hỗ trợ 2 kiểu gọi:

1. Kiểu chuyên dụng:
```json
{
  "user_query": "Which customers placed orders in 2024?",
  "database_schema": "...schema text..."
}
```

2. Kiểu generic (workflow-compatible):
```json
{
  "messages": ["..."]
}
```

### 2) Tiền xử lý input

- Nếu có `user_query` + `database_schema`:
  - Render prompt `schema_linking.md` với 2 biến này.
  - Tạo `SystemMessage` (chứa prompt đã render) + `HumanMessage` (chứa `user_query`).
- Nếu có `messages`: dùng trực tiếp.
- Nếu thiếu cả hai kiểu: raise `ValueError`.

### 3) Build graph

Graph hiện tại rất gọn:

`call_llm -> END`

Chi tiết:
- Tạo LLM từ config (`llm_provider`, `llm_model`).
- Nạp tools từ `tools` config.
- Nếu có tools thì bind vào LLM, nếu không thì chạy LLM thuần.
- Chạy node `call_llm` để gọi model với lịch sử messages.
- `route_after_llm` quyết định kết thúc (`__end__`) vì hiện config tools đang rỗng.

### 4) Kết quả đầu ra

Kết quả trả về từ graph theo `AgentState`:
- Trọng tâm nằm trong message cuối của model.
- Prompt yêu cầu model trả JSON có cấu trúc:
  - `tables[]`
  - `columns[]`
  - `reasoning`

Luu y: hiện chưa có parser/validator bắt buộc JSON ở layer agent, nên consumer downstream nên kiểm tra format trước khi dùng trực tiếp.

## Prompt contract (schema_linking.md)

Prompt áp các rule chính:
- Chỉ chọn bảng/cột thật sự tồn tại trong schema đầu vào.
- Chọn tập tối thiểu đủ để trả lời câu hỏi.
- Không suy đoán table/column không tồn tại.
- Không generate/gợi ý SQL.
- Trả về JSON đúng schema yêu cầu.

## Cấu hình đang dùng

Trong `config/app.yaml`:

```yaml
agents:
  schema_linking_agent:
    llm_provider: "mega_llm"
    llm_model: "openai-gpt-oss-120b"
    tools: []
```

Hệ quả:
- Agent đang chạy LLM-only.
- Không có tool-call loop ở runtime thực tế.

## Cách gọi nhanh

```python
from src.core.agents.factory import AgentFactory

agent = AgentFactory.create("schema_linking_agent")
result = await agent.ainvoke(
    {
        "user_query": "Top 5 customers by revenue in 2024",
        "database_schema": "tables: customers(id, name), orders(id, customer_id, total_amount, order_date)"
    }
)

# Đọc message cuối để lấy JSON tables/columns/reasoning
```

## Tích hợp đề xuất cho bước tiếp theo

1. Nối Guardrail -> Schema Linking trong một workflow thực tế.
2. Thêm validator cho JSON output của schema linking để giảm lỗi format.
3. Chuẩn hóa object output thành typed state riêng (thay vì chỉ để trong message text).
