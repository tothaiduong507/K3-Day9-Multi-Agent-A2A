# Báo cáo vai trò thành viên — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
|---|---|
| Họ và tên | Tô Thái Dương |
| MSSV | 01994 |
| Khóa/Lớp | K3 |
| Vai trò chính | TV1 — Coordinator & Integration |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
|---|---|---|---|---|
| Khung và contract chung | `src/models.py`, `src/config.py` | Input schema và policy trong README | Các dataclass dùng để handoff giữa agent | Hoàn thành |
| Data loader | `src/data_loader.py` — `OlistDataLoader` | Bốn CSV orders, items, payments, sellers | Index dùng chung theo `order_id` và `seller_id` | Hoàn thành |
| Điều phối agent | `src/coordinator.py` — `Coordinator.run_case` | `CaseInput` và các agent đã inject | Chuỗi handoff và output đã qua Verifier | Hoàn thành |
| Chạy hàng loạt và CLI | `src/batch_runner.py`, `src/case_loader.py`, `src/cli.py`, `run.py` | 50 file `EC_001.json`–`EC_050.json` | Kết quả chạy, exit code và thống kê lỗi | Hoàn thành |
| Trace và ghi output | `src/trace_logger.py`, `src/output_writer.py` | Event của agent và final output | `logging/trace.jsonl`, `output/EC_xxx.json` | Hoàn thành |
| Tích hợp module nhóm | `src/agents/adapters.py`, `src/agents/base_agent.py` | API riêng của TV2 và TV3 | Interface `analyze(case, data)` thống nhất | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
|---|---|---|
| Tích hợp contract | TV2 — Order & Seller Agent | Chuyển kết quả `process(context)` thành `OrderAnalysis` mà không thay đổi logic nghiệp vụ của TV2 |
| Tích hợp contract | TV3 — Payment Agent | Cấp dữ liệu payment từ loader và chuyển kết quả domain thành `PaymentAnalysis` chung |
| Kiểm thử handoff | TV4 — Delivery Agent | Xác minh Delivery nhận đúng `OrderAnalysis` và trả dữ liệu cho Policy |
| Review tích hợp | TV5 — Policy & Verifier | Bổ sung compatibility field và contract test cho luồng Policy → Verifier |
| Tài liệu nhóm | Toàn bộ nhóm | Viết sơ đồ, ownership, data access và error flow trong `architecture.md` |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
|---|---|---|---|
| Đọc và index dữ liệu Olist một lần | `src/data_loader.py` | 99.441 orders, 112.650 items, 103.886 payments và 3.095 sellers được index | `python run.py --validate-only` |
| Điều phối end-to-end | `src/coordinator.py`, `src/batch_runner.py` | 50 case chạy độc lập, lỗi một case không làm hỏng toàn batch | `python run.py --input-dir input --output-dir output` |
| Kiểm tra input | `src/case_loader.py` | Bắt thiếu case, JSON lỗi, trùng ID, sai tên file hoặc policy version | `python -m unittest discover -v` |
| Ghi trace và output an toàn | `src/trace_logger.py`, `src/output_writer.py` | JSONL trace hợp lệ và output được atomic replace | `logging/trace.jsonl`, `output/` |
| Tích hợp agent từ các branch | `src/agents/adapters.py` | TV2–TV5 chạy qua cùng Coordinator contract | Chạy thực tế đủ 50 case |
| Kiểm thử | `tests/` | 13 test cho loader, case loader, coordinator, output writer và integration | `python -m unittest discover -v` |

Một output cụ thể do phần tích hợp tạo ra là bộ 50 file JSON từ `output/EC_001.json` đến `output/EC_050.json`. Lượt chạy hoàn chỉnh tạo đủ 50 output, không có case thất bại và ghi 650 event vào `logging/trace.jsonl`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Phần việc của tôi giải quyết bài toán đưa các module do nhiều thành viên phát triển độc lập vào cùng một pipeline có contract rõ ràng. Hệ thống cần đọc dữ liệu lớn hiệu quả, truyền đúng kết quả giữa các agent, cô lập lỗi theo case, ghi lại được handoff và chỉ tạo output sau khi Verifier chấp nhận.

### Cách triển khai

`OlistDataLoader` đọc bốn CSV cần thiết đúng một lần khi chương trình khởi động. Dữ liệu được lập index theo `order_id` hoặc `seller_id`, nhờ đó agent không phải quét lại toàn bộ CSV cho từng case. Getter trả defensive copy để agent không sửa trạng thái dùng chung.

Coordinator sử dụng dependency injection: mỗi agent được truyền vào constructor thay vì được khởi tạo bên trong logic nghiệp vụ. Với một case, Coordinator gọi Order/Seller và Payment, chuyển `OrderAnalysis` cho Delivery, sau đó đưa đủ ba báo cáo cho Policy và cuối cùng chuyển quyết định sang Verifier. Mỗi bước phát event vào trace. Nếu agent ném exception, Coordinator ghi `case_failed` và BatchRunner quyết định tiếp tục hay dừng theo `--fail-fast`.

Do API trên các branch ban đầu khác nhau, tôi không viết lại logic của thành viên mà tạo adapter. Adapter chuyển `process(context)` của TV2 và API payment theo mapping của TV3 sang contract chung. Cách này giữ ownership module, đồng thời giảm coupling trong Coordinator.

OutputWriter serialize `Decimal`, làm tròn các trường tiền `*_brl` tại ranh giới output, ghi vào file tạm cùng thư mục rồi atomic replace sang tên chính thức. Cơ chế này tránh để lại JSON chưa hoàn chỉnh nếu tiến trình bị gián đoạn.

### Input, output và contract

