# Quy trình công việc — Hệ CSDL lưu trữ & tìm kiếm ảnh cá (CBIR)

> **Tài liệu điều hành của nhóm.** Ghi chi tiết từng bước từ đầu đến cuối, kèm phân công cho nhóm trưởng và hai thành viên.
> Cập nhật: 2026-09-30. Nguồn quyết định: `docs/intent/fish-image-retrieval.md`.

## Cách dùng tài liệu này

- Mỗi giai đoạn có bảng **ai làm gì**, **đầu vào**, **đầu ra** và **tiêu chí hoàn thành**.
- Ô nào ghi `[chờ chốt]` là chưa quyết định xong — không tự ý làm trước.
- Ba phụ lục ở cuối (checklist duyệt ảnh, bảng mã loài, quy ước tên file) là phần cần **in ra hoặc ghim vào nhóm chat**.

---

# 1. Phân vai

| Vai | Ký hiệu | Phụ trách |
|---|---|---|
| **Nhóm trưởng** | **NT** | Hạ tầng (Drive, Git, Docker, CSDL), toàn bộ script, module tìm kiếm + hợp nhất đặc trưng, tích hợp web demo, điều phối và kiểm tra chất lượng |
| **Thành viên A** | **TV-A** | Đặc trưng **màu** (①②③) và **kết cấu** (④⑤⑥); phần trực quan hóa màu/kết cấu trong tab "Giải thích"; ablation + Fisher score |
| **Thành viên B** | **TV-B** | Đặc trưng **hình dáng** (⑦⑧⑨⑩) và **Bộ B deep** + Grad-CAM; ma trận nhầm lẫn + nDCG@5 |

**Việc cả ba người cùng làm:** thu thập URL ảnh (mỗi người ~7 loài), duyệt ảnh 2 lượt, gán Bộ C ngữ nghĩa, viết báo cáo.

## Nguyên tắc làm việc chung

1. **Mỗi người chỉ ghi vào file và thư mục của loài mình phụ trách.** Không ai sửa phần của người khác.
2. **Không đổi tên, di chuyển hay xóa ảnh gốc.** Mọi quyết định ghi vào file CSV; ảnh nằm yên.
3. **Ảnh để trên Drive, chữ và code để trên Git.** Không bao giờ đặt file CSV trong thư mục Drive.
4. **Chỉ NT chạy script và đưa ảnh lên Drive.** Thành viên không cần cài Python trong giai đoạn thu thập.
5. **Chờ Drive báo đồng bộ xong** (dấu tích xanh) rồi mới thông báo cho nhóm.

---

# 2. Hạ tầng dùng chung

## Ba vùng lưu trữ

| Vùng | Ở đâu | Chứa gì | Ai ghi | Đồng bộ |
|---|---|---|---|---|
| ① Làm việc | Ổ local, `work/` | Ảnh crawler vừa tải, còn lẫn rác | Máy NT | ❌ |
| ② Chia sẻ | Drive, `raw/candidates/<mã_loài>/` | Ảnh đã sơ tuyển, **bất biến** | NT, ghi một lần | ✅ Drive |
| ③ Dẫn xuất | Ổ local, `processed/` | Ảnh sau tiền xử lý, sinh lại được | Script | ❌ (chỉ bản release lên Drive) |

## Cấu trúc Drive — `BTL_CSDLDPT_data/`

```
raw/candidates/<mã_loài>/*.jpg      ← ảnh ứng viên, không sửa/xóa
releases/processed_v1.zip           ← bộ ảnh đã tiền xử lý, bản chốt
releases/processed_v1.sha256        ← danh sách hash để đối chiếu
```

Thư mục để chế độ **riêng tư**, chỉ người được mời xem được. Không đặt "bất kỳ ai có đường liên kết".

## Cấu trúc repo Git

```
fishcbir/            ingest/ preprocess/ features/ db/ search/ eval/
app/                 Streamlit UI
scripts/             các script vận hành
docs/                tài liệu
data_meta/
  species.csv                      danh sách loài (khóa: ma_loai)
  checklist.md                     checklist duyệt ảnh + 11 mã lý do
  sources/<mã_loài>.csv            nguồn từng ảnh
  review/<mã_loài>.r1.csv          kết quả duyệt lượt 1
  review/<mã_loài>.r2.csv          kết quả duyệt chéo
  semantic_attributes.csv          Bộ C
  splits/gallery_query.csv         phân chia gallery/query đã chốt
.env.example
.gitignore                         chặn data/, work/, processed/, .env
```

## Google Sheet dùng chung

| Tab | Dùng làm gì | Ai ghi |
|---|---|---|
| `urls` | Thành viên nộp URL ảnh: `ma_loai`, `nguon`, `url`, `nguoi_nop` | Cả ba |
| `tien_do` | Bảng theo dõi: mỗi loài đã có bao nhiêu URL / ảnh sẵn sàng duyệt / đã duyệt | NT cập nhật |
| `tranh_chap` | Ảnh hai người duyệt không đồng ý | Cả ba |

## Cấu hình đường dẫn

Đường dẫn Drive khác nhau trên mỗi máy, nên **code không ghi cứng đường dẫn**. Mỗi người tạo file `.env` trên máy mình (đã bị `.gitignore` chặn):

```
FISHCBIR_DATA_DIR=G:\My Drive\BTL_CSDLDPT_data
```

---

# 3. Lịch tổng

| Mốc | Ngày | Nội dung nộp |
|---|---|---|
| Tiến độ 1 | **22/10/2026** | Phần 1 + 2 của đề: dữ liệu đã chuẩn hóa, mô tả giống/khác, thiết kế bộ đặc trưng |
| Tiến độ 2 | **26/11/2026** | Phần 3 + 4a + 4b: trích đặc trưng, CSDL, tìm kiếm top-5, sơ đồ khối, tab Giải thích |
| Tổng + demo | **15/12/2026** | Phần 4c + 5: đủ chỉ số đánh giá, báo cáo Word, demo trực tiếp |

## Lịch chi tiết tới mốc 1

| Ngày | Giai đoạn | Việc chính |
|---|---|---|
| 30/9 – 1/10 | **G0** | NT dựng hạ tầng, chốt danh sách loài, viết checklist, viết script |
| 1/10 | **G0** | Họp 30 phút: làm mẫu, giao mỗi người 1 loài × 30 URL |
| 2 – 4/10 | **G1** | Đợt thử: chạy trọn pipeline trên ~100 ảnh, chốt 2 ngưỡng |
| 5 – 6/10 | **G1** | **Cổng kiểm tra**: chốt 20 loài + checklist, giao đủ phần còn lại |
| 7 – 20/10 | **G2** | Thu thập đại trà, duyệt 2 lượt |
| 20 – 22/10 | **G3** | Chốt dữ liệu, viết báo cáo tiến độ 1 |

