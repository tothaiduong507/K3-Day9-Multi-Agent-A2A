# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung                  |
| --------------- | ------------------------- |
| Họ và tên       | Bùi Trung Hiếu            |
| MSSV            | 2A202601281               |
| Khóa/Lớp        | K3                        |
| Vai trò chính   | TV4 - Delivery Agent      |
| Ngày hoàn thành | 2026-08-05                |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | ------------------ | -------------- | --------------- | ---------- |
| Delivery Agent | `src/agents/delivery.py` -> `DeliveryAgent.analyze()` | `CaseInput` (chứa `claimed_order_id`) và `OrderAnalysis` | `DeliveryAnalysis` (chứa `is_delivered_late`, `seller_handoff_late`, `suggested_responsibility`, `late_seller_ids`, `evidence_ids`) | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --------- | ----------------------------- | ------- |
| Chuẩn hóa contract interface | TV5 / PolicyAgent & VerifierAgent | Bổ sung các thuộc tính alias `is_carrier_late` và `is_seller_late` vào `DeliveryAnalysis` để đảm bảo `PolicyAgent` đọc mượt mà không bị AttributeError |
| Tích hợp luồng Coordinator | TV1 / Coordinator | Đảm bảo `DeliveryAgent` xử lý an toàn các trường hợp order không tồn tại hoặc đơn bị hủy/chưa giao |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ---------------- | ------------- |
| Xây dựng logic phân tích giao hàng muộn | `src/agents/delivery.py` | Phân định chính xác giao trễ cho khách vs seller bàn giao muộn cho carrier | `python -m compileall src/agents/delivery.py` |
| Kiểm tra định dạng Evidence IDs vận chuyển | `src/agents/delivery.py` | Trả về mảng evidence IDs chuẩn `order:<order_id>` và `seller:<seller_id>` | Code review & unit test qua contract `DeliveryAnalysis` |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

Khi một đơn hàng bị giao trễ (`order_delivered_customer_date > order_estimated_delivery_date`), `DeliveryAgent` sẽ so sánh `order_delivered_carrier_date` với `shipping_limit_date` của từng sản phẩm. Nếu carrier nhận hàng sau hạn của seller, `seller_handoff_late` nhận giá trị `True`, `suggested_responsibility` nhận `"seller"`, và danh sách seller vi phạm được đưa vào `late_seller_ids`. Nếu không, `suggested_responsibility` nhận `"logistics_provider"`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Trong bài toán khiếu nại thương mại điện tử, cần xác định xem khiếu nại giao trễ của khách hàng có chính xác hay không, và nếu trễ thì trách nhiệm thuộc về đơn vị vận chuyển (`logistics_provider`) hay đối tác bán hàng (`seller`).

### Cách triển khai

1. **Nhận dữ liệu**: Nhận `CaseInput` và `OrderAnalysis` từ `Coordinator`.
2. **So sánh mốc thời gian khách nhận**: So sánh chuỗi ISO timestamp giữa `delivered_customer_at` và `estimated_delivery_at`. Dùng so sánh chuỗi trực tiếp (`left > right`) theo quy định dữ liệu CSV của Olist.
3. **So sánh mốc bàn giao seller**: Duyệt qua từng item trong `order.items`, so sánh `delivered_carrier_at` với `shipping_limit_date`. Nếu có bất kỳ item nào bị bàn giao muộn, ghi nhận `seller_id` vào `late_seller_ids` và đánh dấu `seller_handoff_late = True`.
4. **Đề xuất trách nhiệm**:
   - Nếu `is_delivered_late` = True và `seller_handoff_late` = True $\rightarrow$ `suggested_responsibility = "seller"`.
   - Nếu `is_delivered_late` = True và `seller_handoff_late` = False $\rightarrow$ `suggested_responsibility = "logistics_provider"`.
   - Nếu không trễ $\rightarrow$ `suggested_responsibility = None`.
5. **Đóng gói evidence**: Tạo danh sách evidence IDs bao gồm `order:<order_id>` và `seller:<seller_id>` cho các seller vi phạm (tối đa 10 IDs).

### Input, output và contract

| Thành phần | Mô tả |
| ---------- | ------ |
| Input | `case: CaseInput`, `order: OrderAnalysis` |
| Output | `DeliveryAnalysis` (Dataclass chứa thông tin phân tích vận chuyển) |
| Module phụ thuộc | `OrderSellerAgent` (cung cấp thông tin order và items) |
| Module sử dụng output | `PolicyAgent` (dùng kết quả phân tích để ra quyết định hoàn tiền), `VerifierAgent` (dùng để xác minh evidence) |
| Điều kiện lỗi cần xử lý | `order` không tìm thấy (`order_found = False`), đơn hàng chưa được giao (`delivered_customer_at = None`), hoặc thiếu mốc thời gian ước tính |

### Cách xác minh

```bash
python -m compileall src/agents/delivery.py
```

- **Kết quả mong đợi:** Biên dịch thành công không có lỗi cú pháp hoặc import.
- **Kết quả thực tế:** Biên dịch hoàn tất thành công (`Compiling 'src/agents/delivery.py'...`).
- **Artifact/log:** `src/agents/delivery.py`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần so sánh các mốc thời gian ngày giao hàng (`order_delivered_customer_date`, `order_estimated_delivery_date`, `shipping_limit_date`) để xác định việc trễ hạn.
- **Các phương án đã cân nhắc:**
  1. Chuyển đổi toàn bộ timestamp sang đối tượng `datetime` của Python (dùng `datetime.fromisoformat` hoặc `pd.to_datetime`).
  2. So sánh trực tiếp các chuỗi timestamp theo chuẩn ISO 8601 (`YYYY-MM-DD HH:MM:SS`).
