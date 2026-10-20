# Kế hoạch dự án — Hệ CSDL lưu trữ & tìm kiếm ảnh cá (CBIR)

> Bản kế hoạch chính của nhóm. Lập ngày 2026-09-30, khi **chưa thu thập ảnh nào**.
> Quyết định thiết kế: `docs/intent/fish-image-retrieval.md` · Bản chi tiết cũ (tham khảo khi cần đào sâu): `docs/plan/tham-khao-chi-tiet.md`

---

# 0. Bốn thứ sẽ bị chấm

Mọi việc trong kế hoạch này tồn tại để phục vụ một trong bốn trục dưới đây. Việc nào không phục vụ trục nào thì đã bị cắt.

| # | Trục | Chứng minh bằng | Ai | Xong khi nào |
|---|---|---|---|---|
| 1 | **Bộ đặc trưng phân loại** | Bảng ablation 6 cấu hình · Fisher score từng khối · độ chính xác phân loại top-1 · ma trận nhầm lẫn | TV-A + TV-B | 7/12 |
| 2 | **Khả năng vận hành & truy vấn** | Demo chạy thật · thời gian truy vấn · quét tuần tự vs. index HNSW · `verify_integrity` sạch | NT | 25/11 |
| 3 | **Mô hình dữ liệu** | Bảng so sánh mô hình (Phụ lục C) · lược đồ CSDL · lập luận chọn quan hệ + kiểu vector | NT | 25/11 |
| 4 | **Quá trình thực hiện** | Sổ quyết định · số liệu tỉ lệ ảnh đạt chuẩn · lịch bám 3 mốc | Cả nhóm | Liên tục |

Nguồn ảnh **chỉ cần nêu tên**, không phải chứng minh. Vì vậy đã bỏ toàn bộ phần ghi URL, giấy phép và truy vết từng ảnh.

---

# 1. Phân vai

| Vai | Phụ trách chính |
|---|---|
| **NT** (nhóm trưởng) | Hạ tầng, toàn bộ script, CSDL, module tìm kiếm, tích hợp demo, điều phối |
| **TV-A** | Đặc trưng **màu** + **kết cấu** · đánh giá: ablation + Fisher score |
| **TV-B** | Đặc trưng **hình dáng** + **deep** · đánh giá: phân loại top-1 + ma trận nhầm lẫn |

**Cả ba cùng làm:** thu thập URL ảnh, duyệt ảnh, gán Bộ C, viết báo cáo.

**Chỉ NT chạy script.** Thành viên không cần cài Python trong giai đoạn dữ liệu.

---

# 2. Lịch

| Mốc nộp | Ngày | Nội dung |
|---|---|---|
| Tiến độ 1 | **22/10** | Dữ liệu đã chuẩn hóa + thiết kế bộ đặc trưng |
| Tiến độ 2 | **26/11** | Trích đặc trưng, CSDL, tìm kiếm top-5, sơ đồ khối |
| Tổng + demo | **15/12** | Đánh giá đầy đủ, báo cáo Word, demo trực tiếp |

| Giai đoạn | Ngày | Việc |
|---|---|---|
| **G1** Chuẩn bị & chốt loài | 30/9 – 6/10 | NT dựng hạ tầng + script; chốt 20 loài; đợt thử nhỏ |
| **G2** Thu URL, tải & duyệt ảnh | 7 – 19/10 | Thành viên nộp URL; NT tải/crawl; cả nhóm duyệt |
| **G3** Chuẩn hóa & đóng băng | 20 – 22/10 | Tiền xử lý, chia gallery/query, **báo cáo mốc 1** |
| **G4** Đặc trưng & CSDL | 23/10 – 16/11 | Trích Bộ A + B, dựng PostgreSQL + pgvector |
| **G5** Tìm kiếm & demo | 17 – 25/11 | Module tìm kiếm, Streamlit, **báo cáo mốc 2** |
| **G6** Đánh giá | 26/11 – 7/12 | 6 chỉ số, chia 3 người |
| **G7** Báo cáo tổng & demo | 8 – 15/12 | Báo cáo Word, tập demo |

---

# G1 — Chuẩn bị & chốt loài (30/9 – 6/10)

## NT làm

