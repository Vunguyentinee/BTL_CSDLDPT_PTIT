# Intent & Chốt công nghệ — Hệ CSDL lưu trữ & tìm kiếm ảnh cá (CBIR)

> **Trạng thái:**
> - Ý định (intent) — **ĐÃ CHỐT** qua `interview-me`, người dùng xác nhận "Yes" — 2026-08-27.
> - Rà soát đối chiếu đề bài + **chốt công nghệ** (người dùng đã giao quyền quyết định cho agent) — 2026-08-29.
> - Bổ sung mục **Kiến trúc CSDL: lựa chọn & lập luận** (tập trung vs. phân tán vs. hybrid) — 2026-09-16.

## Nguồn gốc đề bài

Yêu cầu gốc: `Documents/Requirement.docx` — Bài tập lớn môn CSDL Đa phương tiện: "Xây dựng hệ CSDL lưu trữ và tìm kiếm ảnh cá."

> ⚠️ Ghi chú dọn dẹp: file `Documents/Requirement.docx` hiện đã bị dán thêm nội dung interview notes vào cuối. Nên xóa phần dán thêm để giữ file đề bài gốc sạch — bản notes chính thức là file này.

5 phần chính của đề:
1. Thu thập/sưu tầm ≥1000 ảnh cá (nhiều loài), ảnh chuẩn hóa: cùng kích thước, 1 con cá/ảnh, chụp ngang, đầu/đuôi hướng nhất quán, tỉ lệ khung hình tương đồng. **Mô tả điểm giống/khác giữa các con cá.**
2. Xây dựng một/vài bộ thuộc tính (đặc trưng) để nhận diện — bao gồm đặc trưng tìm tương đồng và đặc trưng phân biệt. Trình bày cụ thể từng loại đặc trưng + **giá trị thông tin** của đặc trưng.
3. Triển khai thuật toán/công cụ trích rút đặc trưng đã xác định ở bước 2; xây CSDL quản trị các đặc trưng.
4. Triển khai hệ thống tìm kiếm ảnh tương đồng: input = 1 ảnh cá mới (**có thể cùng loài hoặc khác loài** với ảnh trong CSDL), output = top-5 ảnh giống nhất, xếp giảm dần theo độ tương đồng.
   - a. Sơ đồ khối hệ thống, chức năng từng module, dữ liệu vào/ra, quy trình thực hiện.
   - b. **Minh họa kết quả trung gian** (giá trị đặc trưng, tính độ tương đồng) trong quá trình truy vấn.
   - c. Đánh giá kết quả đạt được.
5. Demo hệ thống.

## Bản tóm tắt ý định đã xác nhận (Outcome / User / Why now / Success / Constraint / Out of scope)

| Mục | Nội dung |
|---|---|
| **Outcome** | Xây hệ CSDL đa phương tiện lưu trữ & tìm kiếm ảnh cá (CBIR): thu thập tự sưu tầm ~1000–1200 ảnh (15–20 loài, đã chuẩn hóa 1 con cá/ảnh, hướng nhất quán), trích 2 bộ đặc trưng song song (cổ điển + deep pretrained chỉ inference), lưu trong CSDL, web demo upload ảnh → trả top-5 ảnh tương đồng nhất kèm điểm số **và bảng giải thích cách tính**. |
| **User** | Nhóm 3 người làm bài tập lớn môn CSDL Đa phương tiện; có buổi vấn đáp trực tiếp với giảng viên → hệ thống phải dễ giải thích, không phải hộp đen. |
| **Why now** | Deadline bài tập lớn với 3 mốc báo cáo cố định: 22/10/2026 (tiến độ 1), 26/11/2026 (tiến độ 2), 15/12/2026 (báo cáo tổng + demo cuối). |
| **Success** | Đạt đủ 5 phần của đề; có bộ chỉ số đánh giá định lượng; giải thích được cơ chế khi vấn đáp; đúng hạn 3 mốc báo cáo (kèm báo cáo Word chuẩn theo mẫu trường + demo trực tiếp). |
| **Constraint** | Phần cứng nhóm không đồng nhất (có máy chỉ CPU) → pipeline chính không phụ thuộc GPU; dữ liệu bắt buộc tự thu thập, không dùng nguyên 1 dataset có sẵn; công nghệ tự do lựa chọn (agent đề xuất & đã chốt bên dưới). |
| **Out of scope** | Không xử lý video/real-time; không hỗ trợ ảnh có nhiều cá trong 1 ảnh; không có tài khoản/đăng nhập cho web demo; không tự train model deep learning từ đầu — fine-tune nhẹ (transfer learning) chỉ là mục tiêu mở rộng nếu dư thời gian/GPU, không bắt buộc. |

