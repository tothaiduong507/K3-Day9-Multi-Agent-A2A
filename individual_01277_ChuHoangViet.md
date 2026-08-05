# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung                                 |
| --------------- | ---------------------------------------- |
| Họ và tên       | Chu Hoàng Việt                           |
| MSSV            | 2A202601277                              |
| Khóa/Lớp        | K3                                       |
| Vai trò chính   | Policy Agent & Verifier Agent Developer  |
| Ngày hoàn thành | 2026-08-05                               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | ------------------ | -------------- | ----------------- | ------------------------------------- |
| Policy Agent | `src/policy.py` (`PolicyAgent.decide`) | `CaseInput`, `OrderAnalysis`, `PaymentAnalysis`, `DeliveryAnalysis` | `PolicyDecision` | Hoàn thành |
| Verifier Agent & Output Builder | `src/verifier.py` (`VerifierAgent.verify_and_build`) | `CaseInput`, `OrderAnalysis`, `PaymentAnalysis`, `DeliveryAnalysis`, `PolicyDecision` | `FinalCaseOutput` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ------------------------- | ----------------------------- | ----------------------- |
| Code Review | TV4 / `src/delivery.py` | Kiểm tra logic so sánh mốc `order_delivered_customer_date` với `order_estimated_delivery_date` và `shipping_limit_date` đảm bảo trả về boolean chính xác. |
| Soạn thảo tài liệu kiến trúc | Nhóm / `architecture.md` | Hoàn thành mô tả sơ đồ multi-agent, vai trò, quyền truy cập dữ liệu và luồng handoff giữa các agent. |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ------------------------- | --------------- |
| Triển khai logic quy tắc `EC_POLICY_V1` | `src/policy.py` | Áp dụng chính xác 6 quy tắc phân loại issue, xác định bên chịu trách nhiệm và khoản hoàn tiền theo thứ tự ưu tiên. | Test đơn vị và kiểm thử end-to-end trên 50 case. |
| Kiểm định Schema & Dựng Output | `src/verifier.py` | Đảm bảo 100% file JSON xuất ra đúng định dạng schema, kiểm tra regex Evidence IDs, làm tròn số tiền bằng Decimal và giới hạn số lượng mảng. | `python -m unittest tests/test_verifier.py` và kiểm tra 50 file JSON trong `output/`. |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:
* Tạo ra toàn bộ 50 file JSON chuẩn định dạng từ `output/EC_001.json` đến `output/EC_050.json` đạt điểm tối đa về độ chính xác của Evidence IDs, Financial resolution (làm tròn 2 chữ số thập phân) và các giới hạn mảng theo đúng yêu cầu đề bài.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Phần việc này giải quyết giai đoạn ra quyết định tài chính/nghiệp vụ và chốt chặn an toàn kỹ thuật cuối cùng trong pipeline multi-agent. Sau khi các agent chuyên môn phân tích order, thanh toán và giao hàng, `PolicyAgent` sẽ áp dụng bộ quy tắc kinh doanh để kết luận vấn đề chính, trong khi `VerifierAgent` chịu trách nhiệm rà soát định dạng, làm tròn tiền tệ an toàn và ép dữ liệu khớp hoàn toàn với JSON Schema bắt buộc trước khi ghi xuống đĩa.

### Cách triển khai

1. **`PolicyAgent`:**
   - Đọc dữ liệu từ các Pydantic models phân tích (`OrderAnalysis`, `PaymentAnalysis`, `DeliveryAnalysis`).
   - Áp dụng cấu trúc rẽ nhánh `if-elif-else` theo đúng **thứ tự ưu tiên** của bộ quy tắc `EC_POLICY_V1`:
     1. `canceled_order_paid`: Order status = `canceled` & payment > 0 -> Hoàn full tiền, platform chịu trách nhiệm.
     2. `unavailable_order_paid`: Order status = `unavailable` & payment > 0 -> Hoàn full tiền, platform chịu trách nhiệm.
     3. `late_delivery_seller`: Carrier muộn & Seller bàn giao sau `shipping_limit_date` -> Hoàn cước (`freight_total_brl`), seller chịu trách nhiệm.
     4. `late_delivery_logistics`: Carrier muộn & Seller bàn giao đúng/trước hạn -> Hoàn cước, logistics chịu trách nhiệm.
     5. `valid_split_payment`: Có 2 dòng thanh toán & tổng thanh toán khớp tổng (item + freight) trong sai số <= 0.10 BRL -> Giải thích, không hoàn tiền.
     6. `unsupported_late_claim`: Mặc định khi giao đúng hạn -> Bác bỏ khiếu nại.
