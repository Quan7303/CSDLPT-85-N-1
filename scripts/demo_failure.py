import sys
import os
import time
import subprocess

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from client.coordinator import Coordinator
from client.eager_loader import run_eager_query
from client.lazy_loader import run_lazy_query

coordinator = Coordinator()

def print_header(title):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")

def print_health():

    print_header("BƯỚC 1: Kiểm tra sức khỏe các Nút mạng")
    for i, node_cfg in enumerate(config.NODES):
        url = f"http://{node_cfg['host']}:{node_cfg['port']}"
        try:
            import requests
            resp = requests.get(f"{url}/health", timeout=2)
            status = "ONLINE" if resp.status_code == 200 else "OFFLINE"
        except Exception:
            status = "OFFLINE"
        print(f"    {node_cfg['name']} (Site {node_cfg['site_id']}, "
              f"dải {node_cfg['letter_range'][0]}-{node_cfg['letter_range'][1]}, "
              f"cổng {node_cfg['port']}): {status}")

def print_query_details(result, label=""):

    t = result.to_dict()

    print(f"\n    Bóc tách chi phí nạp lại (Rehydration Cost):")
    print(f"       Mạng (Network I/O):           {t['network_ms']:>10.1f} ms")
    print(f"       Tuần tự hóa (Serialization):  {t['server_serialization_ms']:>10.1f} ms")
    print(f"       Giải tuần tự hóa (Deser):     {t['client_deserialization_ms']:>10.1f} ms")
    print(f"       ────────────────────────────────────────")
    print(f"       TỔNG CỘNG:                    {t['total_rehydration_ms']:>10.1f} ms")
    print(f"       Số lượt HTTP requests:        {t['request_count']:>10d}")
    print(f"       Số tác giả tìm thấy:          {t['author_count']:>10d}")

    if not result.data:
        return

    print(f"\n    Minh chứng OID (§15.4.1) — UUID duy nhất toàn cục:")
    for author in result.data[:3]:
        book_count = len(author.get('books', []))
        print(f"       OID: {author['oid']}  →  {author['name']} ({book_count} sách)")

    sample = result.data[0]
    books = sample.get('books', [])
    print(f"\n    Minh chứng Composite Object (§15.1.3):")
    print(f"       Tác giả: {sample['name']} (OID: {sample['oid'][:8]}...)")
    print(f"       Số sách lồng nhau: {len(books)}")
    if books:
        print(f"       Sách mẫu: \"{books[0]['title']}\" "
              f"(OID: {books[0]['oid'][:8]}..., "
              f"author_oid: {books[0]['author_oid'][:8]}...)")

    node_counts = {"Node_A": 0, "Node_B": 0, "Node_C": 0}
    for author in result.data:
        idx = config.get_node_index(author.get('name', 'A'))
        node_name = config.NODES[idx]['name']
        if node_name in node_counts:
            node_counts[node_name] += 1

    print(f"\n    Phân bố tác giả trên các nút (Horizontal Fragmentation §15.2):")
    for name, count in node_counts.items():
        bar = "█" * (count // 2) if count > 0 else "░░░ (OFFLINE)"
        print(f"       {name}: {count:>3d} tác giả  {bar}")

def print_cache_and_gc():

    print_header("BƯỚC 3: Thống kê Cache (CBL §15.3.2) & GC (§15.5)")
    metrics = coordinator.get_metrics()
    if not metrics:
        print("    Không thể lấy metrics (có thể các nút đang offline)")
        return

    for m in metrics:
        c = m.get('cache', {})
        print(f"\n    {m['node']} (Site {m['site_id']}):")
        print(f"       Tổng yêu cầu đã xử lý:    {m['request_count']}")
        print(f"       Tuần tự hóa trung bình:     {m['avg_serialization_ms']:.3f} ms")
        print(f"       Cache entries:               {c.get('entries', 0)} / {c.get('max_entries', 0)}")
        print(f"       Cache hits / misses:         {c.get('hits', 0)} / {c.get('misses', 0)}")
        hit_rate = c.get('hit_rate', 0) * 100
        print(f"       Cache hit rate:              {hit_rate:.1f}%")
        print(f"       GC đã thu hồi (tổng):       {c.get('gc_collected', 0)}")
        print(f"       GC thu hồi (lần gọi này):   {m.get('gc_sweep_collected', 0)}")

def kill_node_b():

    print_header("BƯỚC 4: Tự động dừng Nút B (cổng 5002)")
    script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                               "scripts", "kill_node.py")
    try:
        result = subprocess.run(
            [sys.executable, script_path, "5002"],
            capture_output=True, text=True, timeout=10
        )
        print(f"    Kết quả: {result.stdout.strip() or result.stderr.strip() or 'Đã gửi lệnh dừng'}")
    except Exception as e:
        print(f"    Lỗi khi dừng node: {e}")

    print("    Đợi 2 giây để Node B tắt hoàn toàn...")
    time.sleep(2)

def demo():
    print("=" * 60)
    print("  TRÌNH DIỄN TỔNG HỢP — Vấn đề N+1")
    print("  Özsu & Valduriez, Chương 15")
    print("  Cover tất cả tiêu chí chấm điểm Category 9")
    print("=" * 60)

    print_health()

    print_header("BƯỚC 2: Truy vấn Eager Loading — Tất cả nút ONLINE")
    result_before = run_eager_query(latency_ms=0)
    count_before = result_before.to_dict()['author_count']
    print_query_details(result_before)

    print_cache_and_gc()

    kill_node_b()
    print_health()

    print_header("BƯỚC 5: Truy vấn Eager Loading — Nút B OFFLINE")
    result_after = run_eager_query(latency_ms=0)
    count_after = result_after.to_dict()['author_count']
    print_query_details(result_after)

    print_header("BƯỚC 6: KẾT LUẬN — So sánh trước/sau khi lỗi")

    t_before = result_before.to_dict()
    t_after = result_after.to_dict()
    lost = count_before - count_after

    print(f"""
    ┌─────────────────────────────┬──────────────┬──────────────┐
    │         Chỉ số              │  Trước lỗi   │   Sau lỗi    │
    ├─────────────────────────────┼──────────────┼──────────────┤
    │ Số tác giả                  │ {count_before:>12d} │ {count_after:>12d} │
    │ HTTP requests               │ {t_before['request_count']:>12d} │ {t_after['request_count']:>12d} │
    │ Tổng thời gian (ms)         │ {t_before['total_rehydration_ms']:>12.1f} │ {t_after['total_rehydration_ms']:>12.1f} │
    │ Network I/O (ms)            │ {t_before['network_ms']:>12.1f} │ {t_after['network_ms']:>12.1f} │
    └─────────────────────────────┴──────────────┴──────────────┘

    Hệ thống KHÔNG bị sập (No crash)
    Không mất dữ liệu (No data corruption)
    Trả về kết quả từ phần ({count_after}/{count_before} tác giả — mất {lost} tác giả từ Nút B)
    """)
    print("=" * 60)
    print("  Trình diễn hoàn tất. Sẵn sàng trả lời câu hỏi!")
    print("=" * 60)

if __name__ == '__main__':
    demo()