## Chi tiết đã thống nhất qua các vòng phỏng vấn

| Chủ đề | Quyết định |
|---|---|
| Nhóm | 3 người |
| Deadline tổng | ~15/12/2026 (báo cáo tổng + demo cuối) |
| Mốc báo cáo tiến độ | 22/10/2026 (đợt 1), 26/11/2026 (đợt 2), 15/12/2026 (đợt 3 — báo cáo tổng + demo) |
| Công nghệ | Tự do lựa chọn — người dùng giao quyền chọn cho agent → **đã chốt, xem mục "Chốt công nghệ"** |
| Nguồn dữ liệu ảnh | **Tự thu thập** (không dùng nguyên một bộ dataset có sẵn) — sưu tầm từ nhiều nguồn rồi tự chuẩn hóa |
| Số loài / số ảnh | **20 loài × ~60 ảnh = ~1200 ảnh, cân bằng lớp** (khớp yêu cầu ≥1000; cân bằng để Precision@5 theo loài so sánh được công bằng) |
| Demo | Web app upload 1 ảnh → top-5 ảnh tương đồng + điểm số + **tab "Giải thích"** (kết quả trung gian). Có vấn đáp trực tiếp → hệ thống cần dễ giải thích cơ chế bên trong |
| Phần cứng nhóm | Không đồng nhất — có máy có GPU, có máy chỉ CPU. **Kết luận sau rà soát: ở quy mô 1200 ảnh, GPU không cần thiết** (xem mục "Ngân sách tính toán") |
| Hướng đặc trưng | **2 bộ đặc trưng song song để so sánh:** cổ điển (color/texture/shape) vs. deep pretrained chỉ inference. Fine-tune nhẹ là stretch goal, không bắt buộc |
| Tài liệu nộp | Cần **cả hai**: báo cáo Word chuẩn theo mẫu trường VÀ demo kết quả trực tiếp |
| Phạm vi loại trừ | Không video/real-time; không ảnh nhiều cá/ảnh; không auth cho web demo; không train deep model from-scratch |

---

## Chốt công nghệ

Người dùng giao quyền quyết định. Các lựa chọn dưới đây là **quyết định cuối**, không còn là phương án A/B.