- [ ] Tạo **repo GitHub riêng tư**, thêm 2 collaborator, thêm `.gitignore` chặn `data/` và `.env`
- [ ] Tạo **thư mục Drive** dùng chung, mời 2 thành viên, để chế độ riêng tư
- [ ] **Chốt 20 loài** — xem Phụ lục B, có một quyết định cần quyết trước
- [ ] Viết script: `fetch_inaturalist.py`, `prepare_candidates.py`, `review_tool.py`
- [ ] **Đợt thử: 2 loài × 30 ảnh.** Chạy trọn pipeline, cả nhóm duyệt thử nửa buổi

## Thành viên làm

- [ ] Cài **Google Drive for Desktop** → "Thêm lối tắt vào Drive" → "Có sẵn khi ngoại tuyến"
- [ ] Dự buổi họp 30 phút, duyệt thử 30 ảnh

## Buổi họp 1/10 — 30 phút

1. Mục tiêu: 20 loài × 60 ảnh, ảnh chụp ngang, một con một ảnh
2. **Làm mẫu duyệt ảnh trực tiếp** — quan trọng hơn mọi tài liệu
3. Mỗi người duyệt thử 30 ảnh ngay tại chỗ

## Đợt thử dùng để đo hai con số

| Con số | Dùng để |
|---|---|
| **Tỉ lệ ảnh đạt chuẩn** | Biết phải tải bao nhiêu ảnh ứng viên mỗi loài |
| **Tỉ lệ hai người duyệt đồng ý** | Biết checklist đã đủ rõ chưa; cũng là số liệu cho trục 4 |

**Xong G1 khi:** chốt xong 20 loài, checklist không còn gây tranh cãi, script chạy thông từ tải đến duyệt.

---

# G2 — Thu URL, tải & duyệt ảnh (7 – 19/10)

## Bước 1 — Thành viên nộp URL

Nộp vào Google Sheet, tab `urls`, **ba cột**:

| ma_loai | url | nguoi_nop |
|---|---|---|
| `PAN_BOC` | https://... | Minh |

Không cần cột "nguồn" — script suy ra từ tên miền của URL.

### Quota theo loài — chia theo số ảnh iNaturalist đã đếm được

Không giao đều 200 URL cho cả 20 loài. Loài nào API tự lấy được thì khỏi làm tay:

| Nhóm | Số loài | Ảnh trên iNaturalist | Quota URL/loài | Ghi chú |
|---|---|---|---|---|
| **A** | 3 | dưới 100 | **200–300** | Phần việc chính. `PAN_BOC` chỉ có 4 ảnh trên iNat nên gần như phải lấy tay toàn bộ |
| **B** | 4 | 100 – 400 | **60** | Bù cho chắc chắn đủ 70 ảnh đạt |
| **C** | 13 | trên 400 | **0** *(tùy chọn 20)* | API lo. Nộp thêm nếu muốn đa dạng nguồn |

Tổng khoảng **850–1000 URL**, chia 3 người ≈ **300 URL/người**, khoảng một buổi.

### Cách lấy URL đúng

| Nguồn | Cách làm |
|---|---|
| **FishBase** | Mở trang loài → mục *Photos* → bấm ảnh cho hiện **bản cỡ lớn** → chuột phải → *Sao chép địa chỉ hình ảnh* |
| **Google / Bing** | Bấm ảnh cho hiện bản lớn → **mở ảnh gốc** → mới chuột phải sao chép. Sao chép ngay từ lưới kết quả chỉ được ảnh thu nhỏ ~150px, **dùng không được** |

**Luôn tìm bằng tên khoa học** (`Pangasius bocourti`), không tìm bằng tên tiếng Việt — tên tiếng Việt trả về lẫn nhiều loài.

**Chưa cần chọn kỹ** — vòng duyệt kỹ làm sau, cả nhóm cùng làm. Bây giờ chỉ bỏ qua ảnh rõ ràng vô dụng: hình vẽ, nhiều con, **cá đã mổ / phi lê / nấu chín**, ảnh quá nhỏ.

> ⚠️ **Riêng nhóm A cần lưu ý:** cá basa, cá chim trắng là cá thương phẩm, nên phần lớn ảnh trên Google là cá đã mổ, phi lê, hoặc bày trên đĩa. Tỉ lệ đạt chuẩn sẽ thấp — đó là lý do quota nhóm này cao gấp 3–5 lần. Thêm từ khóa `whole fish`, `live`, `specimen` khi tìm sẽ đỡ hơn.

