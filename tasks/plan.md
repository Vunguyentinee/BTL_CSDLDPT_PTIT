# Kế hoạch hiện thực — Hệ CSDL tìm kiếm ảnh cá (CBIR)

> Lập ngày 13/10/2026. Giai đoạn dữ liệu đã xong; tài liệu này phủ phần còn lại tới khi nộp bài.
> Quyết định thiết kế: `docs/intent/fish-image-retrieval.md` · Quy trình: `docs/plan/ke-hoach.md`

## Tổng quan

Xây hệ tìm kiếm ảnh theo nội dung: đưa vào một ảnh cá, trả về 5 ảnh giống nhất trong CSDL. Hiện đã có **1.085 ảnh / 20 loài / 11 họ**, chuẩn hóa 384×384 PNG RGBA (cá dài 348px, đầu trái, lưng trên, kênh alpha là mask). Việc còn lại: trích đặc trưng, dựng CSDL, module tìm kiếm, web demo, đánh giá, và ba báo cáo.

Thời gian còn lại tính từ 13/10: **9 ngày** tới mốc 1, **44 ngày** tới mốc 2, **63 ngày** tới mốc cuối.

## Quyết định kiến trúc

| Quyết định | Lý do |
|---|---|
| **Cắt dọc, không cắt ngang** — làm trọn một tuyến "đặc trưng → CSDL → tìm kiếm → chỉ số" với một đặc trưng đơn giản nhất trước, rồi mới thêm các khối còn lại | Có con số Precision@5 đầu tiên trong vài ngày thay vì vài tuần. Mọi sai sót về đường ống lộ ra sớm, khi còn rẻ để sửa |
| **PostgreSQL 17 + pgvector** qua Docker, kèm backend NumPy dự phòng | Mô hình **Object-Relational + Vector** theo đúng Lecture 5 tr.40–42: PostgreSQL là ví dụ ORDBMS, pgvector là phần mở rộng đưa ORDBMS tới similarity search. Lập luận đầy đủ: `docs/kien-truc-va-mo-hinh-du-lieu.md`. Backend NumPy dự phòng để demo không chết vì Docker |
| Kiến trúc **centralized** + storage principle **homogeneity** | Theo khung Lecture 4 tr.5 và tr.12. Một loại phương tiện duy nhất nên separation không áp dụng |
| **5-fold phân tầng** thay vì chia gallery/query 80/20 một lần | Cho 1.085 truy vấn thay vì ~217, từ chính dữ liệu đang có. Loài 19 ảnh có 19 truy vấn thay vì 4 |
| **Macro-average** mọi chỉ số | Lớp lệch 8,5 lần; micro-average sẽ để cá dĩa 162 ảnh át cá lóc 19 ảnh |
| Đặc trưng lưu **mỗi khối một cột vector riêng** trong CSDL | Để chạy ablation và bảng phân rã khoảng cách mà không phải trích lại |
| Trọng số hợp nhất dò **bên trong từng fold** | Dò trên toàn bộ rồi đánh giá trên toàn bộ là rò rỉ dữ liệu |

## Đồ thị phụ thuộc

```
species.csv + work/chuan/ (ĐÃ CÓ)
    │
    ├── T1 khung package fishcbir
    │     │
    │     ├── T2 chia 5-fold ──────────────┐
    │     │                                │
    │     └── T3 đặc trưng ① color moments │
    │               │                      │
    │               └── T4 tìm kiếm + P@5 ◄┘   ◄── LÁT CẮT DỌC ĐẦU TIÊN
    │                     │
    │        ┌────────────┼────────────┬──────────────┐
    │        │            │            │              │
    │     T5 màu      T6 kết cấu   T7 hình dáng   T8 deep
    │        └────────────┴────────────┴──────────────┘
    │                     │
    │              T10 chuẩn hóa + hợp nhất
    │                     │
    │        ┌────────────┴────────────┐
    │     T11-13 CSDL              T16-18 đánh giá
    │        │                          │
    │     T14-15 demo ──────────────────┤
    │                                   │
    └── T9 Bộ C ngữ nghĩa ──────────────┘
                                        │
                              T19-21 ba báo cáo
```

---

# Giai đoạn 1 — Nền móng và lát cắt dọc đầu tiên

Mục tiêu: chứng minh **toàn tuyến chạy được** với đặc trưng đơn giản nhất, trước khi đầu tư vào 9 đặc trưng còn lại.

