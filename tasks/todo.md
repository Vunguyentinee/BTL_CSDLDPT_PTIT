# Danh sách việc — CBIR ảnh cá

> Chi tiết từng việc: `tasks/plan.md` · Cập nhật 13/10/2026
> Quy ước: `[ ]` chưa làm · `[~]` đang làm · `[x]` xong và đã nghiệm thu

## ✅ Đã xong — giai đoạn dữ liệu

- [x] Chốt 20 loài / 11 họ, sinh mã loài, tra `inat_taxon_id`
- [x] Thu thập 4.768 ảnh thô từ FishBase, iNaturalist, Archive
- [x] Chuẩn hóa 384×384 RGBA (cá 348px, đầu trái, lưng trên, alpha là mask)
- [x] Duyệt tay 3.486 ảnh, nhận 1.105
- [x] Bỏ 2 loài không đủ nguồn (`CLA_BAT` 9 ảnh, `PAM_ARG` 11 ảnh)
- [x] **Bộ dữ liệu chốt: 1.085 ảnh / 20 loài**
- [x] Chốt kiến trúc và mô hình dữ liệu theo khung bài giảng → `docs/kien-truc-va-mo-hinh-du-lieu.md`

---

## Giai đoạn 1 — Nền móng và lát cắt dọc đầu tiên

- [ ] **T1** Khung package `fishcbir` (nạp danh mục, nạp ảnh, cấu hình `.env`) · S · NT
- [ ] **T2** Chia 5-fold **phân tầng theo loài**, seed cố định → `data_meta/splits/folds.csv` · S · NT
- [ ] **T3** Đặc trưng ① color moments Lab 9 chiều, chỉ trên mask · S · TV-A
- [ ] **T4** Tìm kiếm top-5 NumPy + Precision@5 macro, **loại self-match** · M · NT

### ✅ Chốt chặn 1 — toàn tuyến thông
- [ ] Có con số Precision@5 đầu tiên
- [ ] Không ảnh nào tự khớp chính nó
- [ ] Mọi loài có mặt ở cả 5 fold
- [ ] P@5 cao hơn mức ngẫu nhiên 5% rõ rệt
- [ ] **Báo nhóm trước khi làm tiếp**

---

## Giai đoạn 2 — Đủ bộ đặc trưng

- [ ] **T5** Màu: ② histogram HSV 4 dải + ③ màu trội k-means (276 chiều) · M · TV-A
- [ ] **T6** Kết cấu: ④ LBP 3 bán kính + ⑤ GLCM 4 hướng + ⑥ Gabor (118 chiều) · M · TV-A
- [ ] **T7** Hình dáng: ⑦ tỉ số + ⑧ Hu + ⑨ Fourier + ⑩ contour (98 chiều) · M · TV-B
- [ ] **T8** Bộ B ResNet18 512 chiều + PCA · S · TV-B
- [ ] **T9** Bộ C: 20 loài × 10 thuộc tính ngữ nghĩa, duyệt chéo · M · cả nhóm
- [ ] **T10** Chuẩn hóa khối + độ đo theo loại + hợp nhất có trọng số · M · NT

### ✅ Chốt chặn 2 — ablation chạy được
- [ ] 6 cấu hình ra số: màu / kết cấu / hình dáng / ghép cổ điển / deep / hợp nhất
- [ ] Hợp nhất tốt hơn từng khối riêng
- [ ] Không khối nào sinh NaN hay vector toàn 0
- [ ] **Báo nhóm trước khi làm tiếp**

---

## Giai đoạn 3 — Cơ sở dữ liệu

- [ ] **T11** Docker PostgreSQL 17 + pgvector, 4 bảng, một cột vector mỗi khối · S · NT
- [ ] **T12** Nạp dữ liệu + `verify_integrity` (bảng ↔ thư mục ảnh) · S · NT
- [ ] **T13** Index HNSW, đo **thời gian và recall** so với quét tuần tự · S · NT
  - số liệu này dùng để trả lời phản biện "sao không dùng vector DB chuyên dụng" 

### ✅ Chốt chặn 3 — CSDL vận hành đúng
- [ ] `verify_integrity` sạch
- [ ] Backend pgvector và NumPy cho kết quả giống hệt
- [ ] Có bảng số thời gian truy vấn và recall

---

## Giai đoạn 4 — Web demo

- [ ] **T14** Tab Tìm kiếm: upload → top-5 + điểm số + ngưỡng "không tìm thấy" · M · NT
  - **TTA đa giả thuyết hướng** hai tầng (80 chiều rẻ chấm 4–8 biến thể → 1.013 chiều cho biến thể thắng)
  - nút a/w/d/s chỉ là tùy chọn ghi đè, mặc định tắt — hệ tự động hoàn toàn
- [ ] **T15** Tab Giải thích: mask, histogram, LBP, contour, **bảng phân rã khoảng cách**, Grad-CAM · M · TV-A + TV-B

### ✅ Chốt chặn 4 — chạy được trên máy khác
- [ ] Máy sạch: `docker compose up` + `streamlit run` là chạy
- [ ] Thử trên máy chỉ có CPU
- [ ] Backend dự phòng chạy khi tắt Docker

---

## Giai đoạn 5 — Đánh giá

- [ ] **T16** P@1/@5/@10, Recall@10, mAP — 5-fold, macro-average, kèm độ lệch chuẩn · M · TV-A
  - **ablation hướng**: P@5 của máy-một-giả-thuyết / TTA / hướng người duyệt (mức trần)
  - độ chính xác `doan_huong` theo loài, đối chiếu cột `tu_the` đã có trong review CSV
- [ ] **T17** Ablation 6 cấu hình + Fisher 3 cột + Fisher theo cặp loài cùng họ · M · TV-A
- [ ] **T18** Phân loại top-1 + ma trận nhầm lẫn chuẩn hóa + P@5 theo họ + ảnh ngoài CSDL · M · TV-B

### ✅ Chốt chặn 5 — đủ số liệu
- [ ] Mọi bảng số xuất ra file, tái lập bằng một lệnh
- [ ] Ba quy tắc trung thực được tuân thủ

---

## Giai đoạn 6 — Báo cáo

- [ ] **T19** Báo cáo tiến độ 1 — **hạn 22/10, còn 9 ngày** · M
- [ ] **T20** Báo cáo tiến độ 2 — hạn 26/11 · M
- [ ] **T21** Báo cáo tổng + demo — hạn 15/12 · L
  - đưa mục kiến trúc & mô hình dữ liệu vào báo cáo, nguồn: `docs/kien-truc-va-mo-hinh-du-lieu.md`
  - ôn bảng tóm tắt 11 câu hỏi vấn đáp ở phần 4 của tài liệu đó

---

## Việc phải làm trước mốc 22/10 (9 ngày)

Đây là đường găng gần nhất. Mốc 1 chỉ cần phần 1 và 2 của đề:

- [ ] **T9** Bộ C — nguyên liệu cho phần "mô tả giống/khác nhau" ← **bắt đầu ngay**
- [ ] T1 → T4 — để báo cáo có con số đầu tiên, không chỉ là thiết kế trên giấy
- [ ] T19 — viết báo cáo

T5–T8 chưa cần xong trước 22/10, chỉ cần **trình bày thiết kế** của chúng.

---

## Chờ quyết

- [ ] Bổ sung ảnh cho 7 loài dưới 30 ảnh? *(khuyến nghị: không — 5-fold đã bù phần lớn)*
- [ ] Làm CLIP làm hệ đối chứng thứ ba? *(quyết sau T8)*
- [ ] Phân công lại 20 loài cho 3 người sau khi bỏ 2 loài