**Cá quay đầu trái hay phải đều lấy** — script sẽ lật. Nhưng phải là **ảnh chụp ngang**: xem mẹo "chỉ thấy một mắt" ở Phụ lục A.

## Bước 2 — NT tải về, máy lọc sơ bộ

```
fetch_inaturalist.py  →  tải qua API cho 17 loài nhóm B + C
fetch_from_sheet.py   →  tải từ danh sách URL thành viên nộp
prepare_candidates.py →  lọc file hỏng, ảnh nhỏ, ảnh trùng; xoay theo EXIF; resize 1600px
                      →  đẩy lên Drive: raw/<ma_loai>/
```

**Tải theo lô, không tải hết một lần.** Duyệt xong lô đầu, loài nào chưa đủ 70 ảnh đạt thì tải thêm hoặc xin thêm URL. Cách này giảm số ảnh phải duyệt — mà duyệt là việc tốn công nhất.

Tên file: `<ma_loai>__<nguon>__<id>.jpg`. Nhãn loài chính là phần đầu tên file, **không ai phải gõ nhãn**.

## Bước 3 — Cả nhóm duyệt ảnh

Dùng công cụ duyệt bằng phím tắt, một phím một ảnh:

| Phím | Nghĩa |
|---|---|
| `A` | Nhận — đầu cá quay **trái** |
| `D` | Nhận — đầu cá quay **phải** |
| `1` | Loại — `R-anh` (ảnh không đạt chuẩn) |
| `2` | Loại — `R-nhan` (không chắc đúng loài) |
| `3` | Loại — `R-trung` (trùng ảnh đã có) |

Ghi hướng trái/phải **ngay lúc duyệt** vì lúc đó nhìn là thấy, không tốn thêm giây nào — và nhờ vậy bỏ được hẳn một lượt duyệt hướng riêng về sau.

**Chỉ tiêu:** 70 ảnh đạt mỗi loài (thu dư 10 so với 60 để đệm).
**Ước tính:** ~1000 ảnh/người, 5–10 giây/ảnh → **2–3 giờ/người**, chia nhiều buổi ngắn.

**Duyệt chéo: chỉ lấy mẫu 20%** số ảnh đã được nhận của người kế bên (NT → TV-A → TV-B → NT). Đủ để báo cáo tỉ lệ đồng thuận, tốn ~15 phút/người.

**Xong G2 khi:** mỗi loài có ≥ 70 ảnh được nhận.

---

# G3 — Chuẩn hóa & đóng băng (20 – 22/10)

## Máy làm

```
rembg → mask → xoay cho trục dài nằm ngang (giới hạn góc ±90°)
      → lật theo hướng đã ghi khi duyệt
      → crop → pad thành vuông → resize 256×256 PNG
```

Hai chi tiết không được bỏ:
- **Giới hạn góc xoay ±90°** — PCA chỉ cho biết *phương* của trục chính, không cho biết *chiều*; không giới hạn thì ảnh có thể tự quay 180° và đảo đầu cá, phá mất hướng đã ghi.
- **Pad thành vuông rồi mới resize**, không kéo giãn — kéo giãn làm méo hình và phá hỏng toàn bộ đặc trưng hình dáng.

**Kiểm tra tự động miễn phí:** mô men Hu thứ 7 đổi dấu khi ảnh bị lật gương, nên sau chuẩn hóa mọi ảnh cùng loài phải cùng dấu. Ảnh nào lệch dấu là còn sai hướng.

## Người làm

- **Xem lướt contact sheet** (lưới thumbnail ảnh + mask cạnh nhau) để bắt mask hỏng — ~30 phút cả nhóm
- Ghi lại **tỉ lệ mask lỗi** → số liệu cho trục 4

## Đóng băng (NT chạy)

- Rút **ngẫu nhiên 60 ảnh/loài**, seed cố định — rút ngẫu nhiên, không chọn tay
- Chia **gallery/query 80/20**, seed cố định
- Tính SHA-256, đóng gói `processed_v1.zip` lên Drive

> **Chỉ một người sinh ra bộ ảnh đã xử lý.** Cùng đoạn code chạy trên ba máy vẫn có thể lệch nhau rất nhỏ; nếu mỗi người tự sinh thì số liệu đánh giá của ba người sẽ không khớp mà không ai hiểu vì sao.