## T1 — Khung package `fishcbir`

**Mô tả:** Dựng bộ khung module, nạp danh mục loài và danh sách ảnh, cấu hình đường dẫn qua `.env`.

**Tiêu chí nghiệm thu:**
- [ ] `fishcbir.data.nap_danh_muc()` trả về 20 loài với mã, họ, tên Việt
- [ ] `fishcbir.data.nap_anh()` trả về 1.085 đường dẫn kèm nhãn loài
- [ ] Đọc đường dẫn từ `.env`, không ghi cứng

**Kiểm chứng:** `python -c "from fishcbir.data import *; print(len(nap_anh()))"` in ra `1085`

**Phụ thuộc:** Không · **Quy mô:** S · **Người:** NT

**File:** `fishcbir/__init__.py`, `fishcbir/data.py`, `fishcbir/config.py`

---

## T2 — Chia 5-fold phân tầng

**Mô tả:** Chia 1.085 ảnh thành 5 phần, **phân tầng theo loài** để mỗi fold có tỉ lệ loài như nhau. Seed cố định, lưu ra file để mọi lần chạy đều dùng chung một cách chia.

**Tiêu chí nghiệm thu:**
- [ ] `data_meta/splits/folds.csv` có đúng 1.085 dòng, cột `image_id`, `ma_loai`, `fold` (0–4)
- [ ] Mỗi loài phân bố đều qua 5 fold, lệch không quá 1 ảnh
- [ ] Chạy lại cho kết quả giống hệt (seed cố định)

**Kiểm chứng:** script in bảng số ảnh mỗi loài × mỗi fold; kiểm bằng mắt không fold nào thiếu loài nào

**Phụ thuộc:** T1 · **Quy mô:** S · **Người:** NT

**File:** `fishcbir/splits.py`, `scripts/chia_fold.py`

> **Vì sao phải phân tầng:** chia ngẫu nhiên thuần có thể khiến một fold không có ảnh cá lóc nào (19 ảnh / 5 fold ≈ 4 ảnh/fold). Khi đó fold ấy không đánh giá được loài đó.

---

## T3 — Đặc trưng ① Color moments (9 chiều)

**Mô tả:** Trích mô men màu bậc 1–3 trên không gian Lab, **chỉ tính trên pixel trong mask** (kênh alpha). Đơn giản nhất trong 10 đặc trưng, dùng để thông tuyến.

**Tiêu chí nghiệm thu:**
- [ ] Vector đúng 9 chiều, không có NaN trên cả 1.085 ảnh
- [ ] Ảnh cùng loài có khoảng cách trung bình nhỏ hơn ảnh khác loài (kiểm thô)
- [ ] Trích hết 1.085 ảnh dưới 2 phút

**Kiểm chứng:** `pytest tests/test_mau.py` — ảnh toàn đỏ cho `a` dương lớn; lật ngang ảnh không đổi giá trị (bất biến vị trí)

**Phụ thuộc:** T1 · **Quy mô:** S · **Người:** TV-A

**File:** `fishcbir/features/mau.py`, `tests/test_mau.py`

---

## T4 — Tìm kiếm top-5 + Precision@5 macro

**Mô tả:** Tìm kiếm brute-force bằng NumPy trên vector đặc trưng, loại self-match, chạy qua 5 fold, tính Precision@5 macro-average.

**Tiêu chí nghiệm thu:**
- [ ] `tim_kiem(vector, k=5)` trả về 5 ảnh gần nhất kèm khoảng cách
- [ ] **Ảnh truy vấn không bao giờ nằm trong kết quả của chính nó**
- [ ] In ra Precision@5 từng loài và macro-average
- [ ] Toàn bộ 1.085 truy vấn chạy dưới 10 giây

**Kiểm chứng:** truy vấn bằng một ảnh trong CSDL phải trả về 5 ảnh *khác*; P@5 phải cao hơn mức ngẫu nhiên (1/20 = 5%) rõ rệt

**Phụ thuộc:** T2, T3 · **Quy mô:** M · **Người:** NT

**File:** `fishcbir/search.py`, `fishcbir/eval/metrics.py`, `scripts/danh_gia.py`

---

## ✅ Chốt chặn 1 — Toàn tuyến thông

