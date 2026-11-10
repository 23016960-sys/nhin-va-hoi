# Đưa Nhìn & Hỏi lên Render

Thư mục này là gốc của repository triển khai. Chỉ đưa nội dung dự án này lên GitHub, không đưa toàn bộ workspace bài tập.

## Cấu hình dịch vụ

- Loại: Web Service, runtime Python, gói Free.
- Python: `.python-version` chọn 3.11 để tương thích thư viện hiện tại.
- Build: `pip install -r requirements-render.txt && python download_assets.py --render`
- Start: `gunicorn -c gunicorn.conf.py wsgi:app`
- Health check: `/healthz`
- Biến môi trường: `PUBLIC_DEPLOYMENT=1`, `MAX_SESSIONS=3`, `OMP_NUM_THREADS=2`, `OPENBLAS_NUM_THREADS=1`.
- Nếu triển khai bằng Blueprint, dùng `render.yaml` có sẵn.

Gunicorn lắng nghe `0.0.0.0` và cổng `PORT` của Render. Chỉ chạy **1 worker**, vì thông tin ảnh được giữ trong RAM của tiến trình; nhiều worker có thể gây lỗi ảnh không còn trong phiên. Hai thread phục vụ các yêu cầu và mô hình ảnh được khóa khi suy luận.

Trong lúc build, chỉ tải YOLOv5s, ảnh mẫu và giấy phép đi kèm. Không cần tải SSD/YOLOv5n cho website. Không tải mô hình khi người dùng gửi ảnh.

## Dữ liệu ảnh

Ở bản online, trình duyệt gửi ảnh lên máy chủ Render để xử lý. Ứng dụng không ghi ảnh tải lên thành file, chỉ giữ dữ liệu phiên trong RAM. Phiên hết hạn sau 20 phút, được dọn khi có yêu cầu tiếp theo; cấu hình demo giữ tối đa 3 ảnh gần nhất trên toàn tiến trình. Khi có nhiều người dùng, ảnh cũ có thể bị loại sớm. Khởi động lại dịch vụ cũng làm mất phiên, người dùng cần tải lại ảnh.

Đây là ứng dụng demo, chưa có đăng nhập hay giới hạn lượt truy cập theo người dùng. Không sử dụng để lưu trữ ảnh lâu dài. Mô hình và các tệp nguồn giữ nguyên giấy phép trong LICENSE và THIRD_PARTY.md.

## Kiểm tra sau triển khai

1. Mở địa chỉ HTTPS mà Render cấp và kiểm tra trạng thái sẵn sàng.
2. Bấm Dùng ảnh mẫu, kiểm tra 4 khung người.
3. Hỏi Người số 2 mặc áo màu gì? Kết quả dự kiến be/kem.
4. Thử ảnh riêng và câu hỏi đếm người.
5. Kiểm tra `/healthz` trả `{"ok": true}`.

Render Free sẽ ngủ sau 15 phút không có truy cập và cần thời gian khởi động khi truy cập lại. Mở web trước buổi demo; không dùng dịch vụ gửi ping định kỳ để tránh ngủ.

Tài liệu: https://render.com/docs/deploy-flask ; https://render.com/docs/free ; https://render.com/docs/python-version