**Sau bước này dữ liệu bị đóng băng.**

## Gán Bộ C — 10 thuộc tính ngữ nghĩa, mỗi người 7 loài, ~1 buổi

Gán **theo loài**, dựa vào trang loài trên FishBase, không dựa vào một ảnh riêng lẻ. 20 loài × 10 thuộc tính = 200 ô.

| # | Thuộc tính | Miền giá trị | Đối chiếu tự động được với |
|---|---|---|---|
| 1 | Dáng thân | thoi · dẹt tròn · dẹt dài · hình trụ · dẹt bên | ⑦ aspect ratio, eccentricity |
| 2 | Tỉ lệ dài : cao | số thực — lấy trung bình aspect ratio máy đã đo | ⑦ |
| 3 | Màu nền thân | bạc · vàng · cam · nâu · xanh · đen | ③ cụm màu trội lớn nhất |
| 4 | Hoa văn sọc | không · vuông góc trục thân · dọc theo thân · chéo | ⑤ tỉ số contrast 0°/90° · ⑥ Gabor |
| 5 | Hoa văn chấm | không · chấm nhỏ · chấm lớn | ④ LBP R=1 |
| 6 | Tương phản lưng–bụng | thấp · trung bình · cao | ② histogram theo dải |
| 7 | Dáng đuôi | chẻ V · chẻ nông · tròn · vuông · hình liềm | ⑨ Fourier · ⑩ contour signature |
| 8 | Vây lưng | đơn · kép · có tia cứng | — |
| 9 | Kích thước tương đối | nhỏ · vừa · lớn | — |
| 10 | Môi trường sống | nước ngọt · nước lợ · nước mặn | — |

**Ba công dụng:**
1. **Mục 1 của đề** — bảng này chính là phần "mô tả điểm giống và khác nhau giữa các loài", ở dạng có cấu trúc thay vì văn xuôi.
2. **Giải thích khi hệ nhầm** — tra bảng thấy ngay hai loài bị nhầm trùng 8/10 thuộc tính.
3. **Đối chứng cho đặc trưng tự động** — 7/10 thuộc tính suy ra được từ Bộ A. So bản người gán với bản máy suy ra là bằng chứng rằng đặc trưng tự động bắt đúng thứ ta nghĩ nó bắt, chứ không phải ăn may. Đây là phần trực tiếp phục vụ **trục 1**.

**Không dùng lúc truy vấn**, vì ảnh mới đưa vào chưa biết là loài gì nên không tra được Bộ C của nó.

## Báo cáo mốc 1

| Mục | Ai |
|---|---|
| Mô tả bộ dữ liệu + tỉ lệ ảnh đạt chuẩn + tỉ lệ đồng thuận | NT |
| Mô tả điểm giống/khác giữa các loài (từ bảng Bộ C) | TV-A + TV-B |
| Thiết kế bộ đặc trưng + độ đo tương đồng | TV-A + TV-B |

---

# G4 — Đặc trưng & CSDL (23/10 – 16/11)

## Chia việc

| Người | Module | Đặc trưng | Chiều |
|---|---|---|---|
| **TV-A** | `features/color.py` | ① Color moments Lab · ② Histogram HSV 4 dải · ③ Màu trội k-means | 9 · 256 · 20 |
| **TV-A** | `features/texture.py` | ④ LBP đa tỉ lệ · ⑤ GLCM 4 hướng · ⑥ **Gabor** 4 tần số × 6 hướng | 54 · 16 · 48 |
| **TV-B** | `features/shape.py` | ⑦ Tỉ số hình học · ⑧ Hu moments · ⑨ Fourier descriptors · ⑩ Contour signature | 7 · 7 · 20 · 64 |
| **TV-B** | `features/deep.py` | ResNet18 sau GAP, L2-normalize, PCA 128–256 | 512 |
| **TV-B** | `features/deep.py` | **CLIP ViT-B/32** — hệ đối chứng thứ ba, làm sau khi ResNet18 xong | 512 |
| **NT** | `db/`, `preprocess/` | Lược đồ, nạp dữ liệu, index, chuẩn hóa từng khối | — |