- [ ] Có con số Precision@5 đầu tiên, dù chỉ dùng 9 chiều màu
- [ ] Không có ảnh nào tự khớp với chính nó
- [ ] Mọi loài đều xuất hiện ở cả 5 fold
- [ ] **Báo cáo cho nhóm trước khi làm tiếp**

> Đây là chốt chặn quan trọng nhất. Nếu P@5 ở đây gần mức ngẫu nhiên 5%, có gì đó sai về căn bản — phải tìm ra trước khi viết thêm 9 đặc trưng.

---

# Giai đoạn 2 — Đủ bộ đặc trưng

## T5 — Nhóm màu: ② histogram 4 dải + ③ màu trội (276 chiều)

**Tiêu chí nghiệm thu:**
- [ ] ② chia thân cá thành 4 dải dọc trục đầu→đuôi, mỗi dải H 32 + S 16 + V 16 bin, **chuẩn hóa tổng = 1**
- [ ] ③ k-means k=5 trên Lab, **sắp xếp cụm theo tỉ lệ giảm dần** trước khi ghép vector
- [ ] Không NaN trên 1.085 ảnh

**Kiểm chứng:** `pytest tests/test_mau.py` — hai ảnh giống hệt phải cho vector ③ giống hệt (bắt lỗi thứ tự cụm ngẫu nhiên)

**Phụ thuộc:** T4 · **Quy mô:** M · **Người:** TV-A

---

## T6 — Nhóm kết cấu: ④ LBP + ⑤ GLCM + ⑥ Gabor (118 chiều)

**Tiêu chí nghiệm thu:**
- [ ] ④ LBP uniform xoay-bất biến ở 3 bán kính (P=8/R=1, P=16/R=2, P=24/R=3) = 54 chiều
- [ ] ⑤ GLCM 4 thuộc tính × 4 hướng = 16 chiều, **giữ nguyên 4 hướng, không lấy trung bình**
- [ ] ⑥ Gabor 4 tần số × 6 hướng × (mean, std) = 48 chiều
- [ ] **Tính trên mask đã co vào trong ~5px**, không lấy pixel ở biên

**Kiểm chứng:** ảnh có sọc dọc cho tỉ số GLCM contrast 0°/90° > 2; ảnh trơn cho tỉ số ≈ 1

**Phụ thuộc:** T4 · **Quy mô:** M · **Người:** TV-A

> **Vì sao phải co mask:** nền đã bị xóa nên ranh giới cá/nền là một cạnh cực sắc. Tính cả vào thì LBP và GLCM đo cái biên giả đó chứ không đo vảy cá.

---

## T7 — Nhóm hình dáng: ⑦ tỉ số + ⑧ Hu + ⑨ Fourier + ⑩ contour (98 chiều)

**Tiêu chí nghiệm thu:**
- [ ] ⑦ 7 tỉ số hình học, đều bất biến tỉ lệ
- [ ] ⑧ Hu moments đã nén `-sign(h)·log₁₀|h|`
- [ ] ⑨ Fourier: **lấy mẫu lại đường bao về 256 điểm**, bỏ F(0), chia |F(1)|, lấy modulus, giữ 20 hệ số
- [ ] ⑩ contour signature 64 mẫu, chia cho bán kính trung bình

**Kiểm chứng:** `pytest tests/test_hinh_dang.py` — hình tròn tổng hợp cho circularity ≈ 1; phóng to ảnh 2× không đổi vector

**Phụ thuộc:** T4 · **Quy mô:** M · **Người:** TV-B

---

## T8 — Bộ B: ResNet18 (512 chiều)

**Tiêu chí nghiệm thu:**
- [ ] Lấy đầu ra sau global average pooling, chuẩn hóa L2
- [ ] Trích hết 1.085 ảnh dưới 2 phút trên CPU
- [ ] PCA giảm xuống 128–256 chiều, lưu cả bản gốc lẫn bản PCA

**Kiểm chứng:** hai ảnh giống nhau cho cosine ≈ 1; ảnh khác loài cho cosine thấp hơn rõ rệt

**Phụ thuộc:** T4 · **Quy mô:** S · **Người:** TV-B

---

## T9 — Bộ C: 10 thuộc tính ngữ nghĩa

**Mô tả:** Gán tay 20 loài × 10 thuộc tính, dựa vào trang loài FishBase chứ không dựa vào một ảnh riêng lẻ.