## Lịch sau mốc 1

| Ngày | Giai đoạn | Việc chính |
|---|---|---|
| 23/10 – 10/11 | **G4** | Trích đặc trưng, dựng CSDL, nạp dữ liệu |
| 11 – 20/11 | **G5** | Module tìm kiếm, web demo, tab Giải thích |
| 21 – 26/11 | **G6** | Báo cáo tiến độ 2 |
| 27/11 – 8/12 | **G7** | Đánh giá đầy đủ, tinh chỉnh trọng số |
| 9 – 15/12 | **G8** | Báo cáo tổng, tập demo |

---

# G0 — Chuẩn bị hạ tầng và chốt thiết kế

**Thời gian:** 30/9 – 1/10

## Việc của nhóm trưởng

- [ ] Chốt **danh sách 20 loài / 12 họ** — đối chiếu tên khoa học trên FishBase trước khi sinh mã loài (xem Phụ lục B)
- [ ] Sinh `data_meta/species.csv` theo quy ước mã loài
- [ ] Viết `data_meta/checklist.md` — checklist duyệt ảnh + 11 mã lý do (Phụ lục A)
- [ ] Tạo **repo GitHub riêng tư**, thêm 2 collaborator, thêm `.gitignore` và `.env.example`
- [ ] Tạo **thư mục Drive** `BTL_CSDLDPT_data`, mời 2 thành viên quyền chỉnh sửa, để chế độ riêng tư
- [ ] Tạo **Google Sheet** với 3 tab `urls` / `tien_do` / `tranh_chap`
- [ ] Viết các script: `fetch_inaturalist.py`, `fetch_from_sheet.py`, `prepare_candidates.py`, `promote.py`
- [ ] Viết **công cụ duyệt ảnh bằng phím tắt** (xem G1)
- [ ] Chạy thử `fetch_inaturalist.py` trên 2–3 loài để biết iNaturalist cho được bao nhiêu ảnh — loài nào đủ thì thành viên khỏi làm tay

## Việc của thành viên

- [ ] Cài **Google Drive for Desktop**, đăng nhập
- [ ] Vào "Được chia sẻ với tôi" → chuột phải thư mục → **"Thêm lối tắt vào Drive"** *(thiếu bước này thì thư mục không hiện ra trên máy)*
- [ ] Chuột phải thư mục → **"Có sẵn khi ngoại tuyến"**
- [ ] Clone repo về máy
- [ ] Đọc checklist duyệt ảnh

## Buổi họp 1/10 — 30 phút, NT chủ trì

1. Giải thích mục tiêu: 20 loài × 60 ảnh, ảnh chụp ngang, một con một ảnh.
2. **Làm mẫu trực tiếp** trên một loài: chia sẻ màn hình, lấy 10 URL thật từ FishBase và Google, chỉ luôn hai lỗi hay gặp nhất — sao chép URL ảnh thu nhỏ, và tìm bằng tên tiếng Việt.
3. Giao **mỗi người 1 loài × 30 URL** cho đợt thử.

> Làm mẫu 10 phút có giá trị hơn tài liệu 10 trang. Đừng bỏ bước này.

**Tiêu chí hoàn thành G0:** hạ tầng dùng được, mỗi thành viên đã nộp được ít nhất 1 URL đúng chuẩn vào Sheet.

---

# G1 — Đợt thử và cổng kiểm tra

**Thời gian:** 2 – 6/10 · **Quy mô:** ~100 ảnh, 6–8 loài

## Bước 1 — Thu thập URL

### Việc của thành viên

Nộp URL vào tab `urls`, mỗi ảnh một dòng: `ma_loai | nguon | url | nguoi_nop`

**Mục tiêu đợt thử:** 30 URL cho loài được giao. **Chưa cần chọn kỹ** — vòng duyệt kỹ làm sau. Bây giờ chỉ bỏ qua ảnh rõ ràng vô dụng: ảnh vẽ, nhiều con, cá đã phi lê hoặc nấu chín, ảnh quá nhỏ.

**Cách lấy URL đúng:**

| Nguồn | Cách làm |
|---|---|
| **FishBase** | Mở trang loài → mục *Photos* → bấm ảnh cho hiện **bản cỡ lớn** → chuột phải → *Sao chép địa chỉ hình ảnh* |
| **Google / Bing** | Bấm ảnh cho hiện bản lớn ở khung phải → **mở ảnh gốc** → mới chuột phải sao chép. Sao chép ngay từ lưới kết quả sẽ chỉ được ảnh thu nhỏ ~150px, dùng không được |
| **iNaturalist** | NT lo bằng API. Nếu cần làm tay thì nộp URL **trang quan sát**, script tự lấy ảnh + giấy phép + tên loài |

**Luôn tìm bằng tên khoa học** (`Cyprinus carpio`), không tìm bằng tên tiếng Việt — tên tiếng Việt trả về lẫn nhiều loài.

**Về hướng đầu cá:** **cá quay đầu sang trái hay sang phải đều lấy.** Script sẽ lật. Đừng bỏ ảnh chỉ vì nó quay ngược chiều.

**Nhưng phải là ảnh chụp ngang.** Cách kiểm nhanh nhất:

> **Ảnh chụp ngang đúng chuẩn thì chỉ thấy đúng MỘT mắt.**

Thấy hai mắt, thấy cả bụng hoặc cả lưng, hoặc ảnh chụp từ trên xuống → bỏ qua. Lệch nhẹ dưới ~20° vẫn nhận, vì bước xoay sẽ chỉnh lại.

**Không làm:** tải ảnh về máy, tự đổi tên file, tự upload lên Drive.

### Việc của nhóm trưởng

- [ ] Chạy `fetch_inaturalist.py` cho các loài có sẵn trên iNaturalist
- [ ] Tải Sheet về, chạy `fetch_from_sheet.py` để tải ảnh từ danh sách URL

## Bước 2 — Sơ tuyển kỹ thuật (máy làm, NT chạy)

`prepare_candidates.py` — 9 việc, chạy trên vùng ① rồi mới đưa sang vùng ②:

| # | Việc | Thư viện |
|---|---|---|
| 1 | Kiểm tra file đọc được (loại file hỏng, file HTML mang tên `.jpg`, ảnh 0 byte) | `PIL.Image.verify()` |
| 2 | Loại ảnh cạnh dài < **320px** *(chỉ là phép kiểm thô)* | `PIL` |
| 3 | **Áp dụng hướng EXIF rồi mới xóa EXIF** | `PIL.ImageOps.exif_transpose()` |
| 4 | Loại trùng tuyệt đối | `hashlib.sha256` |
| 5 | Loại trùng gần, ngưỡng Hamming ≤ **5**/64 bit | `imagehash.phash` |
| 6 | Chuyển về RGB (loại ảnh xám, CMYK, GIF động) | `PIL` |
| 7 | Resize cạnh dài ≤ **1600px** | `img.thumbnail()` |
| 8 | Lưu JPEG chất lượng **90** | `img.save()` |
| 9 | Đặt tên chuẩn + ghi `sources/<mã_loài>.csv` | `csv` |

**Việc 3 rất quan trọng:** ảnh từ điện thoại thường lưu ngang kèm cờ EXIF báo "xoay 90°". Xóa EXIF mà không xoay trước thì hàng loạt ảnh tốt sẽ bị người duyệt loại oan.

Xong thì `promote.py` copy sang Drive `raw/candidates/` và kiểm tra: số file phải khớp số dòng CSV, hash phải khớp.

## Bước 3 — Duyệt lượt 1 (cả ba người, mỗi người duyệt loài của mình)

Dùng **công cụ duyệt bằng phím tắt**: hiện từng ảnh, một phím là xong, tự ghi kết quả rồi chuyển ảnh kế.

| Phím | Nghĩa |
|---|---|
| `A` | Nhận — đầu cá quay **trái** |
| `D` | Nhận — đầu cá quay **phải** |
| `1`–`9`, `0`, `-` | Loại, kèm mã lý do R1–R11 |

Ghi ra `data_meta/review/<mã_loài>.r1.csv`:

| image_id | quyet_dinh | ma_ly_do | huong | nguoi_duyet |
|---|---|---|---|---|
| CYP_CAR__inat__12893 | nhan | — | L | Minh |
| CYP_CAR__inat__12894 | loai | R3 | — | Minh |

**Ghi cột `huong` ngay tại đây** không mất thêm một giây nào, và nhờ đó bỏ được hẳn heuristic đoán hướng cùng một lượt duyệt hướng riêng ở bước 5 — tiết kiệm 1–2 giờ và chính xác 100%.

**Thứ tự kiểm tra từng ảnh** (xếp theo thứ tự loại nhanh nhất):
1. Đúng 1 con cá, chụp ngang (một mắt), thấy toàn thân? → R1 / R2 / R3 / R4
2. Chất lượng đạt? → R5 / R6 / R7 / R10
3. Nhãn loài đúng? So với ảnh tham chiếu FishBase. **Không chắc thì loại luôn (R8)**, không đoán
4. Trùng lặp? Xác nhận cặp máy đã đánh dấu → R9
5. Giấy phép dùng được? → R11

**Quy tắc cứng:** chỉ được loại ảnh bằng một mã trong bảng. Không loại vì "trông không đẹp" hay "chắc hệ thống sẽ tìm sai ảnh này".

## Bước 4 — Duyệt chéo

**Cặp duyệt:** NT → TV-A → TV-B → NT

Chỉ duyệt lại **những ảnh đã được nhận** của người trước. Ảnh bị loại oan không làm hỏng dữ liệu; ảnh nhận nhầm thì có.

- Đồng ý → giữ nguyên
- Không đồng ý → ghi vào tab `tranh_chap`, cả nhóm quyết cuối buổi

Ghi ra `review/<mã_loài>.r2.csv`. **Ghi lại tỉ lệ đồng thuận** — con số này đưa vào báo cáo làm bằng chứng tiêu chí duyệt đủ rõ và khách quan.

## Bước 5 — Cổng kiểm tra (5–6/10, cả nhóm cùng xem)

Mục tiêu **không phải** tinh chỉnh cho Precision@5 cao, mà là tìm những chỗ sẽ hỏng khi nhân lên 1200 ảnh.

| Kiểm tra | Nếu có vấn đề |
|---|---|
| `rembg` tách sai bao nhiêu %? | > 10% → siết tiêu chí nền ảnh |
| Đặc trưng màu có đang bắt theo **nền** thay vì theo cá? | Có → xem lại mask và tiêu chí ám màu |
| Precision@5 sơ bộ từng nhóm đặc trưng | Mọi nhóm ~100% → loài quá dễ, **đổi loài khó hơn**. Mọi nhóm đều thấp → xem lại tiêu chí ảnh |
| Tỉ lệ ảnh đạt chuẩn theo từng nguồn | Nguồn nào quá thấp → hạ ưu tiên |
| Loài nào không đủ ảnh ứng viên? | Loại khỏi danh sách, dùng loài dự phòng |
| Các cặp bị pHash đánh trùng — in ra vài chục cặp xem bằng mắt | Có cặp là hai con cá khác nhau → **siết ngưỡng pHash** |
| Phân bố cạnh dài hộp bao mask sau `rembg` | Nhiều ảnh dưới 256px → siết tiêu chí ảnh |

**Tiêu chí hoàn thành G1:** chốt cứng **20 loài** + **checklist** + **2 ngưỡng** (kích thước tối thiểu, pHash). Sau cổng này ba thứ đó **không đổi nữa**.

---

# G2 — Thu thập đại trà

**Thời gian:** 7 – 20/10 · **Quy mô:** ~4000 URL → ~1400 ảnh được nhận

Lặp lại đúng bước 1 → 4 của G1, nhưng trên toàn bộ 20 loài.

## Chỉ tiêu

| Hạng mục | Số lượng |
|---|---|
| URL mỗi loài | ~200 |
| Ảnh được nhận mỗi loài | **70–75** *(thu dư để đệm cho ảnh bị loại muộn)* |
| Tổng ảnh được nhận | ~1400 |

## Ước tính công sức

| Việc | Thời gian |
|---|---|
| Thu thập URL | 1–2 buổi/người |
| **Duyệt lượt 1** (~1400 ảnh/người, 5–10 giây/ảnh) | **2–4 giờ/người** |
| Duyệt chéo | ~1 giờ/người |

Chia duyệt thành nhiều buổi ngắn. Duyệt lâu liên tục là mỏi mắt và bắt đầu duyệt ẩu.

## Việc kiểm tra chất lượng của nhóm trưởng

Không kiểm từng dòng. Ba việc là đủ, và script in ra hết:

1. **Lấy mẫu 20 URL ngẫu nhiên** của mỗi người, mở xem. Hơn 2–3 URL sai kiểu → nhắc lại cách làm ngay, trước khi họ làm tiếp.
2. **Xem tỉ lệ bị sơ tuyển loại**. Một người bị loại tới 60% vì kích thước → gần như chắc chắn đang sao chép URL ảnh thu nhỏ.
3. **Đếm số URL trùng** trong phần nộp của từng người. Trùng nhiều → đang lấy lặp lại cùng một trang.

Cập nhật tab `tien_do` mỗi 2–3 ngày để cả nhóm thấy loài nào còn thiếu.

**Tiêu chí hoàn thành G2:** mỗi loài có ≥ 70 ảnh được hai người duyệt đồng ý, không còn tranh chấp chưa giải quyết.

---

# G3 — Chốt dữ liệu và báo cáo mốc 1

**Thời gian:** 20 – 22/10

## Tiền xử lý (máy làm, NT chạy)

Thứ tự **bắt buộc** đúng như sau:

```
rembg → mask → xoay cho trục dài nằm ngang (giới hạn góc ±90°)
      → lật theo cột `huong` đã ghi ở bước duyệt
      → crop theo bbox của mask → pad thành vuông → resize 256×256 PNG
```

Hai chi tiết không được bỏ:

- **Giới hạn góc xoay ±90°.** PCA chỉ xác định được *phương* của trục chính, không xác định được *chiều* — nếu không giới hạn, phép xoay có thể tự quay thêm 180° và làm đầu cá đổi bên, phá mất nhãn hướng.
- **Resize phải letterbox (pad thành vuông trước), không kéo giãn.** Resize thẳng về 256×256 làm méo hình và phá hỏng toàn bộ đặc trưng hình dáng.

**Kiểm tra tự động sau khi chạy:** mô men Hu thứ 7 đổi dấu khi ảnh bị lật gương, nên sau chuẩn hóa mọi ảnh cùng loài phải cùng dấu ở chiều này. Ảnh nào lệch dấu là ảnh còn sai hướng. Phép kiểm miễn phí, chạy một giây trên toàn bộ dữ liệu.

## Kiểm tra bằng mắt (cả nhóm)

Máy sinh **contact sheet**: mỗi trang ~50 ô, **mỗi ô hiện ảnh gốc và mask cạnh nhau**. Khoảng 30 trang → 1–2 giờ chia cho cả nhóm.

| Lỗi | Xử lý |
|---|---|
| **Mask sai** — mất vây, dính nền, cắt đôi thân | Chạy lại tham số khác; nền trùng màu cá quá nhiều thì loại |
| Xoay lệch — cá nằm chéo | Đánh dấu → xoay tay |

Chỉ loại khi **tiền xử lý không thể làm đúng**, và phải ghi rõ lý do. Không lẫn sang lý do "hệ thống tìm kiếm kém trên ảnh này" — cái đó là kết quả đánh giá, không phải lỗi dữ liệu.

Ghi lại **tỉ lệ mask lỗi** để đưa vào báo cáo.

## Đóng băng dữ liệu (NT chạy)

- [ ] Mỗi loài **rút ngẫu nhiên đúng 60 ảnh**, seed cố định — rút ngẫu nhiên, **không chọn tay**, để khỏi vô tình chọn toàn ảnh "đẹp"
- [ ] Chia **gallery / query 80/20**, seed cố định. **Ảnh dùng trong đợt thử chỉ được vào gallery** (nhóm đã xem chúng khi thiết kế đặc trưng → đưa vào query là rò rỉ)
- [ ] Ghi `data_meta/splits/gallery_query.csv`
- [ ] Tính SHA-256 từng ảnh → `releases/processed_v1.sha256`
- [ ] Đóng gói `releases/processed_v1.zip` lên Drive

> **Bộ ảnh đã tiền xử lý chỉ do một người sinh ra.** Cùng một đoạn code chạy trên ba máy vẫn có thể lệch nhau rất nhỏ do khác phiên bản thư viện. Nếu mỗi người tự sinh, số liệu đánh giá do ba người đo sẽ không khớp mà không ai hiểu vì sao.

**Sau bước này dữ liệu bị đóng băng.** Mọi thay đổi về sau phải có lý do được ghi lại.

## Gán Bộ C — thuộc tính ngữ nghĩa

Mỗi người 7 loài, gán **theo loài** chứ không theo ảnh. 20 loài × 10 thuộc tính = 200 ô, khoảng một buổi kể cả duyệt chéo.

**Bốn quy tắc:**
1. **Dựa vào tài liệu tham khảo của loài** (trang loài FishBase), **không dựa vào một ảnh riêng lẻ nào**. Bộ C mô tả loài, không mô tả một cá thể.
2. **Chỉ dùng giá trị trong miền đã định sẵn.** Dáng đuôi chỉ được là chẻ V / chẻ nông / tròn / vuông / hình liềm. Không tự thêm "hơi chẻ".
3. Không rõ ràng (loài có nhiều biến thể màu) → ghi **giá trị phổ biến nhất** + ghi chú. Ghi chú này dùng cho phần "hạn chế" trong báo cáo.
4. Thuộc tính **tỉ lệ dài : cao** lấy **trung bình aspect ratio máy đã đo** trên ảnh của loài đó, không ước lượng bằng mắt.

Ghi vào `data_meta/semantic_attributes.csv`, rồi duyệt chéo như bước 4.

## Báo cáo tiến độ 1

| Mục | Ai viết |
|---|---|
| Mô tả bộ dữ liệu: số loài, số ảnh, nguồn, giấy phép, tỉ lệ đạt chuẩn từng nguồn | NT |
| **Mô tả điểm giống và khác nhau giữa các loài** (mục 1 của đề) — dựa trên bảng Bộ C | TV-A + TV-B |
| Quy trình chuẩn hóa ảnh, tỉ lệ mask lỗi, tỉ lệ đồng thuận khi duyệt | NT |
| **Thiết kế** bộ đặc trưng + độ đo tương đồng (mục 2 của đề) | TV-A (màu, kết cấu) + TV-B (hình dáng, deep) |

**Tiêu chí hoàn thành G3:** 1200 ảnh đã chốt và đóng băng, Bộ C đầy đủ, báo cáo đã nộp.

---

# G4 — Trích đặc trưng và dựng CSDL

**Thời gian:** 23/10 – 10/11

## Chia việc