- **Phương án đã chọn:** So sánh trực tiếp chuỗi timestamp (`left > right`).
- **Lý do:** 
  1. Dữ liệu trong CSV của Olist được ghi nhất quán theo định dạng chuỗi chuẩn ISO, do đó so sánh chuỗi cho kết quả thứ tự hoàn toàn chính xác với so sánh datetime.
  2. Không mất chi phí parse datetime trên hàng chục ngàn dòng dữ liệu, tối ưu tốc độ thực thi.
  3. Tránh được các lỗi phát sinh do lệch múi giờ (timezone offset) khi parse datetime.
- **Bằng chứng quyết định phù hợp:** Đề bài trong `README.md` quy định rõ: *"Các timestamp được so sánh theo giá trị trong CSV; không cần chuyển múi giờ."*

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `PolicyAgent` đọc các thuộc tính `delivery.is_carrier_late` và `delivery.is_seller_late` thông qua `getattr()`, nhưng `DeliveryAnalysis` trong `models.py` lại đặt tên trường là `is_delivered_late` và `seller_handoff_late`. Điều này khiến `PolicyAgent` luôn nhận giá trị mặc định `False`.
- **Nguyên nhân gốc:** Sự lệch tên thuộc tính (naming mismatch) giữa contract trong `models.py` và triển khai trong `policy.py`.
- **Cách xử lý:** Thêm hàm helper `_with_policy_aliases` trong `DeliveryAgent` để gán thêm thuộc tính alias `analysis.is_carrier_late = analysis.is_delivered_late` và `analysis.is_seller_late = analysis.seller_handoff_late` trước khi trả về kết quả.
- **Cách xác minh sau khi sửa:** Chạy biên dịch và kiểm tra thuộc tính của object trả về, đảm bảo cả 2 cách đặt tên thuộc tính đều truy cập được giá trị chính xác.
- **Điều học được:** Khi làm việc trong hệ thống multi-agent có contract chung, ngoài việc tuân thủ strict dataclass/schema, việc dự phòng tương thích (backward compatibility / alias) giúp tích hợp giữa các agent do các thành viên khác nhau phát triển diễn ra mượt mà không làm vỡ pipeline.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ input case đến output final như thế nào trong dự án?**
   - File input JSON chứa `claimed_order_id` được `Coordinator` tiếp nhận.
   - `OrderSellerAgent` và `PaymentAgent` truy xuất dữ liệu từ các file CSV của Olist (`olist_orders_dataset.csv`, `olist_order_items_dataset.csv`, `olist_order_payments_dataset.csv`) để lấy thông tin đơn hàng, danh sách item, seller và giao dịch thanh toán.
   - `DeliveryAgent` nhận kết quả từ `OrderSellerAgent` để so sánh các mốc thời gian giao hàng và phân định trách nhiệm giao trễ.
   - `PolicyAgent` tổng hợp kết quả từ 3 agent trên, đối chiếu với các quy tắc của `EC_POLICY_V1` để đưa ra quyết định (primary issue, root cause code, bên chịu trách nhiệm, khoản tiền hoàn đề xuất, action).
   - `VerifierAgent` kiểm tra định dạng evidence IDs, số lượng giới hạn entities, làm tròn tiền tệ và đóng gói thành JSON hoàn chỉnh ghi vào thư mục `output/`.

2. **Quy tắc phân định trách nhiệm khi giao trễ trong `EC_POLICY_V1` là gì?**
   - Nếu đơn hàng giao sau ngày ước tính (`delivered_customer > estimated`):
     - Nếu carrier nhận hàng sau hạn bàn giao của seller (`carrier_date > shipping_limit_date`) $\rightarrow$ Bán hàng chịu trách nhiệm (`late_delivery_seller` / `SELLER_HANDOFF_AFTER_LIMIT`), hoàn phí vận chuyển.
     - Nếu carrier nhận hàng đúng hoặc trước hạn bàn giao của seller $\rightarrow$ Đơn vị vận chuyển chịu trách nhiệm (`late_delivery_logistics` / `CARRIER_DELIVERED_AFTER_ESTIMATE`), hoàn phí vận chuyển.

3. **Vì sao tiền tệ trong dự án phải dùng `Decimal` thay vì `float`?**
   - Phép tính số chấm động (`float`) trong máy tính gây ra sai số làm tròn (floating-point precision issue, ví dụ `0.1 + 0.2 = 0.30000000000000004`).
   - Sử dụng `Decimal` đảm bảo các phép cộng/trừ tổng tiền payment, item, freight và so sánh đối soát trong khoảng sai số $0.10$ BRL đạt độ chính xác tuyệt đối.

4. **Ý nghĩa của Evidence IDs trong bài toán này?**
   - Evidence IDs đóng vai trò là bằng chứng có thể kiểm chứng trực tiếp từ dữ liệu CSV (như `order:<id>`, `item:<order_id>:<item_id>`, `payment:<order_id>:<seq>`, `seller:<seller_id>`, `policy:<cause_code>`).
   - Việc sinh evidence sai định dạng hoặc không tồn tại trong dữ liệu thực tế sẽ bị tính là false positive và bị trừ điểm.

5. **Vai trò của Verifier Agent ở cuối pipeline?**
   - Kiểm tra và đảm bảo output JSON tuân thủ strict schema (giới hạn số lượng entity $\le 5$, evidence $\le 10$, root cause $\le 3$).
   - Làm tròn tiền tệ về 2 chữ số thập phân (`ROUND_HALF_UP`) ở ranh giới output.
   - Lọc bỏ các evidence ID không hợp lệ thông qua Regex pattern trước khi ghi file.

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Bùi Trung Hiếu  
**Ngày xác nhận:** 2026-08-05