**Tiêu chí nghiệm thu:**
- [ ] `data_meta/semantic_attributes.csv` đủ 20 dòng, không ô trống
- [ ] Mọi giá trị nằm trong miền đã định sẵn, không tự thêm giá trị mới
- [ ] Cột tỉ lệ dài:cao lấy **trung bình aspect ratio máy đã đo**, không ước lượng bằng mắt
- [ ] Mỗi người gán 7 loài rồi duyệt chéo

**Kiểm chứng:** script kiểm mọi ô thuộc miền hợp lệ; đối chiếu 7/10 thuộc tính với đặc trưng tự động

**Phụ thuộc:** T7 (cần aspect ratio) · **Quy mô:** M · **Người:** cả nhóm

---

## T10 — Chuẩn hóa khối, độ đo theo loại, hợp nhất

**Mô tả:** Z-score từng khối (mean/std tính **trên phần gallery của từng fold**), chọn độ đo theo loại đặc trưng, đưa khoảng cách về [0,1], hợp nhất có trọng số.

**Tiêu chí nghiệm thu:**
- [ ] Histogram dùng Chi-square hoặc Bhattacharyya; vector deep và mô men dùng cosine; tỉ số hình học dùng L2
- [ ] Trọng số dò bằng lưới **chỉ trên phần gallery của fold**, không chạm phần query
- [ ] Hàm `phan_ra_khoang_cach()` trả về khoảng cách từng khối cho một cặp ảnh

**Kiểm chứng:** tắt chuẩn hóa thì 256 chiều histogram phải lấn át 7 chiều Hu — chứng minh bước chuẩn hóa có tác dụng

**Phụ thuộc:** T5, T6, T7, T8 · **Quy mô:** M · **Người:** NT

---

## ✅ Chốt chặn 2 — Đủ đặc trưng, chạy được ablation

- [ ] 6 cấu hình chạy ra số: màu / kết cấu / hình dáng / ghép cổ điển / deep / hợp nhất
- [ ] Hợp nhất cho kết quả **tốt hơn** từng khối riêng lẻ
- [ ] Không khối nào sinh NaN hay vector toàn 0
- [ ] **Báo cáo cho nhóm trước khi làm tiếp**

---

# Giai đoạn 3 — Cơ sở dữ liệu

## T11 — Docker PostgreSQL + pgvector, lược đồ

**Tiêu chí nghiệm thu:**
- [ ] `docker compose up` dựng được CSDL trên máy sạch
- [ ] 4 bảng `species`, `images`, `features`, `feature_stats` kèm khóa ngoại và ràng buộc
- [ ] `features` có **một cột vector cho mỗi khối** (màu 285, kết cấu 118, hình dáng 98, deep 512)

**Kiểm chứng:** `\d features` trong psql hiện đúng kiểu `vector(n)`

**Phụ thuộc:** T10 · **Quy mô:** S · **Người:** NT

---

## T12 — Nạp dữ liệu và kiểm toàn vẹn

**Tiêu chí nghiệm thu:**
- [ ] 1.085 ảnh và 20 loài nạp đủ, không dòng nào thiếu vector
- [ ] `verify_integrity.py` đối chiếu bảng ↔ thư mục ảnh: không thiếu file, không file mồ côi, hash khớp
- [ ] Thứ tự ghi: **file trước, insert sau**, trong một giao dịch

**Kiểm chứng:** xóa thử một file ảnh → `verify_integrity` phải báo lỗi

**Phụ thuộc:** T11 · **Quy mô:** S · **Người:** NT

---

## T13 — Index HNSW và so sánh với quét tuần tự

**Tiêu chí nghiệm thu:**
- [ ] Tạo index HNSW trên cột deep
- [ ] Đo **thời gian và recall** của HNSW so với quét tuần tự chính xác
- [ ] Backend NumPy dự phòng cho kết quả **giống hệt** backend pgvector
- [ ] Số liệu đủ để trả lời phản biện "sao không dùng vector database chuyên dụng" (xem `docs/kien-truc-va-mo-hinh-du-lieu.md` phần 5)

**Kiểm chứng:** 1.085 truy vấn qua hai backend, so từng kết quả top-5

**Phụ thuộc:** T12 · **Quy mô:** S · **Người:** NT

> Ở 1.085 vector, nhiều khả năng HNSW **không nhanh hơn** quét tuần tự và còn giảm recall. Nếu đo ra như vậy thì đó là **bằng chứng thực nghiệm cho lựa chọn kiến trúc tập trung**, không phải thất bại.

---

