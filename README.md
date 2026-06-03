# Vấn đề N+1 trong ORM Phân tán: Hệ thống Tác giả - Sách

> **Đề tài 85** | CSDLPT — Hệ thống Cơ sở dữ liệu phân tán
> Dựa trên giáo trình Özsu & Valduriez, Chương 15: Quản trị Cơ sở dữ liệu Đối tượng Phân tán
> **Sử dụng Dữ liệu Thực tế (Goodreads Dataset)**

---

## Tổng quan

Dự án này trình bày và đo lường **vấn đề truy vấn N+1** trong môi trường ORM phân tán với 3 nút được phân mảnh ngang. Khác với các phiên bản trước (sử dụng dữ liệu giả lập), phiên bản này sử dụng bộ dữ liệu thực tế từ Kaggle Goodreads (gồm 300 tác giả và hơn 4,200 cuốn sách).
Đồ án so sánh giữa chiến lược **Lazy Loading** (N+1 yêu cầu HTTP) và **Eager Loading** (JOIN tập trung), đồng thời bóc tách chi tiết "Chi phí nạp lại" (Rehydration Cost) theo lý thuyết.

## Cấu trúc Dự án

```text
5/
├── Book_Details.csv           # Tập dữ liệu thực tế từ Kaggle
├── config.py                  # Cấu hình dùng chung & Logic phân mảnh
├── requirements.txt           # Các thư viện Python cần thiết
├── web_dashboard.py           # Dashboard điều khiển tổng (cổng 8080)
│
├── nodes/
│   ├── models.py              # Mô hình Author & Book với OID (UUID)
│   ├── cache_manager.py       # Quản lý cache LRU với Garbage Collection
│   └── node_server.py         # API REST Flask cho từng Node
│
├── client/
│   ├── coordinator.py         # Điều phối định tuyến + Mô phỏng lỗi
│   ├── lazy_loader.py         # Chiến lược N+1
│   └── eager_loader.py        # Chiến lược Batch JOIN
│
├── benchmark/
│   ├── run_benchmark.py       # Trình chạy benchmark đa mức độ trễ
│   └── plot_results.py        # Trình vẽ biểu đồ (matplotlib)
│
├── scripts/
│   ├── import_data.py         # ETL pipeline nạp CSV vào 3 DB SQLite
│   ├── start_all_nodes.py     # Khởi động đồng loạt 3 nút
│   ├── kill_node.py           # Dừng nút theo cổng
│   └── demo_failure.py        # Demo kịch bản lỗi hệ thống (Partial Failure)
│
├── web/                       # Chứa giao diện HTML/CSS/JS cho Dashboard
├── docs/                      # Toàn bộ tài liệu báo cáo và lý thuyết
└── results/                   # Thư mục chứa kết quả benchmark
```

## Hướng dẫn cài đặt và sử dụng

### 1. Cài đặt thư viện

Mở Terminal tại thư mục `5/` và chạy:

```bash
pip install -r requirements.txt
```

### 2. Nạp dữ liệu vào cơ sở dữ liệu (ETL)

Do sử dụng dữ liệu thực tế, bạn cần chạy kịch bản import để đọc file CSV, tạo UUID ngẫu nhiên và phân mảnh dữ liệu vào 3 Node:

```bash
python scripts/import_data.py
```

*Lưu ý: Quá trình này sẽ sinh ra 3 file `node_a.db`, `node_b.db`, `node_c.db` bên trong thư mục `nodes/`.*

### 3. Khởi động hệ thống phân tán

Mở một Terminal mới và chạy lệnh sau để khởi động đồng thời 3 Node (Port 5001, 5002, 5003):

```bash
python scripts/start_all_nodes.py
```

### 4. Chạy Benchmark và vẽ biểu đồ

Mở một Terminal khác để chạy tập lệnh so sánh hiệu năng giữa Eager và Lazy:

```bash
python benchmark/run_benchmark.py
python benchmark/plot_results.py
```

Các file ảnh `.png` vẽ biểu đồ phân tích chi phí mạng và tốc độ (Speedup) sẽ xuất hiện trong thư mục `results/`.

### 5. Demo Kịch bản Lỗi (Graceful Degradation)

Để chứng minh hệ thống vẫn hoạt động khi một Node bị sập tắt đột ngột (Minh chứng định lý CAP):

```bash
python scripts/demo_failure.py
```

Kịch bản này sẽ tự động gọi truy vấn, tự tắt (kill process) Node B giữa chừng, sau đó trình Điều phối (Coordinator) sẽ tự động Retry, bỏ qua Node B và trả về dữ liệu của 2 Node còn sống một cách an toàn.

### 6. Mở Web Dashboard

```bash
python web_dashboard.py
```

Truy cập: **http://127.0.0.1:8080** để xem giao diện trực quan, tình trạng các Node và quản lý Cache.

---

## Cơ sở Lý thuyết (Theo Özsu & Valduriez)

Đồ án này là mô hình thực chứng (Proof-of-Concept) cho các khái niệm cốt lõi sau trong môn CSDL Phân Tán:

- **Định danh đối tượng (OID):** Sử dụng UUID làm LOID (Logical OID) bất biến và duy nhất toàn cầu (§15.4.1).
- **Phân mảnh ngang dẫn xuất (Derived Fragmentation):** Tác giả phân mảnh theo dải ký tự (`[A-H]`, `[I-P]`, `[Q-Z]`), các Sách đi theo vị trí vật lý của Tác giả tương ứng (§15.2).
- **Cấu trúc đối tượng phức hợp (Composite Object):** Sự lồng nhau giữa `Author` và `Book` gây ra bài toán hiệu năng N+1 (§15.1.3).
- **Chi phí nạp lại (Rehydration Cost):** Đo lường tường tận 3 thành phần: chi phí truyền I/O Mạng, chi phí Tuần tự hóa JSON tại Server, và Giải tuần tự hóa tại Client (§15.6).
- **Khả năng chịu lỗi (Fault Tolerance):** Chấp nhận mất một phần dữ liệu (Graceful Degradation) thay vì sập toàn bộ hệ thống khi bị chia cắt mạng (Network Partition).
