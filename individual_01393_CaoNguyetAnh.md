# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Cao Nguyệt Ánh |
| MSSV | 2A202601393 |
| Khóa/Lớp | K3 |
| Vai trò chính | Payment Agent — đối soát thanh toán |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Payment Agent | `src/agents/payment.py` — `PaymentAgent.analyze()` | `order_id`, các payment row, `item_total_brl`, `freight_total_brl` | `PaymentAnalysis`: tổng tiền, số payment row, trạng thái split/reconciliation, payment/evidence ID và lỗi dữ liệu | Hoàn thành module; chưa tích hợp được với contract chung |
| Chuẩn hóa dữ liệu payment | `src/agents/payment.py` — `to_decimal()`, `safe_int()`, `_parse_payment_row()` | Giá trị đọc từ CSV | `Decimal`, số nguyên và `PaymentRow` đã kiểm tra | Hoàn thành |
| Định dạng kết quả payment | `src/agents/payment.py` — `PaymentAnalysis.to_dict()` | Kết quả phân tích nội bộ | Dictionary có tiền làm tròn 2 chữ số và ID đúng giới hạn | Hoàn thành |

Payment Agent chỉ phân tích domain thanh toán. Việc chọn `primary_issue`, bên chịu trách nhiệm và khoản hoàn cuối cùng thuộc Policy Agent; Verifier Agent kiểm tra output trước khi ghi file.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Thống nhất contract tài chính | Order/Seller Agent và Policy Agent | Xác định `expected_total = item_total + freight_total`, ngưỡng đối soát `0.10 BRL` |
| Review nguy cơ join many-to-many | DataLoader/Coordinator | Đề xuất tổng hợp `order_items` và `order_payments` riêng theo `order_id` |
| Thống nhất evidence payment | Policy/Verifier Agent | Dùng dạng `payment:<order_id>:<payment_sequential>` có thể truy ngược về CSV |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Chuyển đổi tiền an toàn | `src/agents/payment.py` — `to_decimal()` | Dùng `Decimal(str(value))`, xử lý giá trị rỗng và báo lỗi giá trị không hợp lệ | Gọi hàm với chuỗi tiền hợp lệ, rỗng và ký tự không phải số |
| Phân tích payment theo order | `PaymentAgent.analyze()` | Tính `payment_total_brl`, `payment_count`, `is_split_payment`, `is_reconciled` | Chạy ví dụ độc lập bằng Python với payment row giả lập |
| Sinh ID có thể kiểm chứng | `PaymentRow.entity_id`, `PaymentRow.evidence_id` | ID theo schema của đề bài | Đối chiếu với `payment_sequential` trong CSV |
| Kiểm tra dữ liệu bất thường | `PaymentAgent._parse_payment_row()` | Phát hiện order ID không khớp, sequence/installment sai, payment âm hoặc type rỗng | Gọi hàm với từng input lỗi và kiểm tra `errors` |
| Giới hạn artifact đầu ra | `PaymentAnalysis.to_dict()` | Tối đa 5 payment ID và 10 evidence ID | Truyền hơn giới hạn số payment row và kiểm tra dictionary trả về |

Output cụ thể của phần việc là một `PaymentAnalysis`, ví dụ:

```json
{
  "order_id": "<order_id>",
  "payment_count": 2,
  "payment_total_brl": 115.0,
  "expected_total_brl": 115.0,
  "reconciliation_difference_brl": 0.0,
  "is_split_payment": true,
  "is_reconciled": true,
  "has_positive_payment": true,
  "payment_ids": ["<order_id>:1", "<order_id>:2"],
  "evidence_ids": ["payment:<order_id>:1", "payment:<order_id>:2"],
  "payment_methods": ["credit_card", "voucher"],
  "root_cause_signal": "MULTIPLE_PAYMENTS_RECONCILED",
  "errors": []
}
```

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Một order có thể có nhiều payment row, trong đó `payment_value` là giá trị của từng dòng còn `payment_installments` là số kỳ trả góp. Module cần lấy đủ các dòng, cộng tiền chính xác, nhận biết split payment, đối soát với tổng item và freight, rồi tạo evidence có thể truy ngược về dữ liệu gốc.

### Cách triển khai

`PaymentAgent` nhận mapping payment đã được nhóm theo `order_id`. Mỗi dòng được chuẩn hóa thành `PaymentRow` và kiểm tra `order_id`, `payment_sequential`, `payment_type`, `payment_installments`, `payment_value`. Các dòng hợp lệ được sắp xếp theo sequence để output ổn định.

Tiền được chuyển qua `Decimal(str(value))`. Module tính:

```text
payment_total = sum(payment_value)
expected_total = item_total_brl + freight_total_brl
difference = abs(payment_total - expected_total)
is_reconciled = difference <= 0.10 BRL
is_split_payment = payment_count >= 2
```

Khi vừa split payment vừa đối soát thành công, module phát tín hiệu `MULTIPLE_PAYMENTS_RECONCILED`. Policy Agent vẫn phải áp dụng thứ tự ưu tiên nghiệp vụ trước khi chọn kết luận cuối.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Mapping payment row theo order; `order_id`; `item_total_brl`; `freight_total_brl` |
| Output | `PaymentAnalysis` gồm tổng tiền, sai lệch, trạng thái split/reconciliation, ID, phương thức, tín hiệu và lỗi |
| Module phụ thuộc | Dữ liệu payment do `src/data_loader.py` đọc; tổng item/freight từ Order/Seller Agent |
| Module sử dụng output | Dự kiến: `src/agents/policy.py`, `src/agents/verifier.py`, `src/coordinator.py` |
| Điều kiện lỗi cần xử lý | Payment row sai order, sequence không hợp lệ hoặc trùng, installment âm, payment âm, type rỗng, giá trị tiền không hợp lệ |

