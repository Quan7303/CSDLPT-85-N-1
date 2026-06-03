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
├── docs/
│   ├── proposal.md            # Bản đề xuất dự án (Project Proposal)
│   ├── design_document.md     # Tài liệu thiết kế hệ thống (Architecture)
│   └── final_academic_report.md # Báo cáo học thuật chung cuộc
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

---

## Cơ sở Lý thuyết (Theo Özsu & Valduriez)

Đồ án này là mô hình thực chứng (Proof-of-Concept) cho các khái niệm cốt lõi sau trong môn CSDL Phân Tán:

- **Định danh đối tượng (OID):** Sử dụng UUID làm LOID (Logical OID) bất biến và duy nhất toàn cầu (§15.4.1).
- **Phân mảnh ngang dẫn xuất (Derived Fragmentation):** Tác giả phân mảnh theo dải ký tự (`[A-H]`, `[I-P]`, `[Q-Z]`), các Sách đi theo vị trí vật lý của Tác giả tương ứng (§15.2).
- **Cấu trúc đối tượng phức hợp (Composite Object):** Sự lồng nhau giữa `Author` và `Book` gây ra bài toán hiệu năng N+1 (§15.1.3).
- **Chi phí nạp lại (Rehydration Cost):** Đo lường tường tận 3 thành phần: chi phí truyền I/O Mạng, chi phí Tuần tự hóa JSON tại Server, và Giải tuần tự hóa tại Client (§15.6).
- **Khả năng chịu lỗi (Fault Tolerance):** Chấp nhận mất một phần dữ liệu (Graceful Degradation) thay vì sập toàn bộ hệ thống khi bị chia cắt mạng (Network Partition).


---

# Distributed Database Project Proposal

**Due Date:**
**Project ID & Category:** Đề tài 85 - Quản lý đối tượng phân tán (Category: Distributed Object Database)

## 1. Project Identity

- **Team Name:** QuanThienDe
- **Team Members:** Nguyễn Gia Quân
- **Project Title:** Vấn Đề N+1 trong ORM Phân Tán: Hệ thống Tác giả - Sách

## 2. Objective & Problem Statement

- **The "Why":** Trong kiến trúc CSDL đối tượng phân tán, các ORM thường che giấu sự phân tán dữ liệu. Tuy nhiên, sai lầm N+1 Query sẽ bị khuếch đại khủng khiếp do phải chịu thêm **Network Latency** (Độ trễ truyền tải) và **Object Rehydration / Pointer Swizzling Cost** (Chi phí khôi phục con trỏ đối tượng trên RAM). Chúng tôi muốn đo lường sự chênh lệch hiệu năng giữa Lazy Loading (N+1) và Eager Loading (SQL JOIN) khi tăng độ trễ mạng.
- **Core Logic:** Chúng tôi cài đặt mô hình phân mảnh ngang (Horizontal Fragmentation) dựa trên ký tự đầu tiên của Tác giả. Triển khai cấu trúc LOID (Logical Object Identifier) qua UUID để định danh. Thuật toán Eager Loading sẽ sử dụng Batch JOIN cục bộ tại từng Node để tránh truy vấn chéo, giảm tổng số Network Call từ `N+1` xuống còn hằng số `3`.

## 3. Dataset Specification

