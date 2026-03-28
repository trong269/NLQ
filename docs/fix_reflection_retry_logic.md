# Fix Reflection Retry Logic

Tài liệu này giải thích các lỗi phát sinh trong hệ thống xử lý (pipeline) sinh câu lệnh SQL từ ngôn ngữ tự nhiên (NLQ -> SQL) liên quan đến chức năng thử lại (retry) khi ứng dụng báo lỗi, và phương pháp đã được áp dụng để sửa lỗi đó.

## Nguyên nhân gây ra lỗi Vòng lặp vô hạn (Infinite Loop)

Trước khi cấu trúc lại thư mục, hệ thống thường xuyên bị kẹt ở bước thẩm định câu lệnh SQL (Reflection). Khi AI thẩm định lệnh SQL là sai, luồng chạy quay lại bước gọi SQL Generator, tuy nhiên AI Generator lại sinh ra **đúng câu y hệt** câu lệnh vừa báo lỗi. Sau đó AI thẩm định lại báo sai, và vòng lặp tiếp tục mãi mãi, nguyên do bởi 3 lổ hổng chính dưới đây:

### 1. Phản hồi mâu thuẫn giữa Graph Node và Router
Cách kiểm tra điều kiện Retry không đồng nhất:
- Node xử lý (`node_nlq_run_reflection`) chỉ chấp nhận đếm tăng biến `reflection_retry_count` khi AI xuất ra `"verdict": "RETRY"`.
- Edge Router (`route_nlq_after_reflection`) sẽ bắt Graph quành lại `"retry"` chừng nào câu trả lời không phải là True (`is_correct: False`) và số lần chạy `retry_count < MAX_RETRIES`.

**Hậu quả:** Nếu Reflection trả về False nhưng không kèm chữ `"RETRY"`, bộ đếm Retry hoàn toàn bị kẹt ở mốc 0, Router vì thấy `< 3` nên liên tục reset lại Graph, mãi mãi không bao giờ vượt qua được chốt chặn Max Retries.

### 2. Sự "Mất trí nhớ" của SQL Gen Agent
Trong luồng Workflow, hệ thống LangGraph sẽ quay lại `"sql_gen"` nhờ Edge Router.
Tại thời điểm quay lui này, Node `node_nlq_run_sql_gen` gọi hàm `SqlGenAgent.ainvoke()` hoàn toàn bằng một State mới chỉ có câu hỏi gốc (`nl_input`) và cấu trúc Database (`schema_context`).

**Hậu quả:** Lỗi do Reflection bắt được hoàn toàn **bị vứt bỏ**. SqlGen Agent không nhận được feedback tại sao câu SQL cũ của nó bị sai, nên lần sau chạy lại nó vẫn sẽ nghĩ hướng trước đó là đúng, và gen y chang câu gặp lỗi cũ.

Thậm chí, nếu nạp cả feedback vào, thì Node khởi tạo vòng lặp của SqlGen là `node_sql_gen_initialize` luôn luôn reset biến `sql_query` và `sql_error` thành chuỗi rỗng `""`.

### 3. Lỗi Đứt kết nối (Network Error) khi Chat với LLM
Module chung định tuyến các Agent `route_after_llm` có một lổ hổng trong code (Bug).
Khi thực hiện gọi LLM thất bại (Error/Exception), Status chuyển thành `"running"` và `retry_count` được cộng dồn (vd: `retry_count = 1`).
Nhưng router `route_after_llm` lại không có định hướng đường đi (Edge Mapping) cho Status này. Kết quả, Graph đi thẳng tới nhánh `"__end__"`. Agent chết ngay lập tức thay vì vòng lại node gọi LLM để thử API lại lần nữa.

---

## Chi tiết các bước sửa lỗi (Fixes Applied)

1. **Sửa `src/core/workflows/components/nodes.py`:**
   - **`node_nlq_run_sql_gen`**: Truyền chèn `reflection_raw` (như là thông điệp bào lỗi của Reflection) lồng vào `sql_error` và `sql_query` khi khởi chạy mô hình.
   - **`node_nlq_run_reflection`**: Thống nhất điều kiện. Bất cứ khi nào Agent trả kết quả sai logic (`is_correct == False`), bộ đếm Retry đều phải tăng lên `+1`. Loại bỏ dòng code lỗi mà người dùng vừa nhập ngoài luồng.
   - **`route_nlq_after_reflection`**: Số lần thử tối đa (`MAX_REFLECTION_RETRY`) đổi từ 3 xuống 2.

2. **Sửa `src/core/agents/components/nodes.py`:**
   - **`node_sql_gen_initialize`**: Sửa cấu trúc Khởi tạo. State `sql_error` và `sql_query` nhận từ Workflow đưa vào qua args sẽ **không bị ghi đè** (overwrite) thành rỗng nữa. Các Agent giờ đã giữ lại trí nhớ (feedback) của lần chạy trước.
   - **`route_after_llm`**: Bổ sung điều hướng nếu `retry_count > 0` và số lần chạy lỗi dưới mức `max_retries`: sẽ return nhánh `"call_llm"` nhằm yêu cầu Node Call API chạy lại kết nối khi đứt mạng (Connection Refused).

3. **Sửa `src/core/agents/reflection_agent.py`:**
   - Dọn dẹp lại Module (Imports rác, copy paste). Cấu hình đúng chuẩn tên Edge `"call_llm"` vào `add_conditional_edges` của mô hình LangGraph để cho phép tái sử dụng Node llm nội bộ.