| Người | Module | Đặc trưng | Chiều |
|---|---|---|---|
| **TV-A** | `features/color.py` | ① Color moments Lab · ② Histogram HSV 4 dải · ③ Màu trội k-means | 9 · 256 · 20 |
| **TV-A** | `features/texture.py` | ④ LBP đa tỉ lệ · ⑤ GLCM · ⑥ Gabor *(tùy chọn)* | 54 · 16 · *48* |
| **TV-B** | `features/shape.py` | ⑦ Tỉ số hình học · ⑧ Hu moments · ⑨ Fourier descriptors · ⑩ Contour signature | 7 · 7 · 20 · 64 |
| **TV-B** | `features/deep.py` | Bộ B — ResNet18 sau GAP, L2-normalize, PCA 128–256 | 512 |
| **NT** | `db/`, `preprocess/` | Schema, nạp dữ liệu, index, chuẩn hóa từng khối | — |

## Quy tắc kỹ thuật bắt buộc

1. **Mọi đặc trưng chỉ trích trên vùng mask**, không trích trên ảnh đầy đủ. Dataset chụp studio có cùng một nền → không làm vậy thì hệ phân biệt theo *nền* chứ không theo *cá*, và phá hỏng luôn phần phân tích giá trị thông tin.
2. **Chuẩn hóa z-score từng khối riêng** trước khi ghép, dùng `mean`/`std` **tính trên tập gallery**. Bỏ bước này thì 256 chiều histogram nhấn chìm 7 chiều Hu moments.
3. **③ Màu trội phải sắp xếp cụm theo tỉ lệ giảm dần.** k-means trả cụm theo thứ tự ngẫu nhiên; không sắp xếp thì hai ảnh giống hệt nhau vẫn cho hai vector khác nhau hoàn toàn.
4. **⑤ GLCM giữ nguyên 4 hướng, không lấy trung bình.** Ảnh đã chuẩn hóa hướng nên hướng hoa văn là thông tin phân biệt loài, không phải nhiễu.
5. **⑨ Fourier phải lấy mẫu lại đường bao về số điểm cố định** (256) trước khi DFT.
6. **⑩ Contour signature:** với hình lõm sâu (đuôi chẻ) một tia cắt biên nhiều điểm → quy ước lấy **giao xa nhất**, áp dụng nhất quán mọi ảnh.

## CSDL (NT)

**PostgreSQL 17 + pgvector** qua Docker Compose (`pgvector/pgvector:pg17`). Mỗi người chạy một bản trên máy mình để phát triển; nạp từ **cùng một bộ ảnh đã chốt** nên ba bản giống hệt nhau. Lúc demo chỉ chạy một bản.

| Bảng | Cột chính |
|---|---|
| `species` | `id`, `code` UNIQUE, `scientific_name`, `genus`, `family`, `family_code`, `common_name_vi` |
| `images` | `id`, `species_id`, `sha256` UNIQUE, `file_path`, `thumbnail BYTEA`, `source`, `source_url`, `license`, `split` |
| `features` | `image_id`, `color vector(285)`, `texture vector(70)`, `shape vector(98)`, `deep vector(512)` |
| `feature_stats` | `block`, `mean[]`, `std[]`, `fisher_score` |

Một cột vector cho **mỗi khối** — nhờ vậy làm được ablation và bảng phân rã khoảng cách ở mục 4b.

**Lưu trữ phân tách:** metadata + vector trong CSDL; **ảnh 256×256 trên hệ thống file**, tên = SHA-256; **thumbnail 128px dạng `BYTEA`** trong CSDL để hiển thị top-5 bằng một câu SQL.

Vì không có ACID giữa hàng trong bảng và file trên đĩa, cần bốn biện pháp:
1. Ảnh **bất biến** — chỉ thêm, không sửa tại chỗ
2. Tên file = **SHA-256 nội dung**, lưu hash trong CSDL
3. Script **`verify_integrity`** đối chiếu bảng ↔ thư mục (thiếu file, file mồ côi, hash sai) — chạy trước mỗi lần đánh giá và trước demo
4. Nạp ảnh theo thứ tự **ghi file trước → insert sau**; insert lỗi thì file mồ côi sẽ bị `verify_integrity` phát hiện

**Tiêu chí hoàn thành G4:** `verify_integrity` sạch, 1200 ảnh đủ 4 khối vector trong CSDL, không có vector NaN hoặc toàn 0.

---

# G5 — Tìm kiếm và web demo

**Thời gian:** 11 – 20/11 · **Phụ trách chính: NT**

## Module tìm kiếm

**Độ đo chọn theo loại đặc trưng** — đây là trái tim của mục 4, không dùng Euclidean cho tất cả:

| Loại | Độ đo | Vì sao |
|---|---|---|
| Histogram (②, ④) | **Chi-square** / **Bhattacharyya** | Là phân phối xác suất, không phải điểm trong không gian |
| Vector deep (B), color moments (①) | **Cosine** | Quan tâm hướng, không quan tâm độ lớn |
| Tỉ số hình học (⑦), Hu (⑧) | **L2** | Là các đại lượng vô hướng độc lập |

**Hợp nhất:** đưa mọi khoảng cách về `[0,1]` bằng min-max trên gallery, rồi `d_total = Σ wᵢ·dᵢ` với `Σwᵢ = 1`.

Trọng số `wᵢ` tìm bằng dò lưới **trên tập gallery**, tối ưu theo mAP. **Tuyệt đối không dùng tập query để dò trọng số** — đó là rò rỉ dữ liệu, kết quả sẽ bị thổi phồng. Thử thêm **rank fusion kiểu Borda** làm phương án so sánh.

**Hai backend sau cùng một interface `search(query_vec, k)`:** pgvector (chính) và NumPy brute-force (dự phòng cho ngày demo).

## Web demo — Streamlit

Toàn bộ logic nằm trong package `fishcbir/`; Streamlit chỉ là lớp vỏ mỏng, để **sơ đồ khối ở mục 4a là sơ đồ thật của code**.

| Tab | Nội dung |
|---|---|
| **Tìm kiếm** | Upload 1 ảnh → top-5 ảnh tương đồng + điểm số, xếp giảm dần |
| **Giải thích** *(mục 4b)* | ① ảnh gốc → mask → ảnh đã xoay/pad/resize · ② histogram HSV theo dải, ảnh LBP, bảng Hu moments + tỉ số hình học, đường cong contour signature · ③ **bảng phân rã khoảng cách** cho từng ứng viên top-5: `d_màu`, `d_kết_cấu`, `d_hình_dáng`, `d_deep`, trọng số, tổng |

