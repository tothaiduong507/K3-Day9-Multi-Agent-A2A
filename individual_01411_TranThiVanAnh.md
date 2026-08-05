# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung     |
| --------------- | ------------ |
| Họ và tên       | Trần Thị Vân Anh |
| MSSV            | 01411        |
| Khóa/Lớp        | K3           |
| Vai trò chính   | TV2 — Order & Seller Agent |
| Ngày hoàn thành | 2026-08-05   |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | ------------------ | -------------- | ----------------- | ---------- |
| Order & Seller Agent (TV2) | `src/agents/order_seller_agent.py` / `OrderSellerAgent.process()` | `claimed_order_id` & dữ liệu từ Olist CSV | Payload contract `order_analysis` | Hoàn thành |
| Phân tích trạng thái đơn & mốc thời gian | `src/agents/order_seller_agent.py` | Order record trong `olist_orders_dataset.csv` | Dict timestamps (`purchase`, `approved`, `delivered_carrier`, `delivered_customer`, `estimated_delivery`) | Hoàn thành |
| Kiểm tra Seller bàn giao trễ | `src/agents/order_seller_agent.py` | Item records & `shipping_limit_date` | `seller_handoff_late` (bool) & `violating_seller_ids` | Hoàn thành |
| Trích xuất Evidence Entity IDs | `src/agents/order_seller_agent.py` | Order, item, seller ID | `affected_order_ids`, `affected_item_ids`, `affected_seller_ids`, `evidence_ids` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --------- | ----------------------------- | ------- |
| Thống nhất Contract `order_analysis` | TV1 Coordinator & TV4 Delivery Agent | Chốt schema `order_analysis` làm đầu vào cho Delivery Agent và Policy Agent |
| Kiểm thử chéo với Delivery Agent | TV4 Delivery Agent | Rà soát phân định trách nhiệm giao trễ giữa seller và đơn vị vận chuyển |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ----------------- | ------------- |
| Xây dựng OrderSellerAgent | `src/agents/order_seller_agent.py` | Class `OrderSellerAgent` kế thừa `BaseAgent` | `python3 -c "from src.agents.order_seller_agent import OrderSellerAgent"` |
| Phân tích mốc bàn giao của Seller | `OrderSellerAgent.process()` | So sánh `order_delivered_carrier_date` so với `shipping_limit_date` từng sản phẩm | Đơn `EC_001` xác định seller `f7496d659ca9fdaf323c0aae84176632` bàn giao muộn |
| Tạo Evidence theo định dạng chuẩn | `OrderSellerAgent.process()` | Sinh mảng `evidence_ids` chứa các tiền tố `order:`, `item:`, `seller:` | `output/EC_001.json` chứa đủ evidence format |

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Phân tích dữ liệu đơn hàng (order status, timestamps) và các sản phẩm trong đơn (order items) để xác định:
1. Đơn hàng có các sản phẩm nào, do seller nào bán.
2. Seller có bàn giao hàng cho đơn vị vận chuyển muộn hơn hạn quy định (`shipping_limit_date`) hay không.
3. Sinh các ID thực thể ảnh hưởng (`order_ids`, `item_ids`, `seller_ids`) và các ID bằng chứng (`evidence_ids`) tuân thủ đúng định dạng quy định.

### Cách triển khai
- **Khởi tạo và nhận Input**: Agent nhận `claimed_order_id` từ Coordinator.
- **Truy xuất dữ liệu**: Sử dụng Data Loader để lấy thông tin order từ `olist_orders_dataset.csv` và danh sách các item từ `olist_order_items_dataset.csv`.
- **So sánh mốc bàn giao**: Lấy thời điểm carrier nhận hàng `order_delivered_carrier_date`. Với mỗi item trong đơn, so sánh chuỗi timestamp `order_delivered_carrier_date > shipping_limit_date`. Nếu vi phạm, đánh dấu `is_handoff_late = True` cho item đó và đưa `seller_id` tương ứng vào `violating_seller_ids`.
- **Giới hạn số lượng & Format Evidence**:
  - Giới hạn tối đa 5 element cho `affected_order_ids`, `affected_item_ids`, `affected_seller_ids`.
  - Tạo bằng chứng với định dạng `order:<order_id>`, `item:<order_id>:<item_id>`, `seller:<seller_id>`.

### Input, output và contract

| Thành phần | Mô tả |
| ---------- | ------ |
| Input | Context chứa `claimed_order_id` |
| Output | Payload `order_analysis` chứa `order_status`, `timestamps`, `items`, `sellers`, `seller_handoff_late`, `violating_seller_ids`, `evidence_ids` |
| Module phụ thuộc | `src/data_loader.py` |
| Module sử dụng output | TV4 Delivery Agent, TV5 Policy Agent |

### Cách xác minh

```bash
python3 main.py
```

- **Kết quả mong đợi:** `OrderSellerAgent` phân tích chính xác trạng thái đơn và cờ bàn giao muộn của seller cho 50 case mà không gặp lỗi runtime.
- **Kết quả thực tế:** Chạy thành công 50/50 case, dữ liệu `order_analysis` truyền đầy đủ sang Delivery Agent và Policy Agent.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Một đơn hàng có thể có nhiều item thuộc các seller khác nhau hoặc có các hạn giao `shipping_limit_date` khác nhau.
- **Các phương án đã cân nhắc:**
  1. Đánh giá bàn giao muộn ở cấp độ đơn hàng chung (chỉ lấy min/max limit date của đơn).
  2. Duyệt chi tiết từng item row và so sánh trực tiếp `order_delivered_carrier_date` với `shipping_limit_date` riêng của từng item.
- **Phương án đã chọn:** Phương án 2 (duyệt chi tiết theo từng item).
- **Lý do:** Tuân thủ đúng quy tắc nghiệp vụ đề bài: seller bị coi là bàn giao muộn nếu `order_delivered_carrier_date > shipping_limit_date` của item thuộc seller đó, đảm bảo tính chính xác tuyệt đối khi gán trách nhiệm vi phạm cho đúng seller ID.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Với các đơn hàng có trạng thái `canceled` hoặc `unavailable`, danh sách item rỗng (`raw_items = []`), dẫn tới việc cố gắng lấy `item_ids` gây lỗi hoặc sinh bằng chứng giả (false positive evidence).
- **Root cause:** Đơn bị hủy trước khi sản phẩm được tạo dòng dữ liệu trong `olist_order_items_dataset.csv`.
- **Cách xử lý:** Thêm cờ `has_items = len(raw_items) > 0`. Khi `has_items == False`, thiết lập `affected_item_ids = []`, `affected_seller_ids = []`, và chỉ tạo bằng chứng ở cấp đơn hàng `order:<order_id>`.
- **Cách xác minh sau khi sửa:** Đơn hàng hủy/không sẵn có chạy qua agent không bị crash và không sinh ra bằng chứng `item:` hay `seller:` lỗi.

---

## 7. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Trần Thị Vân Anh  
**Ngày xác nhận:** 2026-08-05