## ✅ Chốt chặn 3 — CSDL vận hành đúng

- [ ] `verify_integrity` sạch
- [ ] Hai backend cho kết quả giống hệt
- [ ] Có bảng số thời gian truy vấn và recall

---

# Giai đoạn 4 — Web demo

## T14 — Tab Tìm kiếm

**Tiêu chí nghiệm thu:**
- [ ] Tải lên một ảnh → hiện 5 ảnh giống nhất kèm điểm số, xếp giảm dần
- [ ] Chạy đúng đường ống như lúc nạp: rembg → xoay → crop → 384×384 → trích đặc trưng
- [ ] **Tìm theo đa giả thuyết hướng (TTA)** — sinh 4 biến thể lật ngang × lật dọc, cộng thêm α±90° khi độ thon < 1,5; chọn biến thể có khoảng cách nhỏ nhất. Hệ **tự động hoàn toàn**, không cần người can thiệp
- [ ] Hai tầng cho khỏi chậm: chấm 4–8 giả thuyết bằng 80 chiều rẻ (color moments + tỉ số hình học + contour), rồi trích đủ 1.013 chiều **chỉ cho giả thuyết thắng**
- [ ] Nút sửa hướng tay (a/w/d/s) là **tùy chọn ghi đè**, mặc định tắt — dùng khi demo và khi gỡ lỗi, không phải cổng bắt buộc
- [ ] Ảnh không phải cá, hoặc loài ngoài CSDL → báo **"không tìm thấy loài tương ứng"** theo ngưỡng
- [ ] Ngưỡng τ phải hiệu chuẩn **với cùng thủ tục TTA** áp cho cả ảnh ngoài CSDL — vì chọn-theo-khoảng-cách-nhỏ-nhất làm mọi ảnh trông gần CSDL hơn một chút

**Kiểm chứng:** thử 5 ảnh — trong CSDL, ngoài CSDL cùng họ, ngoài CSDL khác họ, ảnh không phải cá, ảnh hỏng. Thêm: cùng một ảnh lật ngang/lật dọc/xoay 90° phải cho **cùng top-5**

**Phụ thuộc:** T13 · **Quy mô:** M · **Người:** NT

---

## T15 — Tab Giải thích (mục 4b của đề)

**Tiêu chí nghiệm thu:**
- [ ] Hiện chuỗi: ảnh gốc → mask → ảnh đã chuẩn hóa
- [ ] Hiện histogram HSV theo dải, ảnh LBP, bảng Hu moments, đường cong contour signature
- [ ] **Bảng phân rã khoảng cách** cho từng ảnh trong top-5: `d_màu`, `d_kết_cấu`, `d_hình_dáng`, `d_deep`, trọng số, tổng
- [ ] Grad-CAM cho Bộ B

**Kiểm chứng:** một người ngoài nhóm nhìn tab này phải hiểu được vì sao ảnh số 1 được xếp trên ảnh số 2

**Phụ thuộc:** T14 · **Quy mô:** M · **Người:** TV-A (màu, kết cấu) + TV-B (hình dáng, Grad-CAM)

---

## ✅ Chốt chặn 4 — Demo chạy được trên máy khác

- [ ] Clone repo về máy sạch, `docker compose up` + `streamlit run` là chạy
- [ ] Thử trên máy chỉ có CPU
- [ ] Backend dự phòng vẫn chạy khi tắt Docker

---

# Giai đoạn 5 — Đánh giá

## T16 — Sáu chỉ số chính, 5-fold, macro-average

**Tiêu chí nghiệm thu:**
- [ ] Precision@1, @5, @10, Recall@10, mAP — **macro-average theo loài**
- [ ] Mỗi ảnh được làm truy vấn **đúng một lần** qua 5 fold
- [ ] Báo cáo cả trung bình và độ lệch chuẩn giữa các fold
- [ ] **Ablation chuẩn hóa hướng — ba con số P@5:** (a) máy đoán một giả thuyết, (b) TTA đa giả thuyết, (c) hướng người duyệt đã ghi (mức trần). Khoảng cách (c)−(b) là phần thiệt còn lại do đoán hướng
- [ ] **Độ chính xác của `doan_huong`** tách theo loài, đối chiếu với cột `tu_the`/`bien_doi` trong `data_meta/review/*.r1.csv` — nhãn hướng đúng đã có sẵn, không tốn thêm phút duyệt nào. Dự đoán: cá thoi gần 100%, cá dĩa và cá hồng két thấp vì độ thon chỉ 1,29

