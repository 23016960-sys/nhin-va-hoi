# Nhìn & Hỏi

Ứng dụng web hỏi đáp bằng tiếng Việt về người trong ảnh. Dùng YOLOv5s để phát hiện người, HSV để ước lượng màu trang phục, TF-IDF và hồi quy logistic kết hợp quy tắc để hiểu câu hỏi.

## Triển khai Render

Xem [hướng dẫn](HUONG_DAN_RENDER.md). Repository đã có `render.yaml` dành cho Web Service Free.

- Build: `pip install -r requirements-render.txt && python download_assets.py --render`
- Start: `gunicorn -c gunicorn.conf.py wsgi:app`
- Python 3.11; health check `/healthz`.
- `PUBLIC_DEPLOYMENT=1`, `MAX_SESSIONS=3`, `OMP_NUM_THREADS=2`, `OPENBLAS_NUM_THREADS=1`.

## Chạy local

Cài Python 3.11, tạo môi trường ảo, rồi chạy:

```sh
pip install -r requirements.txt
python download_assets.py --render
python app.py
```

Mở http://127.0.0.1:7861 và bấm Dùng ảnh mẫu. Thử hỏi Người số 2 mặc áo màu gì?

## Phạm vi

Hỗ trợ đếm người, hỏi vị trí, hỏi màu áo/quần và tìm người theo màu. Màu là ước lượng, có thể sai do ánh sáng, vùng cắt hay che khuất. Câu hỏi phủ định chưa được xử lý đầy đủ. Mô hình YOLO đã huấn luyện sẵn, không do dự án tự huấn luyện.

Ở bản online, ảnh được gửi tới máy chủ và giữ tạm trong RAM; không ghi ảnh tải lên thành file. Phiên mất khi dịch vụ khởi động lại hoặc ảnh cũ bị loại. Đây là bản demo, chưa có đăng nhập hay hạn mức theo người dùng.

Mã dự án theo AGPL-3.0. Xem LICENSE và THIRD_PARTY.md về thành phần bên thứ ba.