Tab "Giải thích" vừa hoàn thành mục 4b, vừa xử lý đúng ràng buộc "không phải hộp đen" khi vấn đáp. **TV-A** làm phần trực quan hóa màu/kết cấu, **TV-B** làm phần hình dáng + Grad-CAM cho Bộ B.

**Ngưỡng similarity:** khi ảnh truy vấn không thuộc loài nào trong CSDL, hệ phải báo được *"không tìm thấy loài tương ứng"* thay vì cứ trả 5 ảnh bất kỳ.

---

# G6 — Báo cáo tiến độ 2

**Thời gian:** 21 – 26/11

| Mục | Ai viết |
|---|---|
| Sơ đồ khối hệ thống, chức năng từng module, dữ liệu vào/ra (mục 4a) | NT |
| **Kiến trúc CSDL: tập trung, lập luận vì sao không phân tán** | NT |
| Thuật toán trích rút từng đặc trưng, kèm giá trị ví dụ (mục 3) | TV-A + TV-B |
| Minh họa kết quả trung gian của một truy vấn cụ thể (mục 4b) | TV-A + TV-B |

Ba điểm nên nêu để chứng tỏ hiểu vấn đề: **client–server không phải phân tán**; cái giá của mô hình "metadata trong DB, nội dung ngoài DB"; và bảng ngưỡng quy mô cho biết từ bao nhiêu vector mới cần phân tán.

---

# G7 — Đánh giá đầy đủ

**Thời gian:** 27/11 – 8/12

## Chia việc

| # | Chỉ số | Ai làm |
|---|---|---|
| 1 | Precision@1, @5, @10 và Recall@10 theo từng loài + trung bình | TV-A |
| 2 | **mAP** | TV-A |
| 3 | **Ablation 6 cấu hình** — color / texture / shape / concat cổ điển / deep / fusion | TV-A |
| 4 | **Fisher score** theo từng khối và từng chiều, kèm **phương sai nội lớp và liên lớp tách riêng** | TV-A |
| 5 | **Ma trận nhầm lẫn giữa các loài** | TV-B |
| 6 | **Precision@5 theo họ** và **nDCG@5** (cùng loài = 2, cùng họ = 1, khác họ = 0) | TV-B |
| 7 | **Thời gian truy vấn + recall**: quét tuần tự vs. index HNSW, đo trên máy CPU-only và máy có GPU | NT |
| 8 | Ma trận tương quan giữa các khối (phát hiện dư thừa) | NT |
| 9 | Ba loại ảnh truy vấn (bảng dưới) | NT |

## Ba loại ảnh truy vấn

| Loại | Ví dụ | Chấm thế nào |
|---|---|---|
| Loài **có** trong CSDL | Cá chép mới | Precision@5 theo loài |
| Loài **không có**, nhưng **họ có** | Cá mè (họ Cá chép) | **Precision@5 theo họ** |
| Cả loài lẫn họ đều **không có** | Cá ngựa | Hệ có báo được "không tìm thấy loài tương ứng"? |

Dòng giữa là phần trả lời được bằng số cho yêu cầu *"ảnh cùng loài hoặc khác loài"* của đề — trước đây chỉ đánh giá định tính được.

## Giá trị thông tin của đặc trưng (mục 2, vế 3)

Chỉ số 3, 4, 8 hợp lại thành phần này. Cách trình bày mạnh nhất: bảng có **ba cột** — phương sai nội lớp (trả lời vế "tương đồng"), phương sai liên lớp (trả lời vế "khác biệt"), và tỉ số Fisher (kết luận). Một bảng đáp ứng trọn vẹn yêu cầu của mục 2.

Thêm **Fisher score theo từng cặp loài** để nói được những câu cụ thể, ví dụ: *"cặp cá hề – cá vàng có màu tổng thể gần trùng nhau nên color moments vô dụng; cặp này được cứu bởi tỉ số contrast GLCM 0°/90°"*.

## Ba quy tắc chống thiên lệch — nhắc lại, và nên ghi thẳng vào báo cáo

1. **Chỉ loại ảnh theo checklist, không bao giờ loại vì hệ thống tìm sai.** Ảnh đạt checklist mà bị trả về sai loài là *kết quả đánh giá*, không phải *ảnh xấu*. Loại chúng chính là tự gian lận chỉ số.
2. **Checklist và danh sách loài đóng băng sau cổng kiểm tra G1.** Sửa được trước khi thu đại trà, không sửa sau khi đã thấy kết quả đánh giá.
3. **Ảnh đợt thử chỉ vào gallery, không vào query.**

## Vấn đề số chiều

Bộ A ~453 chiều + Bộ B 512 chiều ≈ 965 chiều, trong khi chỉ có ~1200 ảnh. Số chiều cao so với số mẫu nên khoảng cách kém nhạy. **Báo cáo cả hai phương án** vì so sánh chúng cũng là một kết quả:
- **PCA** giữ 95% phương sai (thường còn 80–150 chiều)
- **Chọn lọc chiều theo Fisher score**, giữ top-k — cách này dùng lại chính bảng giá trị thông tin ở trên

---

# G8 — Báo cáo tổng và demo

**Thời gian:** 9 – 15/12

- [ ] Báo cáo Word **theo đúng mẫu của trường** — NT gộp, cả ba viết phần của mình
- [ ] Chạy `verify_integrity` trước khi tập demo
- [ ] **Tập demo trước, ít nhất 2 lần**, trên đúng máy sẽ dùng
- [ ] Chuẩn bị sẵn phương án dự phòng: backend NumPy brute-force nếu Docker/Postgres không lên
- [ ] Chuẩn bị 5–7 ảnh truy vấn mẫu, gồm cả ca dễ, ca khó (cặp cùng họ) và ca loài ngoài CSDL

## Câu hỏi vấn đáp nên chuẩn bị sẵn câu trả lời

| Câu hỏi | Chỗ tra |
|---|---|
| CSDL tập trung hay phân tán, vì sao? | Mục "Kiến trúc CSDL" trong `docs/intent/` |
| Client–server có phải là phân tán không? | Cùng mục trên — **không phải** |
| Sao không lưu ảnh vào CSDL? | Mục "Lưu trữ phân tách" |
| Sao không dùng FAISS? | 1200 vector, brute-force vài ms; HNSW của pgvector đã thể hiện khái niệm ANN |
| Đặc trưng nào quan trọng nhất? | Bảng ablation + Fisher score |
| Làm sao biết mạng deep nhìn vào đâu? | Grad-CAM trong tab Giải thích |
| Dữ liệu tự thu thập thật không? | `sources.csv` + bảng phân bố theo nguồn |
| Đưa vào con cá lạ thì sao? | Bảng ba loại ảnh truy vấn |