- **Source:** [Kaggle (Goodreads Books Dataset May 2024)](https://www.kaggle.com/datasets/dk123891/books-dataset-goodreadsmay-2024/data?select=Book_Details.csv)
- **Size & Filtering:**
  - **Dataset gốc:** File CSV từ Kaggle có dung lượng ~22 MB.
  - **Dữ liệu thực tế:** Hệ thống chủ động lọc lấy **300 tác giả sáng tác nhiều sách nhất**.
  - **Số dòng (Rows):** Tổng cộng **~4,537 rows** (Bao gồm 300 tác giả và 4,237 cuốn sách).
- **Data Restructuring & Synthetic Fields:**
  - Dataset gốc là một bảng phẳng (Flat table), không có bảng Tác giả (`Author`). Chúng tôi đã dùng script trích xuất để tạo bảng `Author` độc lập, thiết lập quan hệ 1-N.
  - Tự động sinh thêm 2 trường dữ liệu giả lập (Synthetic Data) là `country` (Quốc gia) và `birth_year` (Năm sinh) để gia tăng độ phức tạp cho mô hình thực tế.
- **Schema:**
  - `Author`: OID (UUID), name, country, author_link, birth_year, created_at
  - `Book`: OID (UUID), author_oid (FK), title, average_rating, num_ratings, num_reviews, num_pages, genres, publication_info, description, cover_image_uri, created_at
- **Fragmentation Strategy:** Horizontal Range Partitioning trên trường `name` của Author.
  - Node A: `[A-H]`, Node B: `[I-P]`, Node C: `[Q-Z]`. Các đối tượng Sách được phân mảnh dẫn xuất (Derived Fragmentation) theo OID của Tác giả.

## 4. System Architecture

- **Nodes:** Chúng tôi triển khai 3 Sites (Node A, B, C) đóng vai trò là kho lưu trữ dữ liệu phân tán, kèm theo 1 Client Coordinator làm nhiệm vụ điều phối và đo lường.
- **Communication Layer:** Giao tiếp qua HTTP/REST APIs. Middleware tự động gài HTTP Header `X-Simulated-Latency` để ép trễ đường truyền nhân tạo.
- **Storage:** Xây dựng theo kiến trúc **Object-Server**. Mỗi Node sở hữu một Database SQLite hoàn toàn độc lập (`node_a.db`, `node_b.db`, `node_c.db`) lưu trên ổ cứng cục bộ. Có sử dụng cấu trúc Memory Cache kết hợp **Distributed Garbage Collection (TTL Sweeping)** để đồng bộ hóa và chống rò rỉ RAM.

## 5. Tech Stack & Implementation Plan

- **Programming Language:** Python 3.10+
- **Deployment:** Chạy dưới dạng Localhost Multi-processes (Mở các tiến trình độc lập bằng subprocess qua script `run_benchmark.py`).
- **Libraries/Frameworks:** Flask (để dựng REST API Networking), SQLAlchemy (làm ORM xử lý query & JOIN), Pandas (để xử lý ETL data ban đầu), Matplotlib (vẽ biểu đồ báo cáo).

## 6. Success Metrics & Analysis

- **Quantitative Metric:** Chúng tôi sẽ đo lường **Total execution time**, số lượng **Network calls**, và đặc biệt là bóc tách rành mạch **Object Rehydration Time** (Serialization tại Server + Deserialization / Pointer Swizzling tại Client) để lấy bằng chứng số liệu về điểm nghẽn CPU.
- **The "Failure" Scenario:** Để chứng minh tính bền bỉ của hệ thống phân tán (Fault Tolerance), chúng tôi sẽ thực hiện mô phỏng sự cố **Partial Failure (Lỗi một phần)**: Đang trong quá trình Client truy vấn toàn bộ dữ liệu, chúng tôi sẽ **tắt đột ngột (kill) Node B**. Hệ thống điều phối (Coordinator) sẽ được kỳ vọng không bị treo hoặc sập (Crash). Thay vào đó, nó sẽ kích hoạt cơ chế **Retry Policies** (Thử lại 3 lần), sau đó thực hiện **Graceful Degradation** (Suy thoái nhẹ): Báo cáo Node B thất bại (Failed Nodes) nhưng **vẫn gộp và trả về thành công** dữ liệu từ Node A và Node C cho người dùng. Kịch bản này chứng minh hệ thống ORM Phân tán vẫn duy trì được tính Khả dụng (Availability) ngay cả khi mất một mảnh dữ liệu.

## 7. Project Milestones

- **Milestone 1 (Week 5):** Hoàn tất ETL Pipeline để lọc, gắn UUID và phân mảnh dữ liệu Goodreads vào 3 database độc lập. Dựng các API gốc.
- **Milestone 2 (Week 8):** Triển khai xong Client Coordinator, logic Lazy Loading (N+1), Eager Loading (cấp độ SQL JOIN). Hoàn thiện Cache và Garbage Collection.
- **Milestone 3 (Week 12):** Hoàn thiện bộ Benchmark, gài độ trễ mạng, xuất biểu đồ báo cáo và giao diện Web Dashboard (nếu có). Nộp báo cáo.


---

# Tài liệu Thiết kế: Vấn Đề N+1 trong ORM Phân Tán

*Đề tài 85 – Cập nhật (Dataset Goodreads)*

## 0. Thông tin Dataset (Goodreads)

### Kích thước & Lọc dữ liệu (Data Sizing & Filtering)
- **Dataset gốc:** Trích xuất từ Kaggle Goodreads (File gốc dung lượng ~22 MB).
- **Kích thước thực tế sử dụng:** Hệ thống đã lọc lấy **300 tác giả hàng đầu (sáng tác nhiều sách nhất)** để đảm bảo đồ thị đối tượng đủ độ sâu.
- **Số dòng thực tế (Rows):** Tổng cộng **~4,537 rows**, bao gồm:
  - 300 dòng (Tác giả).
  - 4,237 dòng (Sách của 300 tác giả này).

### Tái cấu trúc Dữ liệu (Data Restructuring)
Dataset gốc trên Kaggle là một bảng phẳng (Flat table), **hoàn toàn không có bảng Tác giả (Author table)** độc lập. Để phục vụ bài toán Phân tán Đối tượng (Complex Object), chúng tôi đã thực hiện:
1. **Tự tạo bảng `Author`:** Tách cột tác giả từ bảng sách ra thành một bảng riêng biệt để tạo lập quan hệ Cha-Con (1-N).
2. **Thêm dữ liệu giả lập (Synthetic Data):** Dataset gốc thiếu thông tin cá nhân của tác giả. Để cấu trúc dữ liệu thêm phần thực tế và phức tạp, chúng tôi đã viết script tự động "bịa" (generate) thêm 2 trường thông tin: 
   - `country` (Quốc gia của tác giả).
   - `birth_year` (Năm sinh của tác giả).

---

## 1. Thiết kế Mô hình Đối tượng (§ 15.1)

### Định danh đối tượng (Object Identity - § 15.1.1 & § 15.5.0.1)
Mọi đối tượng đều có một **OID dựa trên UUID (v4)** – đóng vai trò là một định danh logic (Logical OID - LOID). Chúng tôi không sử dụng ID tự tăng (Auto-increment) để đảm bảo OID mang tính **độc nhất toàn cục** trên toàn mạng phân tán.
- **Tính bất biến (Invariant Property)**: Định danh tồn tại vĩnh viễn và không bao giờ thay đổi dù trạng thái đối tượng bị chỉnh sửa.
- **Độc lập vị trí**: LOID không gắn chặt với địa chỉ vật lý của đĩa, cho phép gộp dữ liệu hoặc di trú (migrate) an toàn mà không gãy khóa ngoại.

### Trạng thái & Phức hợp đối tượng (§ 15.1.3)
```
Author = ⟨OID, state={name, country, author_link, birth_year, created_at}, books=[Book]⟩
Book   = ⟨OID, state={title, average_rating, num_ratings, num_reviews, num_pages, genres, publication_info, description, cover_image_uri, created_at}, author_oid⟩
```

`Author` là một **đối tượng phức hợp (composite object)** chứa một tập hợp các đối tượng `Book` thông qua chia sẻ tham chiếu (khóa ngoại `author_oid`). Mối quan hệ phức hợp này là chìa khóa của vấn đề N+1: việc truy cập vào các `Book` lồng nhau yêu cầu các truy vấn bổ sung nếu không nạp trước.

### Chi phí Nạp lại & Tuần tự hóa (Pointer Swizzling & JSON Serialization)
Trong môi trường hệ thống không đồng nhất, quá trình biến đổi Object thành Data được thực hiện qua JSON với ba giai đoạn đo lường khắt khe:
- `Server Serialization`: Chuyển đổi trạng thái từ Python Object thành chuỗi JSON (Đóng gói).
- `Network I/O`: Độ trễ đường truyền tải mạng thuần túy.
- `Client Deserialization (Pointer Swizzling)`: Quá trình khôi phục chuỗi JSON thành Python Object trên RAM, phân giải các OID thành con trỏ bộ nhớ cục bộ (Theo mục § 15.4.2 của sách Özsu). Việc bóc tách chỉ số này giúp đo lường chính xác lượng tài nguyên CPU bị vắt kiệt do Context Switching khi chạy Lazy Loading (N+1).



## 2. Thiết kế Phân tán (§ 15.2)

### Phân mảnh ngang (Horizontal Fragmentation)
Áp dụng **phân mảnh ngang dựa trên dải (range-based)** cho lớp `Author`. Vị trí phân mảnh dựa trên ký tự đầu tiên của thuộc tính `name`:

```
Fragment_A = σ_{name[0] ∈ [A,H]}(Author) -> Node A (Port 5001)
Fragment_B = σ_{name[0] ∈ [I,P]}(Author) -> Node B (Port 5002)
Fragment_C = σ_{name[0] ∈ [Q,Z]}(Author) -> Node C (Port 5003)
```

**Phân mảnh Dẫn xuất (Derived Fragmentation - § 15.2):** Sách yêu cầu *"Optimization requires locating objects accessed together in the same fragment"*. Do đó, các đối tượng `Book` được cấp phát cùng vị trí với `Author` cha của chúng. Điều này đảm bảo Eager Loading có thể thực thi **JOIN cục bộ (Local Join)** bên trong mỗi Node mà không sinh ra thảm họa Cross-node Join.

### Cấp phát (Allocation)
Mỗi phân đoạn được cấp phát cho chính xác một nút (không có bản sao/replication). Hàm cấp phát `get_node_index(name)` ánh xạ một cách xác định bất kỳ tên Author nào đến đúng nút tương ứng thông qua ký tự đầu tiên.



## 3. Kiến trúc Lưu trữ & Quản lý Bộ đệm (§ 15.3 & § 15.5)

### Kiến trúc Object-Server (§ 15.3.1)
Thay vì sử dụng mô hình Page-Server (gửi nguyên các trang đĩa chứa byte thô qua mạng), hệ thống của chúng tôi được thiết kế chuẩn theo kiến trúc **Object-Server**. Nút Server chịu trách nhiệm thi hành truy vấn (`.outerjoin`), lọc dữ liệu và đóng gói toàn bộ đồ thị đối tượng (Object Graph) thành chuỗi JSON lồng nhau hoàn chỉnh trước khi gửi cho Client.

### Nhất quán Bộ nhớ đệm và Thu gom rác (§ 15.3.2 & § 15.5.0.2)
Hệ thống có triển khai **DistributedCache** (`cache_manager.py`) cho mỗi Node, giải quyết các rào cản phân tán:
1. **Cache Consistency (Tính nhất quán Bộ nhớ đệm)**: Để tránh tình trạng dữ liệu rác (Stale Data), hệ thống áp dụng cơ chế *Time-based Invalidation* thay vì Callback Locking. Giới hạn đối đa 1000 đối tượng và dùng TTL = 300s.
2. **Distributed Garbage Collection (Thu gom rác)**: Sách chỉ ra rằng thuật toán thụ động *Reference Counting* rất dễ gây rò rỉ bộ nhớ (Memory Leak) khi vòng lặp tham chiếu không rớt về 0. Do đó, hệ thống dùng cơ chế **Tracing/Sweeping chủ động**: Tích hợp hàm `gc_sweep()` định kỳ quét toàn bộ RAM và dọn sạch đối tượng quá hạn, đảm bảo Server có thể chạy liên tục 24/7.