| Lớp | Chốt | Lý do | Dự phòng |
|---|---|---|---|
| Ngôn ngữ & thư viện nền | **Python 3.11+**; OpenCV, scikit-image, NumPy/SciPy, Pillow, PyTorch + torchvision | Chuẩn ngành cho CBIR; scikit-image có sẵn LBP (`local_binary_pattern`) và GLCM (`graycomatrix`/`graycoprops`), OpenCV có Hu moments/contour | — |
| **CSDL** | **PostgreSQL 17 + pgvector**, chạy qua **Docker Compose** (image `pgvector/pgvector:pg17`) | Môn học là *CSDL Đa phương tiện* — mục 3 của đề chấm phần "xây hệ CSDL quản trị đặc trưng"; SQLite+NumPy chạy được nhưng yếu về mặt môn học. pgvector cho toán tử `<->` (L2), `<=>` (cosine) và index **HNSW/IVFFlat** → làm được hẳn một mục so sánh *quét tuần tự vs. chỉ mục ANN* trong báo cáo. Docker giải quyết vấn đề 3 máy Windows không đồng nhất | Backend `numpy` brute-force sau cùng một interface `search(query_vec, k)` — bảo hiểm cho ngày demo nếu Docker/Postgres không lên |
| **FAISS** | **KHÔNG dùng** | 1200 vector: brute-force NumPy mất vài mili-giây, ANN vô nghĩa. Thêm FAISS chỉ tốn dependency + rắc rối cài trên Windows. Khái niệm ANN đã được thể hiện bằng HNSW *bên trong CSDL* — đúng trọng tâm môn hơn | — |
| **Web demo** | **Streamlit** | Lưới ảnh, histogram matplotlib, so sánh cạnh nhau — đúng thứ mục 4b cần, ~200 dòng. FastAPI+HTML tốn gấp 3–5 lần công mà không thêm điểm (không auth, không client khác) | Thêm lớp FastAPI mỏng (~20 dòng) nếu giảng viên hỏi "có API không" |
| Kiến trúc code | Toàn bộ logic trong package **`fishcbir/`** (`ingest / preprocess / features / db / search / eval`); Streamlit chỉ là lớp vỏ mỏng | Để **sơ đồ khối ở mục 4a là sơ đồ thật của code**, không phải vẽ cho đẹp; và UI có thể thay mà không đụng logic | — |
| Tách nền / crop | **`rembg` (U²-Net)** — thành phần **cốt lõi, không phải tùy chọn** | Hu moments/contour chỉ có nghĩa khi có mask; mask cũng khử được bẫy "phân biệt theo nền" của dataset chụp studio. Bbox của mask dùng luôn để crop | — |
| **YOLO** | **KHÔNG dùng** ở pipeline chính | Bbox từ mask của rembg đã đủ; bỏ được một dependency nặng | Chỉ thêm nếu rembg thất bại trên >10% ảnh |
| Model deep | **ResNet18** pretrained ImageNet, chỉ inference, global-average-pool → 512-d, **L2-normalize**, cosine similarity; PCA xuống 128–256 chiều khi lưu DB | Nhẹ, chạy CPU tốt, cực kỳ phổ biến → dễ bảo vệ khi vấn đáp. Cặp "cổ điển vs. CNN pretrained" sạch và dễ giải thích | MobileNetV2 nếu cần nhẹ hơn nữa |
| Model deep bổ sung (tùy chọn) | **CLIP ViT-B/32** (512-d, chạy CPU được) làm hệ thứ ba để so sánh | Retrieval mạnh hơn rõ rệt trên bài fine-grained. **Không thay ResNet18 làm baseline chính** — chỉ thêm nếu dư thời gian | Bỏ nếu chậm tiến độ |
| Lưu trữ ảnh | Ảnh đã xử lý (256×256) nằm trên **hệ thống file**, tên file = SHA-256; DB giữ đường dẫn + hash + **thumbnail 128px dạng `BYTEA`**. Ảnh thô để ngoài git (Drive/OneDrive); chỉ commit ảnh đã xử lý + `sources.csv` | Mô hình "metadata trong DB, nội dung ngoài DB" — xem mục **Kiến trúc CSDL**. Ảnh đã xử lý cỡ vài chục đến ~150MB; tránh phình repo | Lưu toàn bộ ảnh dạng `BYTEA` trong DB (khả thi ở quy mô này) nếu muốn một file dump tự chứa |
| Định dạng ảnh | Thô: JPEG. Đã xử lý: **PNG 256×256** (giữ được alpha của mask) | Đề cho tự chọn định dạng; PNG không nén mất mát → không nhiễu đặc trưng texture | — |
| Tái lập | `requirements.txt` + seed cố định + script `pipeline.py` chạy lại toàn bộ bằng 1 lệnh | Giảng viên chấm cao phần tái lập được | — |

### Ngân sách tính toán (đã kiểm chứng lại ràng buộc CPU-only)

| Khâu | Chi phí ước tính (CPU) |
|---|---|
| `rembg` tách nền 1200 ảnh | ~0.5–1 s/ảnh → **~15–20 phút, chạy 1 lần rồi cache** |
| Trích đặc trưng cổ điển 1200 ảnh | vài phút |
| ResNet18 inference 1200 ảnh | ~30 ms/ảnh → **~40 giây toàn bộ dataset** |
| Truy vấn 1 ảnh (brute-force 1200 vector) | phép tính khoảng cách < 1 ms; cả truy vấn (gồm trích đặc trưng ảnh đầu vào) cỡ vài trăm ms, chủ yếu do `rembg` |

→ **Ràng buộc "không phụ thuộc GPU" không phải vấn đề ở quy mô này.** GPU chỉ có ý nghĩa nếu làm stretch goal fine-tune.

---

## Kiến trúc CSDL: lựa chọn & lập luận

### Kết luận

> Hệ thống dùng **CSDL tập trung** (một DBMS, một site), triển khai theo **kiến trúc client–server 3 tầng**, với **lưu trữ phân tách theo loại dữ liệu**: metadata + vector đặc trưng nằm trong PostgreSQL + pgvector; file ảnh nằm trên hệ thống file, CSDL chỉ giữ đường dẫn, mã băm và thumbnail.

Không phân tán, không hybrid (theo nghĩa kiến trúc phân tán lai). Tính "lai" duy nhất của hệ là **lai về lưu trữ** (DB + filesystem), không phải lai về phân tán.

### Đối chiếu ba phương án