| Thành phần | Mô tả |
|---|---|
| Input | `CaseInput` lấy từ `input/EC_xxx.json`; dữ liệu nguồn là orders, order items, payments và sellers CSV |
| Output | `FinalCaseOutput` đúng schema README và file `output/EC_xxx.json` |
| Module phụ thuộc | `src/models.py`, `src/data_loader.py`, các module trong `src/agents/` |
| Module sử dụng output | Delivery dùng `OrderAnalysis`; Policy dùng ba analysis; Verifier dùng toàn bộ analysis và `PolicyDecision` |
| Điều kiện lỗi cần xử lý | Thiếu CSV, chưa gọi `load()`, JSON sai, thiếu case, sai policy, agent exception, output không serialize được |

### Cách xác minh

```powershell
python -m unittest discover -v
python run.py --validate-only
python run.py --input-dir input --output-dir output --trace-path logging\trace.jsonl
```

- **Kết quả mong đợi:** 13 test pass; xác nhận đúng 50 input; sinh đủ 50 JSON và trace hợp lệ.
- **Kết quả thực tế:** 13/13 test pass; 50/50 case thành công; DataLoader index 99.441 orders, 112.650 items, 103.886 payments và 3.095 sellers.
- **Artifact/log:** `output/`, `logging/trace.jsonl`, `architecture.md`; không chứa secret.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Nhiều agent cần truy xuất cùng dữ liệu Olist; nếu mỗi agent tự đọc CSV thì logic join bị lặp, chậm và có nguy cơ không nhất quán.
- **Các phương án đã cân nhắc:** (1) mỗi agent tự đọc và lọc CSV; (2) dùng một DataLoader tập trung, đọc một lần và cung cấp API truy vấn; (3) nạp toàn bộ dữ liệu vào một database riêng.
- **Phương án đã chọn:** DataLoader tập trung với index in-memory và dependency injection.
- **Lý do:** Bộ dữ liệu vừa với bộ nhớ, không cần thêm database hoặc dependency; đọc một lần giúp giảm I/O; mọi agent dùng cùng một nguồn sự thật; defensive copy giảm side effect và test fake loader dễ hơn.
- **Bằng chứng quyết định phù hợp:** Lượt validation index được toàn bộ bốn bảng và pipeline xử lý 50 case trong một lần khởi động loader. Unit test xác minh load idempotent, truy vấn thiếu trả giá trị an toàn và caller không sửa được index nội bộ.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi:** Các branch triển khai agent không cùng interface. Coordinator yêu cầu `analyze(case, data)`, trong khi TV2 cung cấp `process(context)` và TV3 yêu cầu `PaymentAgent(payment_rows_by_order)` rồi gọi `analyze(order_id=..., item_total_brl=..., freight_total_brl=...)`. TV2 cũng tham chiếu `BaseAgent` và tên `DataLoader` chưa tồn tại trong scaffold.
- **Bước tái hiện:** Merge các branch TV2, TV3 và TV4, sau đó đối chiếu constructor/method bằng `rg -n "class .*Agent|def analyze|def process" src/agents` và chạy pipeline tích hợp.
- **Nguyên nhân gốc:** Contract chung mới chỉ thống nhất ở mức khái niệm; mỗi module phát triển trên branch riêng với kiểu input/output và tên class khác nhau.
- **Cách xử lý:** Thêm compatibility `BaseAgent`, alias `DataLoader`, và hai adapter `IntegratedOrderSellerAgent`, `IntegratedPaymentAgent`. Adapter chịu trách nhiệm chuyển đổi dữ liệu nhưng không thay đổi quy tắc nghiệp vụ của module nguồn.
- **Cách xác minh sau khi sửa:** `python -m unittest discover -v` pass 13 test; chạy `python run.py` hoàn thành 50/50 case và tạo 50 output.
- **Điều học được:** Với bài nhóm, contract phải quy định cả chữ ký hàm, kiểu dữ liệu, ownership và semantics của từng field trước khi code. Adapter là giải pháp an toàn khi module đã tồn tại và không nên viết lại logic của thành viên khác trong giai đoạn tích hợp.

## 7. Hiểu biết về luồng end-to-end

Các câu hỏi Crossref/vector index trong template gốc không thuộc bài Day 9 này. Luồng end-to-end của bài Multi-Agent E-commerce Dispute Resolution được tôi hiểu như sau:

1. Mỗi file input cung cấp `case_id` và `claimed_order_id`. CaseLoader kiểm tra schema, sau đó Coordinator dùng order ID để truy vấn các index orders, items, payments và sellers trong DataLoader.
2. Order/Seller Agent phân tích trạng thái đơn, item, seller và mốc bàn giao; Payment Agent tính tổng item, freight, payment và reconciliation. Delivery Agent nhận `OrderAnalysis` để xác định giao trễ và phân biệt seller/logistics.
3. Policy Agent chỉ quyết định sau khi nhận đủ ba báo cáo và áp dụng sáu rule của `EC_POLICY_V1` theo đúng thứ tự ưu tiên. Verifier kiểm tra entity, evidence, giới hạn số lượng, tiền và output schema.
4. Coordinator ghi handoff vào JSONL; BatchRunner cô lập lỗi từng case; OutputWriter chỉ ghi file sau khi verification thành công và dùng atomic replace để bảo vệ artifact.
5. Lượt chạy được xem là thành công khi test pass, đủ chính xác 50 JSON có tên khớp input, không có case lỗi, mọi JSON đọc được, trace có đủ event và chạy lại cho kết quả nghiệp vụ giống nhau.

## 8. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Tô Thái Dương

**Ngày xác nhận:** 2026-08-05
