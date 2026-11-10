# Nguồn thành phần

- YOLOv5 v7.0: https://github.com/ultralytics/yolov5/tree/v7.0 ; trọng số ONNX v5s và v5n từ bản phát hành https://github.com/ultralytics/yolov5/releases/tag/v7.0 . Giấy phép GPL-3.0 lưu tại `models/LICENSE-YOLOv5.txt`. Mô hình pretrained trên COCO, chỉ lấy lớp person; không huấn luyện lại trong dự án.
- MobileNet-SSD: https://github.com/chuanqi305/MobileNet-SSD ; giấy phép MIT trong `models/LICENSE-MobileNet-SSD.txt`. Dùng làm baseline, không là backend mặc định.
- Ảnh bus.jpg: https://github.com/ultralytics/assets/blob/main/im/bus.jpg ; giấy phép repository AGPL-3.0 được giữ tại `samples/LICENSE-Ultralytics.txt`. Dùng ảnh mẫu và kiểm tra chức năng; không phải ảnh tự chụp.
- Flask: https://flask.palletsprojects.com/ ; BSD-3-Clause.
- ONNX Runtime: https://onnxruntime.ai/ ; MIT.
- OpenCV: https://opencv.org/ ; Apache-2.0 đối với phiên bản sử dụng.
- scikit-learn: https://scikit-learn.org/ ; BSD-3-Clause.
- NumPy, Pillow, Werkzeug, joblib: giấy phép theo bản phân phối PyPI tương ứng.

`asset_manifest.json` lưu URL và SHA-256 tài nguyên. Nhãn ảnh thô và bộ câu hỏi kiểm tra trong `evaluation/` được viết riêng cho kiểm tra quy mô nhỏ. Không sử dụng các kết quả này để khẳng định chất lượng trên tập dữ liệu lớn.