**Bộ A = 501 chiều · Bộ B = 512 chiều (+512 nếu thêm CLIP) · Bộ C = 10 thuộc tính.**

## Bốn bộ thuộc tính — giữ nguyên, không cắt

| Bộ | Gồm | Chiều | Dùng lúc truy vấn | Giải thích được? |
|---|---|---|---|---|
| **A** Cổ điển | 10 đặc trưng, 3 nhóm màu/kết cấu/hình dáng | 501 | ✅ | ✅ Từng chiều có nghĩa |
| **B** Deep | ResNet18 (+ CLIP tùy chọn) | 512 | ✅ | ❌ Hộp đen — bù bằng Grad-CAM |
| **C** Ngữ nghĩa | 10 thuộc tính gán tay theo loài | 10 | ❌ | ✅ Đọc như tiếng Việt |
| **D** Hợp nhất | A ⊕ B có trọng số | — | ✅ | Một phần |

Ba bộ A/B/C phục vụ ba việc khác nhau và **không thay thế được cho nhau**: A để giải thích cơ chế, B để đạt kết quả tốt, C để mô tả loài và đối chứng với A. Đây là phần dày điểm nhất của trục 1, nên không cắt bớt đặc trưng nào.

**Thứ tự làm:** ResNet18 và toàn bộ Bộ A trước, CLIP làm sau cùng — nếu hết thời gian thì CLIP là thứ duy nhất được phép bỏ, vì nó chỉ là điểm so sánh thêm chứ không phải một nhóm đặc trưng mới.

## Sáu quy tắc kỹ thuật không được bỏ

1. **Chỉ trích đặc trưng trên vùng mask**, không trên ảnh đầy đủ — nếu không, hệ sẽ phân biệt theo *nền* chứ không theo *cá*.
2. **Chuẩn hóa z-score từng khối riêng** trước khi ghép, dùng `mean`/`std` tính trên gallery — không thì 256 chiều histogram nhấn chìm 7 chiều Hu moments.
3. **③ Màu trội phải sắp xếp cụm theo tỉ lệ giảm dần** — k-means trả cụm theo thứ tự ngẫu nhiên.
4. **⑤ GLCM giữ nguyên 4 hướng**, không lấy trung bình — ảnh đã chuẩn hóa hướng nên hướng hoa văn là thông tin phân biệt loài.
5. **⑨ Fourier phải lấy mẫu lại đường bao về số điểm cố định** (256) trước khi biến đổi.
6. **⑩ Contour signature:** với đuôi chẻ, một tia cắt biên nhiều điểm → quy ước lấy giao xa nhất, áp dụng nhất quán.

## CSDL — trục 3

**PostgreSQL 17 + pgvector** qua Docker Compose. Mỗi người chạy một bản trên máy mình; nạp từ cùng bộ ảnh đã chốt nên ba bản giống nhau. Lúc demo chỉ chạy một bản.

| Bảng | Cột chính |
|---|---|
| `species` | `id`, `code` UNIQUE, `scientific_name`, `genus`, `family_code`, `family`, `common_name_vi` |
| `images` | `id`, `species_id`, `sha256` UNIQUE, `file_path`, `source`, `split` |
| `features` | `image_id`, `color vector(285)`, `texture vector(70)`, `shape vector(98)`, `deep vector(512)` |
| `feature_stats` | `block`, `mean[]`, `std[]`, `fisher_score` |

**Một cột vector cho mỗi khối** — nhờ đó làm được ablation và bảng phân rã khoảng cách.

**Lưu trữ phân tách:** metadata và vector trong CSDL; ảnh nhị phân trên hệ thống file, tên = SHA-256. Vì không có ACID giữa hàng trong bảng và file trên đĩa nên cần `verify_integrity.py` đối chiếu hai bên — chạy trước mỗi lần đánh giá và trước demo.

---

# G5 — Tìm kiếm & demo (17 – 25/11)

## Module tìm kiếm — NT

**Độ đo chọn theo loại đặc trưng**, không dùng Euclidean cho tất cả:

| Loại | Độ đo |
|---|---|
| Histogram (②, ④) | Chi-square hoặc Bhattacharyya |
| Vector deep, color moments | Cosine |
| Tỉ số hình học, Hu moments | L2 |

