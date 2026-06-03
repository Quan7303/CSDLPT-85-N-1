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