| Tiêu chí | Tập trung ✅ | Phân tán | Hybrid |
|---|---|---|---|
| Quy mô dữ liệu (~1200 ảnh, vector ≈ 4–5 MB, ảnh < 1 GB) | Nằm gọn trong RAM một laptop | Không có gì để chia | Không có gì để chia |
| Tải truy vấn (1 người dùng, demo) | Dư sức | Thừa hạ tầng | Thừa hạ tầng |
| Truy vấn k-NN toàn cục | Một lần quét / một index | Scatter–gather tới **mọi** node → thêm độ trễ mạng, không giảm tổng khối lượng tính | Như phân tán ở phần bị phân mảnh |
| Tính nhất quán cho phần đánh giá (P@5, mAP) | ACID, một snapshot duy nhất | Nguy cơ nhất quán cuối → kết quả đo không ổn định | Phức tạp hóa việc đảm bảo snapshot |
| Vận hành trên 3 máy Windows, demo 1 laptop | 1 container Docker | Nhiều node phải cùng sống → nhiều điểm chết | Như phân tán |
| Yêu cầu của đề | Mục 3 chỉ yêu cầu "hệ CSDL quản trị đặc trưng" — đáp ứng đủ | Không được yêu cầu | Không được yêu cầu |

### Lập luận chi tiết

**① Quy mô quá nhỏ để phân tán có nghĩa.** Vector đặc trưng (cổ điển ~450 chiều + deep 512 chiều) cho 1200 ảnh chỉ ≈ 4–5 MB. Phân tán tồn tại để giải quyết 4 vấn đề: dữ liệu vượt dung lượng 1 máy, tải vượt năng lực 1 máy, độ trễ theo địa lý, yêu cầu sẵn sàng cao. **Bài này không có vấn đề nào trong 4 vấn đề đó.**

**② Bản chất truy vấn k-NN chống lại việc phân tán — lập luận chính.** Tìm top-5 láng giềng gần nhất là **truy vấn toàn cục**, về nguyên tắc phải so với toàn bộ không gian vector. Nếu chia dữ liệu ra N node:

```
query → fan-out tới CẢ N node → mỗi node trả top-5 cục bộ → merge → top-5 toàn cục
```

Mô hình scatter–gather này **không giảm tổng khối lượng tính toán**, chỉ chia nhỏ ra và trả thêm chi phí mạng + bước merge:

| Thao tác | Chi phí |
|---|---|
| Brute-force 1200 vector × ~960 chiều (NumPy) | < 1 ms |
| Một vòng round-trip mạng LAN | ~0.2–1 ms |
| Một vòng round-trip qua Internet | ~20–50 ms |

→ Riêng độ trễ mạng đã ngang hoặc đắt hơn toàn bộ phép tính: **phân tán ở quy mô này làm hệ chậm đi.** Ngoài ra, **chọn khóa phân mảnh cho k-NN là bài toán khó** — không có khóa tự nhiên nào bảo toàn tính lân cận trong không gian nhiều chiều; muốn shard đúng phải phân cụm (IVF) hoặc LSH, tức là thêm cả một tầng thuật toán xấp xỉ cho một vấn đề chưa tồn tại.

**③ Nhất quán cho đánh giá.** Mục 4c cần gallery cố định, một snapshot duy nhất. CSDL tập trung cho ACID; hệ phân tán kéo theo khả năng nhất quán cuối → cùng truy vấn có thể cho kết quả khác nhau giữa hai lần đo.

**④ Rủi ro vận hành.** Demo trên một laptop trong phòng vấn đáp, mạng không chắc chắn. Tập trung = một `docker compose up`.

**Nguyên tắc tổng quát (nên đưa vào báo cáo):**
> Phân tán là **cái giá phải trả** để giải quyết một vấn đề cụ thể. Khi vấn đề đó không tồn tại, chỉ còn lại cái giá — phân mảnh, nhân bản, đồng bộ, giao dịch phân tán (2PC), đánh đổi CAP, giám sát nhiều node — mà không thu được lợi ích nào.

### Kiến trúc triển khai: client–server 3 tầng

```
┌──────────────────────────────────────────────────────────────┐
│ TẦNG TRÌNH BÀY   Trình duyệt ← Streamlit UI                  │
│                  (upload ảnh, lưới top-5, tab "Giải thích")  │
└───────────────────────────────┬──────────────────────────────┘
                                │ HTTP
┌───────────────────────────────▼──────────────────────────────┐
│ TẦNG ỨNG DỤNG    package fishcbir/                           │
│   preprocess → features → search (fusion, xếp hạng) → eval   │
└──────────────┬────────────────────────────────┬──────────────┘
               │ SQL (psycopg)                  │ đọc/ghi file
┌──────────────▼───────────────────┐  ┌─────────▼──────────────┐
│ TẦNG DỮ LIỆU — MỘT SITE          │  │ Hệ thống file          │
│ PostgreSQL 17 + pgvector         │  │ data/processed/        │
│ • metadata (loài, nguồn, license)│  │   <sha256>.png         │
│ • vector đặc trưng + index HNSW  │  │ (ảnh 256×256, bất biến)│
│ • đường dẫn + SHA-256 + thumbnail│  │                        │
└──────────────────────────────────┘  └────────────────────────┘
```