### Cách xác minh

```bash
python -m pytest tests -q
```

- **Kết quả mong đợi:** Toàn bộ test pass và Coordinator gọi được Payment Agent bằng contract thống nhất.
- **Kết quả thực tế:** Chưa chạy được test vì môi trường hiện tại báo `No module named pytest`. Qua kiểm tra tĩnh, `Coordinator` đang gọi `analyze(case, data)` trong khi Payment Agent hiện yêu cầu keyword `order_id`, `item_total_brl`, `freight_total_brl`; vì vậy phần tích hợp chưa được xác nhận.
- **Artifact/log:** Source tại `src/agents/payment.py`; chưa có log test thành công cho riêng Payment Agent.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần cộng và đối soát tiền chính xác mà không làm nhân bản dữ liệu khi một order có nhiều item và nhiều payment row.
- **Các phương án đã cân nhắc:** (1) dùng `float` và merge trực tiếp hai bảng chi tiết; (2) aggregate từng domain riêng theo `order_id`, dùng `Decimal`, rồi handoff kết quả giữa các agent.
- **Phương án đã chọn:** Aggregate payment riêng và dùng `Decimal`; chỉ ghép hoặc handoff sau khi mỗi domain đã tính tổng.
- **Lý do:** Merge hai quan hệ one-to-many có thể tạo `số item × số payment row`; `float` cũng không phù hợp để kiểm tra chính xác ngưỡng tiền `0.10 BRL`.
- **Bằng chứng quyết định phù hợp:** Code dùng `Decimal(str(value))`, cộng payment row trước khi đối soát và kiểm tra `difference <= Decimal("0.10")`.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Kết quả tổng item hoặc tổng payment có thể tăng bất thường nếu merge trực tiếp `order_items` và `order_payments` theo `order_id`.
- **Lệnh hoặc bước tái hiện:** Chọn một order có nhiều item và nhiều payment row, merge hai tập dòng chi tiết rồi cộng các cột tiền.
- **Nguyên nhân gốc:** Hai phía đều là quan hệ one-to-many với order, nên phép join tạo tích dòng và lặp giá trị tiền.
- **Cách xử lý:** Tổng hợp item/freight và payment riêng theo `order_id`, sau đó mới handoff hoặc ghép hai kết quả aggregate.
- **Cách xác minh sau khi sửa:** So sánh `payment_total_brl` với phép tổng trực tiếp `payment_value` trên các dòng payment gốc của cùng order.
- **Điều học được:** Join đúng khóa chưa đảm bảo đúng nghiệp vụ; phải kiểm tra cardinality trước khi tổng hợp dữ liệu.

Blocker tích hợp hiện còn tồn tại:

- **Phạm vi bị ảnh hưởng:** `src/coordinator.py`, `src/agents/payment.py`, model `PaymentAnalysis` dùng chung.
- **Những gì đã loại trừ:** Logic nội bộ của Payment Agent có đủ bước parse, tổng hợp, đối soát và sinh ID; vấn đề nằm ở contract gọi hàm và hai định nghĩa `PaymentAnalysis` khác nhau.
- **Bước tiếp theo:** Thống nhất một `PaymentAnalysis` trong `src/models.py`, đổi `PaymentAgent.analyze()` theo contract của Coordinator hoặc cập nhật Coordinator, rồi bổ sung test riêng cho Payment Agent.

## 7. Hiểu biết về luồng end-to-end

1. Dữ liệu đi từ Crossref đến vector index như thế nào?
2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?
3. Quality checks khác freshness monitoring ở điểm nào trong bài lab?
4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?
5. Repair được xem là thành công dựa trên artifact và metric nào?

**Câu trả lời:**

Các khái niệm Crossref, vector index, retrieval, freshness, baseline/corrupted/repaired không xuất hiện trong bài Day 9 Multi-Agent E-commerce Dispute Resolution này, nên không có artifact thật để mô tả theo đúng pipeline RAG trong năm câu hỏi mẫu. Luồng tương ứng của bài hiện tại là: Coordinator đọc `input/EC_xxx.json`, dùng `claimed_order_id` truy xuất các CSV Olist; Order/Seller, Payment và Delivery Agent phân tích từng domain; Policy Agent áp dụng `EC_POLICY_V1`; Verifier Agent kiểm tra schema, evidence, entity ID và số tiền trước khi Output Writer ghi JSON.

Tập đánh giá là 50 case `EC_001`–`EC_050`; ground truth được suy ra từ dữ liệu CSV và policy thay vì document ID. Quality checks kiểm tra correctness của issue, entity, evidence, financial resolution và action. Nếu sửa pipeline, phải chạy lại cùng 50 case để kết quả trước và sau có thể so sánh công bằng. Repair chỉ thành công khi test pass, tạo đúng 50 JSON, không vi phạm hard gate, evidence truy ngược được về CSV/policy và các metric chấm điểm được cải thiện hoặc giữ nguyên.

## 8. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Cao Nguyệt Ánh  
**Ngày xác nhận:** 2026-08-05