**Hợp nhất:** đưa mọi khoảng cách về `[0,1]`, rồi `d_total = Σ wᵢ·dᵢ`. Trọng số dò trên **tập gallery**, tối ưu theo mAP. **Không dùng tập query để dò trọng số** — đó là rò rỉ dữ liệu.

**Hai backend sau cùng một interface `search(query_vec, k)`:** pgvector (chính) và NumPy brute-force (dự phòng cho ngày demo).

## Web demo — Streamlit

Toàn bộ logic trong package `fishcbir/`; Streamlit chỉ là lớp vỏ mỏng, để sơ đồ khối trong báo cáo là sơ đồ thật của code.

| Tab | Nội dung |
|---|---|
| **Tìm kiếm** | Upload ảnh → top-5 + điểm số |
| **Giải thích** | Ảnh gốc → mask → ảnh chuẩn hóa · histogram, ảnh LBP, contour signature · **bảng phân rã khoảng cách** theo từng khối cho mỗi ứng viên |

Tab "Giải thích" phục vụ mục 4b của đề và cả yêu cầu "không phải hộp đen" khi vấn đáp.

---

# G6 — Đánh giá (26/11 – 7/12)

| # | Chỉ số | Trục | Ai |
|---|---|---|---|
| 1 | Precision@1, Precision@5, mAP | 1 | TV-A |
| 2 | **Ablation 6 cấu hình** — color/texture/shape/concat/deep/fusion | 1 | TV-A |
| 3 | **Fisher score** từng khối, kèm phương sai nội lớp và liên lớp tách riêng | 1 | TV-A |
| 4 | **Độ chính xác phân loại top-1** + **ma trận nhầm lẫn** | 1 | TV-B |
| 5 | **Precision@5 theo họ** + đánh giá ảnh loài ngoài CSDL | 1 | TV-B |
| 6 | **Thời gian truy vấn**: quét tuần tự vs. index HNSW, đo trên máy CPU-only và máy có GPU | 2 | NT |

Chỉ số 4 là cách nói dễ hiểu nhất về trục 1: *"bộ đặc trưng này phân loại đúng 20 loài ở mức X%"*. Nó lấy nhãn của ảnh top-1 làm nhãn dự đoán nên gần như miễn phí — đã có sẵn kết quả truy vấn.

Chỉ số 3 trả lời vế "giá trị thông tin của đặc trưng" mà đề yêu cầu. Trình bày thành **ba cột**: phương sai nội lớp (tính tương đồng), phương sai liên lớp (tính khác biệt), tỉ số Fisher (kết luận).

## Ba quy tắc giữ cho số liệu trung thực

1. **Chỉ loại ảnh theo checklist, không bao giờ loại vì hệ thống tìm sai.** Ảnh đạt chuẩn mà bị trả sai là *kết quả đánh giá*, không phải *ảnh xấu*.
2. **Danh sách loài và checklist đóng băng sau G1.**
3. **Gallery và query tách rời**, seed cố định, loại self-match.

---

# G7 — Báo cáo tổng & demo (8 – 15/12)

- [ ] Báo cáo Word theo mẫu trường — NT gộp, mỗi người viết phần mình
- [ ] Chạy `verify_integrity` trước khi tập demo
- [ ] **Tập demo ít nhất 2 lần** trên đúng máy sẽ dùng
- [ ] Chuẩn bị 5–7 ảnh truy vấn mẫu: ca dễ, ca khó (cặp cùng họ), ca loài ngoài CSDL
- [ ] Kiểm tra backend NumPy dự phòng vẫn chạy

## Câu hỏi vấn đáp và chỗ tra câu trả lời

| Câu hỏi | Tra ở |
|---|---|
| Dùng mô hình dữ liệu gì? Sao không dùng vector DB? | Phụ lục C |
| CSDL tập trung hay phân tán? | `docs/intent/`, mục Kiến trúc CSDL |
| Client–server có phải phân tán không? | Không phải — cùng mục trên |
| Đặc trưng nào quan trọng nhất? | Bảng ablation + Fisher |
| Đưa vào con cá lạ thì sao? | Chỉ số 5 |
| Ảnh lấy ở đâu? | iNaturalist (research grade) + bù thêm FishBase |

---

# Phụ lục A — Checklist duyệt ảnh

**Nhận khi:** đúng 1 con cá · **chụp ngang** · thấy toàn thân kể cả vây và đuôi · đủ nét · chắc chắn đúng loài.