> ⚠️ **Bẫy khái niệm khi vấn đáp: client–server ≠ phân tán.** Việc ứng dụng và DBMS chạy ở hai tiến trình (hay hai máy) khác nhau **không** làm CSDL trở thành phân tán. CSDL phân tán là khi **dữ liệu nằm ở nhiều site và nhiều DBMS phối hợp** để phục vụ chung một lược đồ. Ở đây chỉ có một DBMS, một bản dữ liệu → **tập trung**.

### Lưu trữ phân tách: "metadata trong DB, nội dung ngoài DB"

| Loại dữ liệu | Nơi lưu | Lý do |
|---|---|---|
| Metadata (loài, nguồn, URL, license, kích thước, ngày tải) | PostgreSQL | Cần truy vấn, join, ràng buộc toàn vẹn (khóa ngoại, NOT NULL, CHECK) |
| Vector đặc trưng (từng khối: màu, kết cấu, hình dáng, deep) | PostgreSQL + pgvector | Cần toán tử khoảng cách `<->` / `<=>` và index HNSW/IVFFlat |
| Thumbnail 128px (~10 KB/ảnh) | PostgreSQL, cột `BYTEA` | Hiển thị top-5 lấy thẳng từ **một câu SQL**, không phụ thuộc filesystem |
| Ảnh đã chuẩn hóa 256×256 | Hệ thống file, tên = SHA-256 | DBMS quan hệ xử lý BLOB lớn kém (phình WAL, dump/backup chậm, khó cache); OpenCV/PIL đọc file trực tiếp |
| Ảnh thô | Ngoài repo (Drive/OneDrive) | Chỉ dùng một lần ở bước tiền xử lý |

**Cái giá của mô hình này — và cách xử lý:** không có ACID giữa một hàng trong bảng và một file trên đĩa (có thể xóa hàng mà file còn, hoặc ngược lại). Biện pháp:
1. **Ảnh bất biến** — chỉ thêm mới, không bao giờ sửa tại chỗ; muốn thay thì thêm ảnh mới và xóa bản ghi cũ.
2. **Tên file = SHA-256 của nội dung** và lưu hash trong DB → phát hiện được file bị hỏng/bị thay.
3. **Script `verify_integrity`** đối chiếu bảng ↔ thư mục (thiếu file, file mồ côi, hash sai) — chạy trước mỗi lần đánh giá và trước demo.
4. Thứ tự ghi khi nạp ảnh: **ghi file trước → insert DB sau** trong một giao dịch; nếu insert lỗi thì file mồ côi sẽ bị `verify_integrity` phát hiện và dọn.

**Câu hỏi dự kiến: "Sao không lưu luôn ảnh vào CSDL?"** — Trả lời: ở quy mô này **hoàn toàn làm được** (`BYTEA`, ~100 MB). Đánh đổi: được một file dump tự chứa, nhất quán ACID tuyệt đối; mất tốc độ backup/dump, và pipeline xử lý ảnh phải đọc qua DB. Nhóm chọn phương án trung gian: **thumbnail trong DB, ảnh đầy đủ ngoài DB**.

### Lược đồ logic (phác thảo — chi tiết chốt ở bước spec)

| Bảng | Cột chính | Ghi chú |
|---|---|---|
| `species` | `id`, `scientific_name`, `common_name_vi`, `family` | 20 loài |
| `images` | `id`, `species_id` → `species`, `sha256` (UNIQUE), `file_path`, `thumbnail BYTEA`, `source`, `source_url`, `license`, `split` (`gallery`/`query`), `created_at` | `split` cố định theo seed để chống rò rỉ khi đánh giá |
| `features` | `image_id` → `images`, `color vector(n)`, `texture vector(n)`, `shape vector(n)`, `deep vector(512)` | Một cột vector cho mỗi khối → làm được ablation và bảng phân rã khoảng cách ở mục 4b |
| `feature_stats` | `block`, `mean[]`, `std[]`, `fisher_score` | Tham số chuẩn hóa z-score tính trên tập gallery + giá trị thông tin của từng khối (mục 2) |

### Khi nào mới cần phân tán — ngưỡng quy mô

| Quy mô | Kiến trúc phù hợp |
|---|---|
| **~10³ vector** (bài này) | Tập trung; quét tuần tự đã đủ nhanh |
| ~10⁵–10⁶ vector | Vẫn tập trung một node, nhưng **bắt buộc** dùng index HNSW/IVFFlat |
| ~10⁷ vector trở lên, hoặc tải truy vấn cao | Shard theo cụm (IVF/LSH) + replica đọc, hoặc chuyển sang vector DB phân tán chuyên dụng (Milvus, Qdrant, Weaviate) |