2. **`VerifierAgent`:**
   - Dựng danh sách `evidence_ids` theo 5 mẫu định dạng chuẩn (`order:<id>`, `item:<id>:<i>`, `payment:<id>:<i>`, `seller:<id>`, `policy:<code>`).
   - Kiểm tra bằng Regular Expressions (`re.compile`), loại bỏ các ID không hợp lệ và cắt tối đa 10 evidence IDs.
   - Sử dụng thư viện `decimal.Decimal` với `ROUND_HALF_UP` để làm tròn tất cả các giá trị tiền tệ về đúng 2 chữ số thập phân tại ranh giới xuất output (`float`).
   - Giới hạn độ dài các mảng: `order_ids` (5), `item_ids` (5), `seller_ids` (5), `payment_ids` (5), `ranked_causes` (3), `responsible_parties` (3), `resolution_actions` (5).
   - Áp dụng quy tắc đặc biệt: Nếu đơn hàng không chứa `item_ids`, tự động reset `seller_ids` về rỗng và `item_total_brl`, `freight_total_brl` về `0.0`.

### Input, output và contract

| Thành phần              | Mô tả |
| ----------------------- | -------------------------------------- |
| Input | `CaseInput`, `OrderAnalysis`, `PaymentAnalysis`, `DeliveryAnalysis` |
| Output | `PolicyDecision` (cho Policy Agent) và `FinalCaseOutput` (cho Verifier Agent) |
| Module phụ thuộc | `Order & Seller Agent`, `Payment Agent`, `Delivery Agent` |
| Module sử dụng output | `Coordinator` (ghi log `trace.jsonl` và xuất file `output/EC_xxx.json`) |
| Điều kiện lỗi cần xử lý | Đơn không có item, lỗi trôi số chấm động khi cộng trừ float, evidence ID sai định dạng regex, mảng entities vượt quá độ dài quy định. |

### Cách xác minh
```bash
python -m unittest discover -s tests -p "test_*.py"
python main.py --input_dir input/ --output_dir output/
```

- **Kết quả mong đợi:** Tất cả 50 case chạy thành công, tạo ra 50 file JSON tại thư mục output/, không có lỗi schema validation, toàn bộ số tiền làm tròn đúng 2 chữ số thập phân.
- **Kết quả thực tế:** Kết quả thực tế: Khớp 100% với kết quả mong đợi, thời gian thực thi của Policy/Verifier Agent chỉ mất $< 1$ ms/case.
- **Artifact/log:** Artifact/log: output/EC_001.json - output/EC_050.json, trace.jsonl.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn giữa việc dùng LLM (prompting) hay dùng Deterministic Code (Python if-else + Decimal) cho PolicyAgent và VerifierAgent.
- **Các phương án đã cân nhắc:** 
    + Phương án A: Sử dụng LLM (<=10B parameters) để đọc dữ liệu phân tích và đưa ra quyết định policy kèm JSON output.Phương án B: Triển khai bằng code Python thuần (Deterministic Rule Engine) kết hợp với kiểu dữ liệu Decimal để tính toán tài chính và regex để verify schema.
    + Phương án B: Triển khai bằng code Python thuần (Deterministic Rule Engine) kết hợp với kiểu dữ liệu Decimal để tính toán tài chính và regex để verify schema.
- **Phương án đã chọn:** Phương án B (Code Python thuần).
- **Lý do:** 
    + Quy tắc EC_POLICY_V1 có logic rẽ nhánh điều kiện rất rõ ràng và khắt khe. Dùng LLM dễ gặp rủi ro ảo giác (hallucination), tính toán sai lệch tiền hoàn hoặc sai định dạng regex của Evidence ID.Code Python cho độ chính xác tuyệt đối 100%, không tốn tài nguyên GPU/API quota và độ trễ cực thấp (< 1 ms so với hàng trăm ms của LLM), đảm bảo tối ưu thời gian chạy 50 case trong ca thi.
    + Quy tắc EC_POLICY_V1 có logic rẽ nhánh điều kiện rất rõ ràng và khắt khe. Dùng LLM dễ gặp rủi ro ảo giác (hallucination), tính toán sai lệch tiền hoàn hoặc sai định dạng regex của Evidence ID.Code Python cho độ chính xác tuyệt đối 100%, không tốn tài nguyên GPU/API quota và độ trễ cực thấp (< 1 ms so với hàng trăm ms của LLM), đảm bảo tối ưu thời gian chạy 50 case trong ca thi.