**Kiểm chứng:** tổng số truy vấn = 1.085; không ảnh nào vừa ở gallery vừa ở query trong cùng một fold. TTA chọn biến thể **chỉ theo khoảng cách**, không bao giờ xem nhãn loài

**Phụ thuộc:** T10 · **Quy mô:** M · **Người:** TV-A

---

## T17 — Giá trị thông tin của đặc trưng (mục 2 của đề)

**Tiêu chí nghiệm thu:**
- [ ] Bảng ablation 6 cấu hình
- [ ] **Fisher score** từng khối, trình bày **ba cột**: phương sai nội lớp, phương sai liên lớp, tỉ số
- [ ] Fisher tính trên **mẫu cân bằng** (rút ngẫu nhiên 19 ảnh mỗi loài) để không lệch về lớp lớn
- [ ] Fisher theo **từng cặp loài cùng họ** — chỉ ra đặc trưng nào cứu được cặp khó

**Kiểm chứng:** kết luận phải nêu được ít nhất một cặp loài mà khối A thất bại còn khối B cứu được

**Phụ thuộc:** T16 · **Quy mô:** M · **Người:** TV-A

---

## T18 — Phân loại top-1, ma trận nhầm lẫn, ảnh ngoài CSDL

**Tiêu chí nghiệm thu:**
- [ ] Độ chính xác phân loại lấy nhãn ảnh top-1 làm nhãn dự đoán
- [ ] Ma trận nhầm lẫn 20×20 **chuẩn hóa theo hàng**
- [ ] Precision@5 **theo họ** (nới lỏng) bên cạnh theo loài (nghiêm ngặt)
- [ ] 20 ảnh loài ngoài CSDL: đo tỉ lệ hệ báo đúng "không tìm thấy"

**Kiểm chứng:** ma trận nhầm lẫn phải cho thấy các cặp cùng họ bị nhầm nhiều hơn cặp khác họ

**Phụ thuộc:** T16 · **Quy mô:** M · **Người:** TV-B

---

## ✅ Chốt chặn 5 — Đủ số liệu cho báo cáo

- [ ] Mọi bảng số đã xuất ra file, tái lập được bằng một lệnh
- [ ] Ba quy tắc trung thực được tuân thủ (xem mục Rủi ro)

---

# Giai đoạn 6 — Ba báo cáo

## T19 — Báo cáo tiến độ 1 (hạn 22/10, còn 9 ngày)

| Mục của đề | Nội dung | Người |
|---|---|---|
| Mục 1 | Mô tả bộ dữ liệu: 20 loài, 11 họ, 1.085 ảnh, quy trình chuẩn hóa, tỉ lệ đạt chuẩn theo nguồn | NT |
| Mục 1 | **Mô tả điểm giống và khác nhau giữa các loài** — dựa trên bảng Bộ C | TV-A + TV-B |
| Mục 2 | Thiết kế bộ đặc trưng và độ đo tương đồng | TV-A + TV-B |

**Phụ thuộc:** T9 · **Quy mô:** M

---

## T20 — Báo cáo tiến độ 2 (hạn 26/11)

Mục 3, 4a, 4b: thuật toán trích rút, lược đồ CSDL, sơ đồ khối, kết quả trung gian.

**Phụ thuộc:** T15 · **Quy mô:** M

---

## T21 — Báo cáo tổng và demo (hạn 15/12)

**Phụ thuộc:** T18 · **Quy mô:** L

---

# Sản phẩm cuối phải có

Đối chiếu trực tiếp với 5 phần của đề bài:

| Phần của đề | Sản phẩm | Nơi có |
|---|---|---|
| **1.** ≥1000 ảnh cùng kích thước, 1 con, chụp ngang, hướng nhất quán | **1.085 ảnh PNG 384×384**, cá 348px, đầu trái lưng trên ✅ | `work/chuan/` |
| **1.** Mô tả giống/khác giữa các con cá | Bảng Bộ C 20 loài × 10 thuộc tính + ma trận nhầm lẫn | `data_meta/semantic_attributes.csv` |
| **2.** Bộ thuộc tính nhận diện, đặc trưng tương đồng và khác biệt | **Bộ A 501 chiều** (10 đặc trưng) · **Bộ B 512** · **Bộ C 10** · **Bộ D hợp nhất** | `fishcbir/features/` |
| **2.** Giá trị thông tin của từng đặc trưng | Bảng ablation 6 cấu hình + Fisher score 3 cột + Fisher theo cặp loài | `ketqua/gia_tri_thong_tin.csv` |
| **3.** Thuật toán trích rút + CSDL quản trị đặc trưng | Code có kiểm thử + PostgreSQL 17 + pgvector, 4 bảng, index HNSW | `fishcbir/`, `docker-compose.yml`, `sql/` |
| **4.** Tìm kiếm top-5 xếp giảm dần | Module tìm kiếm + 2 backend (pgvector, NumPy) | `fishcbir/search.py` |
| **4a.** Sơ đồ khối, chức năng từng khối, dữ liệu vào/ra | Sơ đồ **vẽ đúng theo cấu trúc code thật** | báo cáo |
| **Kiến trúc & mô hình dữ liệu** *(thầy sẽ hỏi khi vấn đáp)* | Centralized · Homogeneity · Object-Relational + Vector, kèm lý do bác 5 mô hình còn lại, neo theo số trang slide | `docs/kien-truc-va-mo-hinh-du-lieu.md` ✅ |
| **4b.** Minh họa kết quả trung gian | Tab "Giải thích" trong demo + bảng phân rã khoảng cách | `app/` |
| **4c.** Đánh giá kết quả | 5-fold, macro-average, 6 chỉ số, so sánh quét tuần tự vs HNSW | `ketqua/` |
| **5.** Demo hệ thống | Streamlit chạy được trên máy sạch, có phương án dự phòng | `app/` |

Ngoài ra nộp kèm: **báo cáo Word theo mẫu trường** × 3 đợt, và repo có `requirements.txt` + hướng dẫn chạy lại từ đầu bằng một lệnh.

---

# Rủi ro

| Rủi ro | Mức | Cách giảm |
|---|---|---|
| **Lớp lệch 8,5 lần** (19 ↔ 162 ảnh) | Cao | 5-fold + macro-average + Fisher trên mẫu cân bằng. Nêu rõ trong phần hạn chế, kèm lý do: ảnh cá nước ngọt Việt Nam đúng chuẩn rất hiếm trên nguồn mở |
| **Độ nét lệch giữa các nguồn** (Archive gấp 3 lần iNaturalist) | Trung bình | Đã ghi `do_net` cho từng ảnh. Kiểm tương quan giữa độ nét và lỗi nhận dạng ở T17; nếu có thì nêu trong hạn chế |
| **Chất lượng mask lệch theo nguồn** (Archive 0% hỏng, iNaturalist 17%) | Trung bình | Nêu trong hạn chế; đặc trưng hình dáng của 4 loài Archive sạch hơn các loài khác |
| Docker không chạy được ngày demo | Trung bình | Backend NumPy dự phòng, đã nằm trong T13 |
| Nhãn cấp chi chứ không cấp loài (`SYM_SPP` cá dĩa) | Thấp | Ghi rõ trong phần hạn chế |
| Rò rỉ dữ liệu khi dò trọng số | **Cao** | Dò **bên trong từng fold**, chỉ trên phần gallery. Kiểm bằng cách đối chiếu số truy vấn = 1.085 |

## Ba quy tắc giữ số liệu trung thực

1. **Chỉ loại ảnh theo checklist, không bao giờ loại vì hệ thống tìm sai.** Ảnh đạt chuẩn mà bị trả sai loài là *kết quả đánh giá*, không phải *ảnh xấu*.
2. **Danh sách loài và checklist đã đóng băng.** Không sửa sau khi thấy kết quả đánh giá.
3. **Không ảnh nào vừa ở gallery vừa ở query trong cùng một fold**, và luôn loại self-match.

---

# Câu hỏi còn chờ quyết

| Câu hỏi | Khi nào cần quyết |
|---|---|
| Có bổ sung ảnh cho 7 loài dưới 30 ảnh không? (cần ~1.040 ảnh tải, ~700 ảnh duyệt, 2 giờ) | Trước T16. Khuyến nghị: **không** — 5-fold đã bù được phần lớn |
| Có làm CLIP làm hệ đối chứng thứ ba không? | Sau T8, tùy tiến độ. Đây là thứ duy nhất được phép bỏ |
| Phân công lại 20 loài cho 3 người sau khi bỏ 2 loài | Trước T9 |