### Kiểm chứng bằng thực nghiệm

Vì đã chốt pgvector, nhóm **đo được** cả hai chế độ trên cùng một hệ — quét tuần tự vs. index HNSW — trong chỉ số đánh giá #6.

**Giả thuyết cần kiểm chứng (không khẳng định trước):** ở ~1200 vector, index HNSW không mang lại lợi ích đáng kể so với quét tuần tự, và có thể làm giảm recall do là tìm kiếm xấp xỉ. Nếu kết quả đo xác nhận giả thuyết → đó là **bằng chứng thực nghiệm** cho quyết định chọn kiến trúc tập trung, thay vì lập luận suông. Nên đo cả **recall của HNSW so với kết quả chính xác** của quét tuần tự, không chỉ đo thời gian.

---

## Rà soát đối chiếu đề bài — các lỗ hổng đã bổ sung

Bản intent ban đầu bám đúng 5 phần của đề, nhưng thiếu mấy thứ mà đề **chấm điểm trực tiếp**. Đã bổ sung thành yêu cầu bắt buộc:

### ① Mục 2 — "giá trị thông tin của các đặc trưng" phải đo được
Đề yêu cầu rõ trình bày *giá trị thông tin* của từng loại đặc trưng. Precision@5 + thời gian truy vấn không trả lời được "màu đóng góp bao nhiêu, kết cấu bao nhiêu". Bổ sung:
- **Ablation study** bắt buộc: `color-only` / `texture-only` / `shape-only` / `concat cổ điển` / `deep` / `fusion (cổ điển + deep)` → 6 dòng kết quả. Đây chính là câu trả lời cho mục 2.
- **Fisher score** (hoặc tỉ số khoảng cách nội lớp / liên lớp) cho từng khối đặc trưng — một con số cho biết đặc trưng nào phân biệt loài tốt nhất.

### ② Mục 4b — "minh họa kết quả trung gian" phải nằm trong demo
Demo bắt buộc có **tab "Giải thích"** hiển thị theo đúng thứ tự pipeline:
1. Ảnh gốc → ảnh sau tách nền (mask) → ảnh đã xoay/pad/resize
2. Histogram HSV (theo từng dải thân cá), ảnh LBP, bảng 7 Hu moments + các tỉ số hình học
3. **Bảng phân rã khoảng cách theo từng khối** cho mỗi ứng viên top-5: `d_color`, `d_texture`, `d_shape`, `d_deep`, trọng số, và tổng

→ Vừa xong mục 4b, vừa xử lý đúng ràng buộc "không phải hộp đen" khi vấn đáp.

### ③ Mục 4 — truy vấn ảnh **khác loài** với CSDL
Đề nói rõ ảnh đầu vào có thể *"thuộc cùng loài hoặc khác loài với các ảnh đã có"*. Precision@5 theo loài không định nghĩa được khi loài truy vấn không có trong CSDL. Bổ sung:
- Tập query riêng ~20 ảnh **loài ngoài CSDL**, đánh giá định tính (top-5 trả về có "hợp lý về hình thái" không).
- **Ngưỡng similarity** để hệ thống báo được "không tìm thấy loài tương ứng trong CSDL" thay vì cứ trả 5 ảnh bất kỳ.

### ④ Mục 1 — phần viết "mô tả điểm giống/khác nhau giữa các con cá"
Đây là một deliverable viết trong báo cáo, trước đây chưa có ai phụ trách. Nay là mục bắt buộc, và **dùng lại ma trận nhầm lẫn giữa các loài** (xem mục Đánh giá) làm dẫn chứng định lượng cho phần mô tả này.

---

## Quy tắc kỹ thuật bắt buộc

Sáu điểm dưới đây trước đây không được nêu, và mỗi điểm đều dễ trở thành lỗi thật:

1. **Độ đo tương đồng phải chọn theo loại đặc trưng** — đây là trái tim của mục 4, không được dùng Euclidean cho tất cả:
   - Histogram (màu, LBP) → **Chi-square / Bhattacharyya / histogram intersection**
   - Vector deep, color moments → **cosine**
   - Hợp nhất: tổng có trọng số các khoảng cách **đã chuẩn hóa**; thử thêm rank fusion (Borda) và báo cáo cái nào tốt hơn.

2. **Chuẩn hóa từng khối đặc trưng trước khi ghép.** Concat thẳng histogram 256 bin với 7 Hu moments = xóa sổ Hu moments. Phải z-score (hoặc min-max) từng khối rồi mới ghép và gán trọng số.