- **Bằng chứng quyết định phù hợp:** 100% trong số 50 case output vượt qua bước kiểm tra Verifier mà không xảy ra bất kỳ lỗi trôi số thập phân hay lỗi sai định dạng ID nào.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** AssertionError: 15.000000000000002 != 15.0 hoặc sai số ở phép tính tổng payment_total_brl - (item_total_brl + freight_total_brl) dẫn đến đánh giá sai điều kiện valid_split_payment (<= 0.10 BRL).
- **Lệnh hoặc bước tái hiện:** Chạy thử nghiệm phép tính tài chính với dữ liệu kiểu float trong Python: float(100.10) + float(15.05).
- **Nguyên nhân gốc:** Hiện tượng trôi số chấm động (floating-point representation error) chuẩn IEEE 754 nguyên bản của kiểu dữ liệu float trong Python khi thực hiện phép cộng/trừ tài chính trước khi đối so sánh.
- **Cách xử lý:** 
    + Chuyển toàn bộ các biến tài chính trong PolicyAgent sang kiểu decimal.Decimal khởi tạo từ chuỗi (Decimal(str(val))).
    + Chỉ thực hiện ép kiểu sang float sau khi đã làm tròn bằng quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) tại bước trả về kết quả cuối cùng ở VerifierAgent.
- **Cách xác minh sau khi sửa:** Chạy lại unit test tính toán tiền cước và tổng tiền thanh toán cho tất cả 50 case, không còn trường hợp nào bị sai lệch số thập phân.
- **Điều học được:** Luôn sử dụng Decimal cho bất kỳ bài toán đối soát tài chính hoặc tính toán tiền tệ nào để tránh sai sót ở các ngưỡng so sánh điều kiện.

Nếu chưa xử lý xong:

- **Phạm vi bị ảnh hưởng:** [Module/artifact.]
- **Những gì đã loại trừ:** [Các giả thuyết đã kiểm tra.]
- **Bước tiếp theo:** [Hành động có thể kiểm chứng.]

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. Dữ liệu đi từ Crossref đến vector index như thế nào?
2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?
3. Quality checks khác freshness monitoring ở điểm nào trong bài lab?
4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?
5. Repair được xem là thành công dựa trên artifact và metric nào?

**Câu trả lời:**

1. Dữ liệu từ file JSON input (claimed_order_id) được Coordinator tiếp nhận và truyền tới các sub-agent. Các agent dùng ID này tra cứu, join bảng trên các file CSV Olist (orders, order_items, order_payments, sellers) để trích xuất thông tin trạng thái, mốc thời gian và dòng tiền.

2. Với bài lab này, tập dữ liệu 50 trường hợp (EC_001 - EC_050) đóng vai trò là evaluation set. Ground-truth về quyết định refund, nguyên nhân gốc, bên chịu trách nhiệm và khoản tiền refund được dùng để đối soát tính đúng đắn dựa trên các trọng số điểm (Primary issue 20%, Entities 20%, Financial 20%, Root cause 15%, Evidence 15%, Actions 10%).

3. Quality checks (như ở VerifierAgent) tập trung kiểm tra tính hợp lệ về mặt kỹ thuật và cấu trúc (schema validation, regex format của evidence ID, giới hạn mảng, làm tròn tiền). Trong khi đó, freshness monitoring trong các hệ thống thực tế theo dõi sự biến động và tính cập nhật của dữ liệu theo thời gian (ví dụ: kiểm tra timestamp dữ liệu có bị trễ so với mốc hiện tại hay không).

4. Phải dùng cùng một test set cho baseline, corrupted và repaired pipelines để đảm bảo tính nhất quán (controlled benchmark), giúp so sánh khách quan tác động của từng cải tiến hoặc sửa lỗi trên cùng một phân phối dữ liệu đầu vào.

5. Việc sửa đổi (Repair) hệ thống được xem là thành công dựa trên artifact các file JSON output sinh ra đạt điểm số cao hơn trên leaderboard, giảm thiểu tỷ lệ case bị hard gate (0 điểm), và log vết thực thi trace.jsonl thể hiện đầy đủ các bước handoff giữa các agent không có lỗi ngoại lệ (exception).

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Chu Hoàng Việt
**Ngày xác nhận:** 2026-08-05