> **Mẹo kiểm tra chụp ngang: ảnh đúng chuẩn chỉ thấy ĐÚNG MỘT MẮT.**
> Thấy hai mắt, thấy cả bụng hoặc cả lưng, chụp từ trên xuống → loại. Lệch nhẹ dưới ~20° vẫn nhận.

**Cá quay đầu trái hay phải đều nhận** — chỉ cần ghi hướng, script sẽ lật.

| Mã | Loại vì |
|---|---|
| `R-anh` | Nhiều con · không chụp ngang · cắt mất vây/đuôi · bị che · mờ/nhỏ · ám màu nặng · mẫu ngâm formalin bạc màu · hình vẽ |
| `R-nhan` | Không chắc đúng loài |
| `R-trung` | Trùng ảnh đã có |

---

# Phụ lục B — 20 loài

Chia **12 họ**: 8 cặp cùng họ (để có các ca dễ nhầm) + 4 loài đơn (đối chứng).

Cột *Ảnh iNat* là số ảnh dùng được đã **đếm thật** qua API ngày 30/9. Cột *Quota* là số URL thành viên cần nộp, suy ra từ đó.

| Mã | Họ | Tên khoa học | Tên Việt | Vai trò | Ảnh iNat | **Quota URL** |
|---|---|---|---|---|---|---|
| `PAN_BOC` | PANG | *Pangasius bocourti* | Cá basa | cặp dễ nhầm | **4** | **300** |
| `PAM_ARG` | STRO | *Pampus argenteus* | Cá chim trắng | đối chứng | **20** | **250** |
| `TRI_PEC` | OSPH | *Trichopodus pectoralis* | Cá sặc rằn | cặp dễ nhầm | **68** | **200** |
| `OSP_GOR` | OSPH | *Osphronemus goramy* | Cá tai tượng | cặp dễ nhầm | 133 | 60 |
| `PAN_HYP` | PANG | *Pangasianodon hypophthalmus* | Cá tra | cặp dễ nhầm | 184 | 60 |
| `KAT_PEL` | SCOM | *Katsuwonus pelamis* | Cá ngừ vằn | cặp dễ nhầm | 257 | 60 |
| `SCO_COM` | SCOM | *Scomberomorus commerson* | Cá thu | cặp dễ nhầm | 366 | 60 |
| `LAT_CAL` → *xem ghi chú* | | | | | | |
| `ANA_TES` | ANAB | *Anabas testudineus* | Cá rô đồng | đối chứng | 478 | 0 |
| `PAR_HEP` | ACAN | *Paracanthurus hepatus* | Cá đuôi gai xanh | cùng họ khác xa | 487 | 0 |
| `CLA_BAT` | CLAR | *Clarias batrachus* | Cá trê | đối chứng | 611 | 0 |
| `SAL_SAL` | SALM | *Salmo salar* | Cá hồi Đại Tây Dương | cặp dễ nhầm | 918 | 0 |
| `AMP_FRE` | POMA | *Amphiprion frenatus* | Cá hề cà chua | cặp dễ nhầm | 986 | 0 |
| `ZEB_FLA` | ACAN | *Zebrasoma flavescens* | Cá đuôi gai vàng | cùng họ khác xa | 2.099 | 0 |
| `CHA_STR` | CHAN | *Channa striata* | Cá lóc | đối chứng | 2.209 | 0 |
| `AMP_OCE` | POMA | *Amphiprion ocellaris* | Cá hề | cặp dễ nhầm | 2.492 | 0 |
| `ORE_MOS` | CICH | *Oreochromis mossambicus* | Cá rô phi đen | cặp dễ nhầm | 2.883 | 0 |
| `ORE_NIL` | CICH | *Oreochromis niloticus* | Cá rô phi vằn | cặp dễ nhầm | 3.055 | 0 |
| `CAR_AUR` | CYPR | *Carassius auratus* | Cá diếc | cặp dễ nhầm | 5.445 | 0 |
| `ONC_MYK` | SALM | *Oncorhynchus mykiss* | Cá hồi vân | cặp dễ nhầm | 17.361 | 0 |
| `CYP_CAR` | CYPR | *Cyprinus carpio* | Cá chép | cặp dễ nhầm | 22.304 | 0 |