3. **Resize phải letterbox, không được kéo giãn.** Đề yêu cầu "tỉ lệ khung hình tương đồng"; resize thẳng về 224×224 làm méo hình → phá hỏng toàn bộ đặc trưng hình dáng. Thứ tự đúng:
   `rembg → mask → xoay theo trục chính (PCA trên mask) cho nằm ngang → crop theo bbox → pad thành vuông → resize 256×256`

4. **Bước lật ảnh cho đầu/đuôi cùng hướng:** heuristic (nửa phía đuôi có diện tích mask nhỏ hơn và solidity thấp hơn) **+ một lượt kiểm tra thủ công**. 1200 ảnh chia 3 người, nhìn mắt thường mất ~1–2 giờ và đảm bảo 100% đúng yêu cầu đề.

5. **Chống rò rỉ dữ liệu khi đánh giá.** Truy vấn bằng chính ảnh nằm trong gallery → top-1 luôn là chính nó → Precision@5 ảo. Bắt buộc:
   - Chia **gallery / query tách rời** (80/20), **seed cố định**, ghi rõ cách chia trong báo cáo
   - Loại self-match khỏi kết quả

6. **Khử bẫy nền (background bias).** Dataset chụp studio (vd. "A Large Scale Fish Dataset") có cùng một nền/khay → hệ thống sẽ phân biệt theo *nền* chứ không theo *cá*, làm hỏng luôn phần phân tích "giá trị thông tin". Bắt buộc trích đặc trưng **trên vùng mask (cá) mà thôi**, không trên ảnh đầy đủ.

---

## Bộ đặc trưng chi tiết

### Bộ 1 — Cổ điển (nền tảng, chạy CPU tốt, dễ giải thích khi vấn đáp)

| Nhóm | Đặc trưng | Ghi chú |
|---|---|---|
| **Màu** | Histogram HSV/Lab **theo vùng**: chia thân cá thành 3–4 dải dọc theo trục đầu→đuôi, tính histogram từng dải | Bắt được "sọc ở đuôi", "vây lưng sẫm màu" — phân biệt tốt hơn hẳn histogram toàn cục và cực dễ giải thích |
| **Màu** | **Color moments** (mean/std/skew mỗi kênh = 9 chiều) | Gọn, rất dễ trình bày trong bảng "giá trị đặc trưng" của mục 4b |
| **Kết cấu** | **LBP** uniform (P=8, R=1) histogram | `skimage.feature.local_binary_pattern` |
| **Kết cấu** | **GLCM**: contrast, correlation, energy, homogeneity ở 4 góc | `skimage.feature.graycomatrix` / `graycoprops` |
| **Hình dáng** | **Hu moments** (7, lấy log) | Trên mask nhị phân |
| **Hình dáng** | **Fourier descriptors** của đường bao | Bất biến xoay/tỉ lệ, phân biệt thân cá tốt hơn nhiều so với chỉ Hu moments |
| **Hình dáng** | Tỉ số hình học: aspect ratio, extent, solidity, eccentricity, circularity | Rẻ, rất dễ giải thích |

### Bộ 2 — Deep (bổ sung, chỉ inference)

ResNet18 pretrained ImageNet → global average pool 512-d → **L2-normalize** → cosine similarity. PCA xuống 128–256 chiều khi lưu DB. Tùy chọn: thêm CLIP ViT-B/32 làm hệ thứ ba.

### Bộ 3 — Fusion

Kết hợp có trọng số bộ 1 + bộ 2. Dự kiến cho kết quả tốt nhất → là kết luận của báo cáo.

---

## Nguồn dữ liệu (đã rà soát lại)

