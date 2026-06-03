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
Book   = ⟨OID, state={title, average_rating, num_ratings, num_reviews, num_pages, genres, publication_info, publication_date, description, cover_image_uri, created_at}, author_oid⟩
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