**Tổng quota: khoảng 990 URL** → chia 3 người ≈ 330 URL/người.

Ba dòng đầu là toàn bộ phần việc nặng. Lý do ba loài này ít ảnh trên iNaturalist: đó là **cá thương phẩm**, ít người chụp ngoài tự nhiên. Nhưng trên Google và FishBase thì nhiều — chỉ cần lọc bỏ ảnh cá đã mổ và phi lê.

**Ghi chú về `LAT_CAL` (cá chẽm):** đây là loài **dự phòng**, chưa nằm trong 20 loài. Nếu sau khi thu URL mà `PAN_BOC` hoặc `PAM_ARG` vẫn không đủ 70 ảnh đạt chuẩn thì thay bằng cá chẽm (437 ảnh iNat, không phải làm tay). Bốn loài dự phòng khác: `TRI_TRI` cá sặc bướm (521), `CHA_MIC` cá lóc bông (288), `ONC_KIS` cá hồi bạc (4.471), `AMP_CLA` cá hề Clark (3.846).

**Một quyết định nhỏ còn lại:** `CAR_AUR` — cá vàng và cá diếc là **cùng một loài** *Carassius auratus*, cá vàng là dạng đã thuần hóa. Phải chọn một dạng và ghi rõ đã chọn dạng nào, không lấy lẫn cả hai.

---

# Phụ lục C — Mô hình dữ liệu (trục 3)

| Mô hình | Đánh giá |
|---|---|
| Quan hệ thuần (vector lưu dạng `BYTEA`/`TEXT`) | Không có toán tử khoảng cách; phải kéo toàn bộ vector ra ngoài để tính |
| **Quan hệ + kiểu vector — PostgreSQL + pgvector** ✅ | Có toán tử `<->`, `<=>` và index HNSW/IVFFlat; metadata và vector nằm cùng một nơi, cùng một giao dịch |
| Vector DB chuyên dụng (Milvus, Qdrant) | Mạnh ở quy mô hàng triệu vector; ở 1.200 vector là thừa, và metadata vẫn phải đặt ở một CSDL quan hệ khác → phải quản hai hệ |
| File + NumPy | Chạy được, nhưng không phải "hệ CSDL quản trị đặc trưng" như mục 3 của đề yêu cầu |
| Document DB (MongoDB) | Lưu được vector nhưng tìm k-NN yếu và ràng buộc toàn vẹn lỏng |

**Tóm tắt để trả lời khi vấn đáp:** hệ dùng **mô hình quan hệ mở rộng kiểu vector**, tổ chức theo **lưu trữ phân tách** — metadata và vector đặc trưng trong CSDL, ảnh nhị phân trên hệ thống file với tên bằng SHA-256, và một script đối chiếu hai bên. Kiến trúc **tập trung**, triển khai kiểu client–server ba tầng.

---

# Còn phải quyết

| Việc | Quyết khi nào |
|---|---|
| Chọn một dạng cho `CAR_AUR` (cá vàng và cá diếc là cùng loài) | Trước khi giao quota — việc đầu tiên |
| `PAN_BOC` / `PAM_ARG` có đủ 70 ảnh đạt chuẩn không; nếu không thì thay bằng loài dự phòng | Sau lô URL đầu tiên |
| Tải bao nhiêu ảnh ứng viên mỗi loài từ API | Sau đợt thử, dựa vào tỉ lệ đạt chuẩn đo được |
| Có làm CLIP hay không | Sau G4, tùy tiến độ |
| Trọng số hợp nhất đặc trưng | G6, dò trên gallery |

---

# Điểm dừng để thảo luận tiếp

Kế hoạch này đủ chi tiết để **bắt đầu chạy G1 và G2** mà không cần quyết thêm gì. Sau khi có ảnh thật, hai việc dưới đây mới cần bàn, vì lúc đó mới có số liệu để bàn:

1. **Sau lô URL đầu** — xem tỉ lệ đạt chuẩn thật của từng nguồn, quyết có phải thay loài dự phòng nào không, và điều chỉnh quota.
2. **Sau khi đóng băng dữ liệu (G3)** — bàn chi tiết cách hiện thực từng đặc trưng trong Bộ A: số bin, tham số LBP, cách chuẩn hóa, trọng số hợp nhất. Bàn trước khi có ảnh thì chỉ là đoán.