| Nguồn | Đánh giá | Quyết định |
|---|---|---|
| **FishBase** (fishbase.se) | Ảnh mẫu vật chuẩn hóa, **gần như toàn bộ là ảnh chụp nghiêng ngang** — hợp yêu cầu đề nhất | **Nguồn chính** (kiểm tra license từng ảnh) |
| **QUT Fish Dataset** | Có subset "controlled": chụp nghiêng, nền trắng | **Nguồn chính** |
| **iNaturalist API / GBIF** | License CC tốt, nhưng **tỉ lệ loại bỏ rất cao** — nhiều ảnh cá cầm trên tay, chụp xiên dưới nước, nhiều con/ảnh. Cần duyệt ~3000–5000 ảnh mới lấy đủ 1000 ảnh đạt chuẩn | **Dùng** — phải tính công duyệt thủ công vào lịch |
| **"A Large Scale Fish Dataset"** (Kaggle) | Dùng được nhưng **có bẫy nền studio** (xem Quy tắc kỹ thuật #6) | **Dùng có giới hạn**, bắt buộc tách nền trước khi trích đặc trưng |
| **Fish4Knowledge** | Ảnh dưới nước ~30–100px, nhiễu — trái hẳn yêu cầu "cùng kích thước, chụp ngang, 1 con giữa ảnh" | **BỎ** |
| **Croatian Fish Dataset** | Yếu tương tự (dưới nước, ~800 ảnh) | Chỉ dùng bù nếu thiếu loài |
| **Crawl Google/Bing** (`icrawler`) | Được về mặt học thuật nhưng license mù mờ | Dùng cuối cùng cho loài còn thiếu, **phải ghi nguồn** |

**Bắt buộc: file `sources.csv`** — `image_path, source, source_url, species, license, ngày_tải`. Vừa chứng minh được "tự sưu tầm từ nhiều nguồn, không dùng nguyên một dataset" đúng ràng buộc của đề, vừa là phụ lục đẹp trong báo cáo.

---

## Kế hoạch đánh giá (mục 4c)

| # | Chỉ số | Mục đích |
|---|---|---|
| 1 | **Precision@1, Precision@5, Precision@10, Recall@10** theo từng loài và trung bình | Chỉ số CBIR chuẩn; P@5 khớp trực tiếp yêu cầu top-5 của đề |
| 2 | **mAP** (mean Average Precision) | Chỉ số tổng hợp, đánh giá cả thứ hạng |
| 3 | **Ablation 6 cấu hình** (color/texture/shape/concat/deep/fusion) | → trả lời mục 2 "giá trị thông tin của đặc trưng" |
| 4 | **Fisher score** hoặc tỉ số khoảng cách nội lớp/liên lớp theo từng khối | → củng cố mục 2 bằng con số |
| 5 | **Ma trận nhầm lẫn giữa các loài** | Loài nào hay bị nhầm với loài nào → dùng lại cho mục 1 "mô tả điểm giống/khác nhau" |
| 6 | **Thời gian truy vấn trung bình + recall**: quét tuần tự vs. index HNSW (pgvector), đo trên máy CPU-only và máy có GPU | Đúng trọng tâm môn CSDL; kiểm chứng thực nghiệm cho lựa chọn kiến trúc tập trung (xem mục Kiến trúc CSDL) |
| 7 | **Đánh giá định tính** trên ~20 ảnh loài ngoài CSDL | → trả lời phần "khác loài" của mục 4 |

**Giao thức:** chia gallery/query 80/20 với seed cố định, loại self-match, mọi con số báo cáo đều tính trên tập query.

---

## Ánh xạ deliverable theo 3 mốc

| Mốc | Phần của đề | Deliverable |
|---|---|---|
| **22/10/2026** (đợt 1) | Phần 1 + 2 | ~1200 ảnh đã thu thập & chuẩn hóa xong (20 loài × 60), `sources.csv`, pipeline tiền xử lý chạy được; văn bản mô tả điểm giống/khác giữa các loài; **thiết kế** bộ đặc trưng + độ đo tương đồng |
| **26/11/2026** (đợt 2) | Phần 3 + 4a + 4b | Code trích rút đặc trưng hoàn chỉnh; schema PostgreSQL+pgvector + dữ liệu đã nạp; tìm kiếm top-5 chạy được; sơ đồ khối hệ thống; tab "Giải thích" hiển thị kết quả trung gian |
| **15/12/2026** (đợt 3) | Phần 4c + 5 | Toàn bộ 7 chỉ số đánh giá + ablation; báo cáo Word chuẩn mẫu trường; demo trực tiếp; (tùy chọn) fine-tune stretch goal |

**Ghi chú tiến độ:** tính từ 29/08/2026 còn ~8 tuần đến mốc 1 và ~16 tuần đến mốc cuối, cho 3 người → lịch khá thoải mái. Nghĩa là các phần đánh giá mở rộng ở trên và stretch goal fine-tune đều khả thi, **không cần cắt phạm vi**.

---

## Bước tiếp theo

1. Chuyển sang skill `spec-driven-development` để viết spec chính thức từ tài liệu này (schema CSDL chi tiết phát triển từ lược đồ logic ở mục Kiến trúc CSDL, chữ ký từng module, định dạng dữ liệu vào/ra của từng khối trong sơ đồ 4a).
2. Sau đó `planning-and-task-breakdown` — phân chia vai trò 3 thành viên và lịch trình bám theo 3 mốc (22/10, 26/11, 15/12/2026).
3. Việc dọn dẹp cần làm sớm: xóa phần interview notes bị dán nhầm vào cuối `Documents/Requirement.docx`.