---

# Phụ lục A — Checklist duyệt ảnh và 11 mã lý do

**Nhận ảnh khi:** đúng 1 con cá · chụp ngang (**chỉ thấy một mắt**) · thấy toàn thân kể cả vây và đuôi · thân cá dài ≥ ~200px · màu không bị ám nặng · nhãn loài chắc chắn · giấy phép dùng được.

**Đầu cá quay trái hay phải đều nhận** — ghi vào cột `huong`, script sẽ lật.

| Mã | Lý do loại |
|---|---|
| R1 | Nhiều hơn 1 con cá |
| R2 | Không chụp ngang (từ trên, chính diện, chéo mạnh — thấy hai mắt) |
| R3 | Bị cắt mất vây hoặc đuôi |
| R4 | Bị che (tay người, lưới, đá, cá khác) |
| R5 | Phân giải thấp — thân cá dưới ~200px, mờ nhòe |
| R6 | Ám màu nặng (dưới nước sâu, đèn màu) |
| R7 | Mẫu vật ngâm formalin, bạc màu |
| R8 | Nhãn loài sai hoặc không chắc chắn |
| R9 | Trùng lặp với ảnh đã có |
| R10 | Không phải ảnh chụp (hình vẽ, minh họa, ảnh ghép) |
| R11 | Giấy phép không cho phép sử dụng |

> **R7 cần chú ý riêng:** FishBase có nhiều ảnh mẫu vật bảo tàng đã bạc màu. FishBase vẫn là nguồn chính, nhưng phải lọc bỏ loại ảnh này — cá bạc màu thì đặc trưng màu mất hết giá trị.

---

# Phụ lục B — Bảng mã loài

**Quy ước:** `<3 chữ đầu của chi>_<3 chữ đầu của tính ngữ loài>`, in hoa, đúng 7 ký tự.

**Năm quy tắc:** ① toàn bộ in hoa (Windows không phân biệt hoa/thường, Git thì có) · ② chỉ A–Z và gạch dưới · ③ lấy từ tên khoa học, không lấy tên tiếng Việt · ④ không nhúng thông tin có thể thay đổi (họ, số thứ tự, người phụ trách) · ⑤ **mã là khóa bất biến** — phân loại học đổi thì giữ mã cũ, chỉ sửa cột tên khoa học, đúng nguyên tắc khóa thay thế trong CSDL.

**Trùng mã:** nới phần loài lên 4 chữ cho **cả hai** loài; còn trùng thì lên 5.

| Mã loài | Mã họ | Tên khoa học | Tên Việt | Vai trò |
|---|---|---|---|---|
| `CYP_CAR` | `CYPR` | *Cyprinus carpio* | Cá chép | Cặp dễ nhầm |
| `CAR_AUR` | `CYPR` | *Carassius auratus* | Cá diếc | Cặp dễ nhầm |
| `ORE_NIL` | `CICH` | *Oreochromis niloticus* | Cá rô phi vằn | Cặp dễ nhầm — cùng chi |
| `ORE_MOS` | `CICH` | *Oreochromis mossambicus* | Cá rô phi đen | Cặp dễ nhầm — cùng chi |
| `AMP_OCE` | `POMA` | *Amphiprion ocellaris* | Cá hề | Khác số khoang trắng |
| `AMP_FRE` | `POMA` | *Amphiprion frenatus* | Cá hề cà chua | Khác số khoang trắng |
| `SAL_SAL` | `SALM` | *Salmo salar* | Cá hồi Đại Tây Dương | Cặp dễ nhầm |
| `ONC_MYK` | `SALM` | *Oncorhynchus mykiss* | Cá hồi vân | Cặp dễ nhầm |
| `SCO_COM` | `SCOM` | *Scomberomorus commerson* | Cá thu | Cùng dáng thoi, khác hoa văn |
| `KAT_PEL` | `SCOM` | *Katsuwonus pelamis* | Cá ngừ vằn | Cùng dáng thoi, khác hoa văn |
| `PAN_HYP` | `PANG` | *Pangasianodon hypophthalmus* | Cá tra | **Cặp rất khó** |
| `PAN_BOC` | `PANG` | *Pangasius bocourti* | Cá basa | **Cặp rất khó** |
| `TRI_PEC` | `OSPH` | *Trichopodus pectoralis* | Cá sặc rằn | Cùng họ, khác cỡ/hoa văn |
| `OSP_GOR` | `OSPH` | *Osphronemus goramy* | Cá tai tượng | Cùng họ, khác cỡ/hoa văn |
| `ZEB_FLA` | `ACAN` | *Zebrasoma flavescens* | Cá đuôi gai vàng | **Cùng họ nhưng khác xa** |
| `PAR_HEP` | `ACAN` | *Paracanthurus hepatus* | Cá đuôi gai xanh | **Cùng họ nhưng khác xa** |
| `PAM_ARG` | `STRO` | *Pampus argenteus* | Cá chim trắng | Đối chứng — dẹt tròn, bạc |
| `CHA_STR` | `CHAN` | *Channa striata* | Cá lóc | Đối chứng — hình trụ dài |
| `ANA_TES` | `ANAB` | *Anabas testudineus* | Cá rô đồng | Đối chứng |
| `CLA_BAT` | `CLAR` | *Clarias batrachus* | Cá trê | Đối chứng — có râu, không vảy |

**Bốn lưu ý trước khi chốt:**

1. `[chờ chốt]` **Phải đối chiếu tên khoa học trên FishBase** trước khi sinh mã. Sinh mã sai rồi sửa thì phải đổi tên thư mục và hàng nghìn file ảnh.
2. **Cá vàng và cá diếc là cùng một loài** (*Carassius auratus*) — cá vàng là dạng đã thuần hóa. Muốn có cả hai thành hai lớp riêng thì không dùng được cấp loài làm nhãn. **Chọn một trong hai**, ghi lý do vào `ghi_chu`.
3. **Không chọn loài cá dẹt** (cá bơn, cá lưỡi trâu). Chúng bất đối xứng thật — hai mắt về một bên, hai mặt thân khác màu — nên phép lật ảnh tạo ra con cá không tồn tại. Danh sách trên không có loài nào như vậy.
4. Dễ đọc nhầm: `CYP_CAR` là cá **chép** (*Cyprinus*), `CAR_AUR` là cá **diếc** (*Carassius*). Chuỗi "CAR" ở vị trí chi trong mã này và vị trí loài trong mã kia.

---

# Phụ lục C — Quy ước tên file và ngưỡng

## Tên ảnh ứng viên (vùng ②)

```
<mã_loài>__<nguồn>__<id_nguồn>.jpg
```

Ví dụ: `AMP_OCE__inat__128934771.jpg` · `CYP_CAR__fishbase__6509_03.jpg`

- **Hai dấu gạch dưới** làm phân cách, để một gạch dưới trong mã loài không gây nhầm khi tách chuỗi
- **Giữ id của nguồn** để truy lại hoặc tải lại ảnh gốc
- Chỉ chữ không dấu, số, gạch dưới. Không khoảng trắng, không tiếng Việt có dấu

## Tên ảnh đã tiền xử lý (vùng ③)

`<sha256>.png` — giai đoạn này không cần truy nguồn nữa, cần tính bất biến.

## Metadata không nằm cạnh ảnh

Không tạo file `.json` kèm mỗi ảnh — số file tăng gấp đôi và Drive đồng bộ chậm hẳn. Nguồn ảnh nằm trong `data_meta/sources/<mã_loài>.csv` trên Git, kèm quy tắc: **ảnh nào không có dòng trong CSV thì coi như không tồn tại**, script kiểm tra sẽ báo lỗi nếu lệch.

## Các ngưỡng

| Ngưỡng | Giá trị | Trạng thái |
|---|---|---|
| Kích thước tối thiểu khi sơ tuyển | Cạnh dài ≥ 320px | Đã chốt 03/10 |
| **Cạnh dài hộp bao mask sau rembg** | **≥ 256px** — phép kiểm quyết định | Đã chốt 03/10 |
| pHash coi là trùng gần | Hamming ≤ 5 / 64 bit | `[chốt sau đợt thử]` |
| Resize ảnh ứng viên | Cạnh dài ≤ 1600px, JPEG q90 | Đã chốt |
| Ảnh đã tiền xử lý | 256×256 PNG | Đã chốt |
| Thân cá tối thiểu (duyệt bằng mắt) | ≥ ~200px | Đã chốt |
| Góc lệch còn nhận được | ≤ ~20° (vẫn chỉ thấy một mắt) | Đã chốt |

**Hai phép kiểm kích thước, không phải một.** Ngưỡng 320px lúc tải chỉ để bỏ icon và ảnh thu nhỏ; nó đo *cả ảnh*, trong khi thứ quan trọng là *con cá dài bao nhiêu pixel*. Một ảnh 2000px có con cá 150px ở góc thì tệ hơn một ảnh FishBase 500px có con cá dài 450px.

Phép kiểm quyết định nằm ở `chuan_hoa.py` sau khi `rembg` cho mask: **cạnh dài hộp bao mask phải ≥ 256px**. Dưới mức đó thì resize về 256×256 là *phóng to*, làm nhòe vảy và sọc — đúng những thứ LBP, GLCM và Gabor đo. Khi đó ảnh mờ sẽ giống nhau *vì đều mờ* chứ không vì cùng loài, cùng loại lỗi với bẫy nền.

Số liệu thật trên 342 ảnh FishBase tải ngày 03/10: ngưỡng 600 sẽ loại oan **27 ảnh tốt (8%)**, vì ảnh FishBase bị giới hạn ở 640px.

**pHash là ngưỡng dễ sai nhất.** Quá lỏng thì loại oan hai ảnh khác nhau của hai con cùng loài; quá chặt thì để lọt ảnh trùng, mà ảnh trùng lọt vào cả gallery lẫn query sẽ thổi phồng điểm đánh giá. Ở cổng kiểm tra G1 phải in ra vài chục cặp bị đánh trùng để xem bằng mắt rồi mới chốt.

## Dung lượng ước tính

| Hạng mục | Dung lượng |
|---|---|
| 4000 ảnh ứng viên, resize 1600px q90 | ~1–1.6 GB |
| 1200 ảnh đã tiền xử lý 256×256 PNG | vài chục – ~150 MB |
| Vector đặc trưng toàn bộ CSDL | ~4–5 MB |

Trong thư mục chia sẻ thường trên Drive, **ai tải lên thì file tính vào dung lượng người đó**, nên ~1.5 GB chia ba người là thoải mái trong 15 GB miễn phí. Không giữ ảnh gốc, vì `sources.csv` đã có URL để tải lại.

---

# Phụ lục D — Danh sách script

| Script | Việc | Ai chạy |
|---|---|---|
| `fetch_inaturalist.py` | Gọi API iNaturalist/GBIF, lấy ảnh + tên loài + giấy phép | NT |
| `fetch_from_sheet.py` | Tải ảnh từ danh sách URL trong Sheet | NT |
| `prepare_candidates.py` | Sơ tuyển kỹ thuật 9 bước | NT |
| `promote.py` | Copy sang Drive, đối chiếu số lượng + hash | NT |
| `review_tool.py` | Duyệt ảnh bằng phím tắt, ghi `review/*.csv` | Cả ba |
| `merge_reviews.py` | Gộp file theo loài, suy ra tập ảnh được nhận, tính tỉ lệ đồng thuận | NT |
| `contact_sheet.py` | Sinh lưới thumbnail ảnh + mask để kiểm tra bằng mắt | NT |
| `preprocess.py` | rembg → xoay → lật → crop → pad → resize | NT |
| `freeze_dataset.py` | Rút 60 ảnh/loài, chia gallery/query, tính SHA-256, đóng gói release | NT |
| `extract_features.py` | Trích Bộ A + Bộ B, nạp CSDL | NT |
| `verify_integrity.py` | Đối chiếu CSDL ↔ thư mục ảnh | Cả ba |
| `evaluate.py` | Toàn bộ chỉ số ở G7 | Cả ba |

---

# Những việc còn chờ chốt

| Việc | Chốt khi nào |
|---|---|
| Đối chiếu tên khoa học 20 loài trên FishBase | Trước 1/10 |
| Chọn giữa cá vàng và cá diếc | Trước 1/10 |
| Hai ngưỡng: kích thước tối thiểu, pHash | Cổng kiểm tra G1 (5–6/10) |
| Danh sách 20 loài bản cuối | Cổng kiểm tra G1 |
| Có làm ⑥ Gabor và CLIP hay không | Sau G4, tùy tiến độ |
| Trọng số fusion | G7, dò lưới trên gallery |
| Spec chính thức (schema chi tiết, chữ ký module) | Viết bằng `spec-driven-development` sau khi chốt tài liệu này |
