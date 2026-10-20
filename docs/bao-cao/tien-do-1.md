# Báo cáo tiến độ 1 — Hệ CSDL lưu trữ và tìm kiếm ảnh cá

**Môn:** Cơ sở dữ liệu đa phương tiện · **Giảng viên:** Hoa Đinh Nguyên
**Nhóm:** NT (nhóm trưởng), TV-A, TV-B · **Ngày nộp:** 22/10/2026

---

## 0. Tóm tắt

Báo cáo này trình bày phần 1 và phần 2 của đề: bộ dữ liệu ảnh và bộ thuộc tính nhận diện.

| Hạng mục | Trạng thái |
|---|---|
| Bộ dữ liệu | **1.085 ảnh · 20 loài · 11 họ** — đã chuẩn hóa và duyệt tay xong |
| Bộ thuộc tính | 4 bộ thiết kế xong; **2 bộ đã cài đặt và đo** |
| Giá trị thông tin | Đã đo bằng **hai phương pháp độc lập** |
| Kết quả sớm | **P@5 = 72,2%** trên 1.085 truy vấn, 5-fold |

Nhóm đã vượt mốc tối thiểu 1.000 ảnh của đề, và đã có kết quả thực nghiệm thật chứ không
chỉ thiết kế trên giấy. Toàn bộ số trong báo cáo tái lập được bằng hai lệnh:

```
python scripts/kiem_tra.py --day-du    # 10/10 bộ kiểm thử đạt
python scripts/danh_gia.py             # sinh lại mọi bảng số
```

---

## 1. Bộ dữ liệu ảnh (phần 1 của đề)

### 1.1 Nguồn và quy mô

Thu thập **4.768 ảnh thô** từ ba nguồn, sau chuẩn hóa và duyệt tay còn **1.085 ảnh**:

| Nguồn | Ảnh thô | Cách lấy | Ghi chú |
|---|---|---|---|
| iNaturalist | ~3.600 | API chính thức, lọc theo giấy phép | Ảnh chụp ngoài tự nhiên, tư thế tự do |
| Archive | 813 | Bộ ảnh cá cảnh có sẵn | Nền sạch, nét nhất trong ba nguồn |
| FishBase | 335 | Trang loài | Ảnh chuẩn mực sinh học |

Khi báo cáo tổng, nhóm sẽ nêu rõ nguồn; phần cần chứng minh là bộ đặc trưng và khả năng
vận hành của hệ, không phải xuất xứ từng tấm ảnh.

### 1.2 Hai mươi loài trên mười một họ

Danh sách loài được chọn theo nguyên tắc **có cặp dễ nhầm và có cặp khác xa**, để bộ dữ
liệu đủ khó mà vẫn đo được.

| Họ | Loài | Vai trò |
|---|---|---|
| Cyprinidae | `CYP_CAR` cá chép · `CAR_AUR` cá vàng | cặp dễ nhầm |
| Cichlidae | `ORE_NIL` rô phi vằn · `ORE_MOS` rô phi đen | **cùng chi** — cặp khó nhất |
| Cichlidae | `SYM_SPP` cá dĩa · `AST_OCE` cá hoàng bảo yến | cặp dễ nhầm (cùng dáng dẹt cao) |
| Pomacentridae | `AMP_OCE` cá hề · `AMP_FRE` cá hề cà chua | **cùng chi** |
| Salmonidae | `SAL_SAL` cá hồi Đại Tây Dương · `ONC_MYK` cá hồi vân | cặp dễ nhầm |
| Scombridae | `SCO_COM` cá thu · `KAT_PEL` cá ngừ vằn | cặp dễ nhầm (cùng dáng thoi) |
| Osphronemidae | `OSP_GOR` cá tai tượng · `BET_SPL` cá xiêm | cặp dễ nhầm |
| Acanthuridae | `ZEB_FLA` đuôi gai vàng · `PAR_HEP` đuôi gai xanh | **cặp khác xa** |
| Pangasiidae | `PAN_HYP` cá tra | đối chứng |
| Channidae | `CHA_STR` cá lóc | đối chứng — thân hình trụ |
| Anabantidae | `ANA_TES` cá rô đồng | đối chứng |
| Poeciliidae | `POE_RET` cá bảy màu | đối chứng — cá rất nhỏ |

Cặp `ZEB_FLA`/`PAR_HEP` cùng họ Acanthuridae nhưng khác nhau hoàn toàn về màu và dáng —
giữ lại có chủ đích để chứng minh **không thể lấy họ làm nhãn phân loại**.

**Quy ước mã loài:** ba chữ đầu của chi + ba chữ đầu của tính ngữ loài, viết hoa (`CYP_CAR`).
Mã là **khóa thay thế bất biến**: nếu phân loại học đổi tên khoa học thì giữ nguyên mã, chỉ
sửa cột tên. Nhờ vậy mọi tham chiếu trong CSDL và trong kết quả đánh giá không bị gãy.

### 1.3 Chuẩn hóa về một dạng duy nhất

Đề yêu cầu ảnh **cùng kích thước, một con mỗi ảnh nằm giữa, chụp ngang, đầu/đuôi hướng
nhất quán, tỉ lệ khung hình tương đồng**. Đường ống chuẩn hóa (`scripts/chuan_hoa.py`):

```
ảnh thô → rembg (u2net) tách nền → mask alpha
        → ba cổng chất lượng tự động
        → mô men trục chính → góc xoay
        → đoán hướng đầu theo bề dày hai đầu thân
        → MỘT phép affine gộp (xoay + thu nhỏ + căn giữa + lật)
        → PNG 384×384 RGBA, nền xám (128,128,128)
```

| Tham số | Giá trị | Lý do |
|---|---|---|
| Khổ ảnh | 384 × 384 | đủ chi tiết cho kết cấu, vẫn nhẹ cho 1.085 ảnh |
| Chiều dài cá | 348 px | chừa lề 18 px mỗi bên |
| Kích thước tối thiểu | 348 px | **không phóng to ảnh nào** — hệ số thu nhỏ đo được 0,30× đến 1,00× |
| Nền | xám (128,128,128) | trung tính, không tạo biên giả như nền đen |
| Kênh alpha | giữ làm mask | mọi đặc trưng chỉ tính trong vùng mask |

**Gộp xoay, thu nhỏ, căn giữa và lật thành một phép affine duy nhất** là quyết định kỹ
thuật quan trọng: làm tuần tự sẽ nội suy hai lần và làm nhòe kết cấu gấp đôi — mà kết cấu
chính là thứ LBP, GLCM và Gabor sẽ đo.

Ba cổng chất lượng tự động loại ảnh hỏng trước khi đến tay người duyệt: mask rỗng (<2%
diện tích), cá quá nhỏ (<348 px), mask vỡ nhiều mảnh (mảnh chính <70%).

### 1.4 Duyệt tay

Toàn bộ **3.486 ảnh** qua chuẩn hóa đều được người duyệt xem từng tấm bằng công cụ riêng
(`scripts/review_tool.py`), quyết định nhận/loại theo một bảng kiểm đã **đóng băng trước
khi duyệt**. Kết quả duyệt lưu trong `data_meta/review/*.r1.csv` kèm mã lý do loại.

Tỉ lệ đạt rất khác nhau giữa các nguồn — đây là số liệu đáng chú ý của dự án:

| Nguồn | Qua được chuẩn hóa | Người duyệt nhận | Độ nét sau chuẩn hóa |
|---|---|---|---|
| Archive | **96%** (mask hỏng 0/813) | 57–98% | **6.327** |
| FishBase | 81% | — | 2.208 |
| iNaturalist | 68% (mask hỏng 17%) | **6–34%** | 1.905 |

Ảnh iNaturalist chụp ngoài tự nhiên nên cá thường bị che, nghiêng, hoặc có nhiều con
trong khung — tỉ lệ nhận chỉ 6–34%. Đây là lý do nhóm phải thu gấp 4,4 lần số ảnh cần.

**Hai loài đã loại** vì nguồn cạn: `CLA_BAT` cá trê (duyệt 187 ảnh chỉ nhận 9, tỉ lệ 4%)
và `PAM_ARG` cá chim trắng (11 ảnh). Ảnh của chúng vẫn giữ trên đĩa để tính tỉ lệ, nhưng
đánh dấu `trang_thai=da_loai` và không vào bộ dữ liệu.

### 1.5 Phân bố và mất cân bằng

| Loài | Ảnh | | Loài | Ảnh | | Loài | Ảnh |
|---|---|---|---|---|---|---|---|
| SYM_SPP | 162 | | ORE_NIL | 45 | | AMP_FRE | 30 |
| BET_SPL | 127 | | PAR_HEP | 44 | | KAT_PEL | 29 |
| POE_RET | 105 | | ONC_MYK | 42 | | ORE_MOS | 28 |
| CAR_AUR | 97 | | PAN_HYP | 39 | | SAL_SAL | 28 |
| AST_OCE | 96 | | CYP_CAR | 35 | | AMP_OCE | 27 |
| ANA_TES | 55 | | OSP_GOR | 35 | | SCO_COM | 21 |
| | | | | | | ZEB_FLA | 21 |
| | | | | | | CHA_STR | 19 |

Trung vị 37 ảnh/loài. **Mất cân bằng 8,5 lần** giữa loài nhiều nhất và ít nhất. Nhóm xử lý
bằng hai biện pháp, không bằng cách xóa bớt ảnh:

1. **Trung bình macro theo loài** ở mọi chỉ số — mỗi loài một phiếu, để cá dĩa 162 ảnh
   không lấn át cá lóc 19 ảnh.
2. **Mức ngẫu nhiên tính thật** theo tỉ lệ từng lớp trong gallery, không lấy 1/20 cho tiện.

### 1.6 Điểm giống và khác nhau giữa các loài

Đề yêu cầu mô tả điểm giống và khác nhau. Nhóm không mô tả bằng văn xuôi mà lập **bảng
thuộc tính ngữ nghĩa 20 loài × 10 thuộc tính** (`data_meta/thuoc_tinh_ngu_nghia.csv`), mỗi
ô lấy từ một **từ vựng có kiểm soát**, tra từ trang loài FishBase. Cách này cho phép đo
được mức độ giống/khác bằng con số thay vì bằng cảm nhận.

| # | Thuộc tính | Từ vựng |
|---|---|---|
| 1 | `dang_than` | thoi · det_cao · det_tron · det_dai · tru_dai |
| 2 | `ti_le_dai_cao` | rat_cao <1,5 · cao 1,5–2,5 · trung_binh 2,5–3,5 · dai 3,5–5 · rat_dai >5 |
| 3 | `mau_nen` | bac · vang · cam · do · nau · xanh_luc · xanh_lam · den · da_mau |
| 4 | `soc` | khong · vach_dung · dai_ngang · van_luoi |
| 5 | `cham` | khong · thua · day · dom_mat |
| 6 | `tuong_phan_lung_bung` | yeu · vua · manh |
| 7 | `dang_duoi` | chia_sau · chia_nhe · cat_bang · tron · xoe_dai |
| 8 | `vay_lung` | ngan · dai_lien · gai_cung · co_vay_mo |
| 9 | `kich_thuoc` | rat_nho <10cm · nho 10–30 · trung_binh 30–60 · lon 60–120 · rat_lon >120 |
| 10 | `moi_truong` | nuoc_ngot · nuoc_lo · nuoc_man |

**Mười hai cặp loài cùng họ** — đây là các cặp khó nhất, bảng đếm số thuộc tính khác nhau:

| Cặp | Số TT khác | Khác ở đâu |
|---|---|---|
| **AMP_FRE / AMP_OCE** | **1** ⚠ | `mau_nen` |
| KAT_PEL / SCO_COM | 3 | `ti_le_dai_cao`, `soc`, `kich_thuoc` |
| PAR_HEP / ZEB_FLA | 4 | `dang_than`, `ti_le_dai_cao`, `mau_nen`, `soc` |
| ORE_MOS / ORE_NIL | 4 | `mau_nen`, `soc`, `tuong_phan_lung_bung`, `moi_truong` |
| BET_SPL / OSP_GOR | 4 | `dang_than`, `mau_nen`, `dang_duoi`, `kich_thuoc` |
| AST_OCE / ORE_MOS | 5 | 5 thuộc tính |
| AST_OCE / SYM_SPP | 5 | 5 thuộc tính |
| ONC_MYK / SAL_SAL | 5 | 5 thuộc tính |
| AST_OCE / ORE_NIL | 6 | 6 thuộc tính |
| CAR_AUR / CYP_CAR | 7 | 7 thuộc tính |
| ORE_NIL / SYM_SPP | 7 | 7 thuộc tính |
| ORE_MOS / SYM_SPP | 8 | 8 thuộc tính |

Hai cặp thú vị nhất:

- **Cá thu và cá ngừ vằn** cùng dáng thoi, cùng màu bạc, cùng đuôi chia sâu. Chỉ khác ở
  **phương của hoa văn**: cá thu có vạch **đứng**, cá ngừ vằn có dải **chạy dọc thân**.
  Đây chính là lý do GLCM trong Bộ A **giữ nguyên 4 hướng** thay vì lấy trung bình.
- **Hai loài cá hề** chỉ khác nhau ở đúng **một** thuộc tính. Thực tế chúng còn khác ở
  **số khoang trắng** (3 so với 1), nhưng từ vựng `soc` không mã hóa được số lượng. Nhóm
  giữ nguyên hạn chế này và coi đó là một kết quả — xem mục 2.5.

---

## 2. Bộ thuộc tính nhận diện (phần 2 của đề)

### 2.1 Bốn bộ đặc trưng

| Bộ | Nội dung | Số chiều | Trạng thái |
|---|---|---|---|
| **A** | 10 đặc trưng cổ điển: màu, kết cấu, hình dáng | 501 | ① đã cài, ②–⑩ đã thiết kế |
| **B** | ResNet18 huấn luyện sẵn ImageNet | 512 | **đã cài và đo** |
| **C** | Thuộc tính ngữ nghĩa do người mô tả | 35 sau mã hóa | **đã cài và đo** |
| **D** | Hợp nhất A ⊕ B có trọng số | 1.013 | chưa làm |

### 2.2 Bộ A — 501 chiều cổ điển

| Nhóm | # | Đặc trưng | Chiều |
|---|---|---|---|
| **Màu** | ① | Color moments Lab (trung bình, độ lệch, độ xiên) | 9 |
| (285) | ② | Histogram HSV theo **4 dải dọc thân**, H32 + S16 + V16 | 256 |
| | ③ | Màu trội k-means k=5 trong Lab, sắp theo tỉ lệ giảm dần | 20 |
| **Kết cấu** | ④ | LBP uniform bất biến xoay, 3 bán kính P8/R1 + P16/R2 + P24/R3 | 54 |
| (118) | ⑤ | GLCM 4 thuộc tính × **4 hướng giữ riêng** | 16 |
| | ⑥ | Gabor 4 tần số × 6 hướng × (trung bình, độ lệch) | 48 |
| **Hình dáng** | ⑦ | 7 tỉ số hình học | 7 |
| (98) | ⑧ | Hu moments, nén bằng `-sign(h)·log₁₀|h|` | 7 |
| | ⑨ | Fourier descriptors, lấy mẫu lại 256 điểm, chuẩn hóa theo \|F(1)\| | 20 |
| | ⑩ | Contour signature 64 mẫu | 64 |

Bốn quyết định kỹ thuật bắt buộc, đã ghi vào mã nguồn:

1. **Chỉ trích trên vùng mask.** Nền xám nếu lọt vào sẽ kéo mọi ảnh về cùng một màu trung
   tính và xóa sạch khác biệt giữa các loài. Với đặc trưng kết cấu còn phải **co mask vào
   ~5 px**, vì cửa sổ LBP/GLCM ở sát biên sẽ hút nền vào và sinh kết cấu giả.
2. **Chuẩn hóa z-score từng khối riêng**, mean/std tính **trên gallery của từng fold** —
   nếu tính trên toàn bộ dữ liệu thì thông tin của tập truy vấn rò sang gallery.
3. **Độ đo chọn theo loại đặc trưng**: histogram → Chi-square/Bhattacharyya; moments và
   đặc trưng sâu → cosine; tỉ số hình học → L2.
4. **Trọng số hợp nhất dò bên trong từng fold**, chỉ trên gallery.

### 2.3 Bộ B — ResNet18

Dùng mạng huấn luyện sẵn làm bộ trích đặc trưng **đông cứng**: bỏ lớp phân loại, lấy vector
512 chiều sau global average pooling, chuẩn hóa L2, đo bằng cosine.

Không tinh chỉnh, vì hai lý do: 1.085 ảnh chia 20 loài là quá ít để huấn luyện mà không
học thuộc lòng; và nếu tinh chỉnh thì **mỗi fold phải huấn luyện lại một mô hình riêng**
để không rò nhãn tập truy vấn vào gallery. Mạng đông cứng cho đặc trưng không phụ thuộc
fold, nên phép đánh giá vẫn trung thực mà chi phí chỉ bằng một lần trích.

Chuẩn hóa L2 rồi đo cosine là có chủ đích: **độ dài** vector ResNet phản ánh độ mạnh kích
hoạt (ảnh tương phản cao cho vector dài hơn) chứ không phản ánh loài — chỉ **hướng** mới
mang thông tin loài.

### 2.4 Đặc trưng tìm tương đồng và đặc trưng tìm khác biệt

Đề yêu cầu phân biệt hai loại. Nhóm dùng **phân rã phương sai Fisher** để định nghĩa chúng
một cách đo được, thay vì xếp loại theo cảm tính:

- **Đặc trưng tìm tương đồng** — phương sai **nội lớp** thấp: mọi ảnh của cùng một loài cho
  giá trị gần nhau, dù chụp ở điều kiện khác nhau. Nhờ vậy ảnh truy vấn kéo được đúng
  những ảnh cùng loài về gần.
- **Đặc trưng tìm khác biệt** — phương sai **liên lớp** cao: các loài khác nhau cho giá trị
  tách xa nhau.

Một đặc trưng tốt cần **cả hai**, và tỉ số giữa chúng chính là Fisher score. Nhóm sẽ trình
bày bảng **ba cột** (phương sai nội lớp / liên lớp / tỉ số) ở báo cáo tiến độ 2, tính trên
**mẫu cân bằng** (rút ngẫu nhiên 19 ảnh mỗi loài) để kết quả không lệch về lớp lớn.

Phân loại sơ bộ theo thiết kế:

| Thiên về **tương đồng** | Thiên về **khác biệt** |
|---|---|
| ⑦ tỉ số hình học — ổn định trong loài | ② histogram HSV theo dải — rất khác giữa loài có hoa văn |
| ⑧ Hu moments — bất biến xoay và tỉ lệ | ③ màu trội — tách mạnh nhóm cá cảnh màu rực |
| ⑩ contour signature — dáng thân là tính trạng loài | ⑤ GLCM 4 hướng — bắt phương của sọc |
| Bộ B ResNet18 — bất biến với điều kiện chụp | ⑥ Gabor — bắt tần số hoa văn |

### 2.5 Giá trị thông tin — đo bằng hai phương pháp độc lập

#### Phương pháp 1: entropy trên bảng thuộc tính ngữ nghĩa

20 loài cho **190 cặp loài**. Entropy tối đa về lý thuyết là log₂20 = **4,32 bit**.

| Thuộc tính | Giá trị dùng | Entropy (bit) | Cặp tách được | Tỉ lệ |
|---|---|---|---|---|
| `mau_nen` | 8/9 | **2,65** | 162/190 | **85%** |
| `dang_duoi` | 5/5 | 2,18 | 152/190 | 80% |
| `kich_thuoc` | 5/5 | 2,06 | 147/190 | 77% |
| `ti_le_dai_cao` | 5/5 | 2,06 | 143/190 | 75% |
| `dang_than` | 5/5 | 2,04 | 145/190 | 76% |
| `vay_lung` | 4/4 | 1,74 | 131/190 | 69% |
| `soc` | 4/4 | 1,73 | 134/190 | 71% |
| `tuong_phan_lung_bung` | 3/3 | 1,35 | 111/190 | 58% |
| `moi_truong` | 3/3 | 1,30 | 108/190 | 57% |
| `cham` | 4/4 | **1,02** | 69/190 | **36%** |

Ba kết luận:

1. **Không thuộc tính nào đạt 4,32 bit.** Cao nhất là 2,65. Nghĩa là **không một đặc trưng
   đơn lẻ nào phân loại nổi 20 loài** — phải phối hợp nhiều khối. Đây là lập luận định
   lượng cho kiến trúc nhiều bộ đặc trưng, thay vì chỉ nói "ghép thì tốt hơn".
2. **Entropy thấp không có nghĩa là vô dụng.** `cham` chỉ 1,02 bit vì 14/20 loài không có
   chấm. Nhưng giá trị `dom_mat` **chỉ** `AST_OCE` có, `day` **chỉ** `ONC_MYK` và `POE_RET`
   có. Nó vô dụng với đa số cặp nhưng quyết định với vài cặp cụ thể.
3. **Có những phân biệt thị giác mà thuộc tính ngữ nghĩa không biểu diễn được.** Cặp cá hề
   chỉ khác 1 thuộc tính vì từ vựng không mã hóa được *số lượng* khoang trắng. Chính khoảng
   trống này là lý do tồn tại của Bộ A và Bộ B.

#### Phương pháp 2: đo trực tiếp bằng Precision@5

Xem mục 3. Hai phương pháp cho **cùng một kết luận**, đây là điểm nhóm muốn nhấn mạnh.

---

## 3. Kết quả thực nghiệm sớm

### 3.1 Phương pháp đánh giá

Nhóm dùng **5-fold phân tầng theo loài** thay vì chia 80/20 một lần. Lý do: chia một lần
chỉ cho ~217 truy vấn, và loài ít ảnh nhất (cá lóc, 19 ảnh) chỉ còn 4 truy vấn — sai số
trên loài đó lớn tới mức con số vô nghĩa. Với 5-fold, **mọi ảnh đều lần lượt làm truy vấn
đúng một lần**, cho **1.085 truy vấn**, mà không tốn thêm phút duyệt ảnh nào.

Năm fold có kích thước đúng bằng nhau: 217 / 217 / 217 / 217 / 217. Mọi loài có mặt ở cả
5 fold. Seed cố định (20261020) nên phép chia tái lập được.

**Ba quy tắc trung thực**, cài thẳng vào mã nguồn chứ không chỉ ghi trong tài liệu:

| Quy tắc | Cài ở đâu |
|---|---|
| Không ảnh nào vừa ở gallery vừa ở truy vấn trong cùng fold | `timkiem.kiem_tra_tach_biet` — **ném lỗi** nếu vi phạm |
| Trung bình macro theo loài, không theo ảnh | `timkiem.macro_theo_loai` |
| mean/std chuẩn hóa chỉ lấy từ gallery | `timkiem.tham_so_chuan_hoa` chỉ nhận gallery làm đầu vào |

Thêm hai quy tắc về dữ liệu: chỉ loại ảnh theo bảng kiểm, **không bao giờ loại vì hệ tìm
sai**; và danh sách loài cùng bảng kiểm đã đóng băng trước khi duyệt.

### 3.2 Kết quả

5-fold · 1.085 truy vấn · trung bình macro theo loài · ± độ lệch chuẩn giữa 5 fold

| Chỉ số | Bộ A① — 9 chiều | **Bộ B — 512 chiều** | Ngẫu nhiên |
|---|---|---|---|
| Precision@1 | 37,1% ± 2,8% | **80,9% ± 2,1%** | |
| **Precision@5** | 32,2% ± 1,2% | **72,2% ± 1,1%** | 5,0% |
| Precision@10 | 28,6% ± 1,2% | **66,3% ± 1,2%** | |
| Recall@10 | 8,1% ± 0,4% | 20,8% ± 0,5% | |
| mAP | 18,7% ± 0,9% | **52,1% ± 0,8%** | |
| Độ chính xác top-1 | 37,0% | **80,8%** | |

Chỉ riêng **9 chiều** color moments đã cho P@5 **gấp 6,4 lần** mức ngẫu nhiên. Bộ B đạt
**gấp 14,4 lần**. Thời gian trích đặc trưng trên CPU: 29 ms/ảnh (Bộ A①), 37 ms/ảnh (Bộ B).

> **Lưu ý về Recall@10.** Con số 20,8% trông thấp nhưng không phản ánh hệ kém. Cá dĩa có
> 130 ảnh cùng loài trong gallery, nên dù top-10 đúng cả 10 thì recall vẫn chỉ 10/130 =
> 7,7%. Với lớp mất cân bằng, Recall@10 đo **kích thước lớp** nhiều hơn đo chất lượng.
> Nhóm vẫn báo cáo để đủ bộ chỉ số, nhưng không dùng nó để kết luận.

### 3.3 Precision@5 theo loài

| Loài | Ảnh | Bộ A① | Bộ B | Chênh |
|---|---|---|---|---|
| Cá rô phi đen | 28 | 11% | 32% | +21 |
| Cá chép | 35 | 14% | 39% | +25 |
| Cá rô phi vằn | 45 | 18% | 41% | +23 |
| Cá tai tượng | 35 | 13% | 43% | +30 |
| Cá hồi Đại Tây Dương | 28 | 17% | 49% | +32 |
| Cá lóc | 19 | 7% | 54% | +46 |
| Cá rô đồng | 55 | 18% | 56% | +38 |
| Cá thu | 21 | 16% | 66% | +50 |
| Cá tra | 39 | 11% | 68% | +56 |
| Cá hồi vân | 42 | 10% | 69% | +59 |
| Cá hoàng bảo yến | 96 | 36% | 83% | +46 |
| Cá ngừ vằn | 29 | 35% | 87% | +52 |
| Cá vàng | 97 | 54% | 87% | +33 |
| Cá hề cà chua | 30 | 25% | 91% | +67 |
| Cá đuôi gai vàng | 21 | 69% | 92% | +24 |
| Cá xiêm | 127 | 48% | 95% | +47 |
| Cá hề | 27 | 19% | **96%** | **+77** |
| Cá bảy màu | 105 | 74% | 97% | +24 |
| Cá dĩa | 162 | 70% | 98% | +29 |
| Cá đuôi gai xanh | 44 | 79% | **100%** | +21 |

**Cả 20/20 loài đều tăng, không loài nào tụt.**

### 3.4 Hai phương pháp đo giá trị thông tin cho cùng một kết luận

Xếp 4 loài yếu nhất và 4 loài mạnh nhất của Bộ A① cạnh giá trị `mau_nen` trong bảng thuộc
tính ngữ nghĩa:

| Yếu nhất | P@5 | `mau_nen` | | Mạnh nhất | P@5 | `mau_nen` |
|---|---|---|---|---|---|---|
| Cá lóc | 7% | `nau` | | Cá đuôi gai xanh | 79% | `xanh_lam` ⭐ |
| Cá hồi vân | 10% | `bac` | | Cá bảy màu | 74% | `da_mau` |
| Cá tra | 11% | `bac` | | Cá dĩa | 70% | `da_mau` |
| Cá rô phi đen | 11% | `den` | | Cá đuôi gai vàng | 69% | `vang` ⭐ |

⭐ = màu duy nhất trong 20 loài.

Bốn loài kém nhất đều là cá **nâu, bạc, đen** — đúng những loài mà `mau_nen` không mang
thông tin. Bốn loài tốt nhất đều có màu rực hoặc màu riêng. Hai phương pháp hoàn toàn độc
lập — entropy tính trên bảng do người gán, P@5 đo trên ảnh thật — cho cùng một kết luận.

**Cặp cá hề khép lại câu chuyện này.** Bộ C chỉ tách được bằng 1 trong 10 thuộc tính; Bộ A①
chỉ đạt 19% và 25%; Bộ B đạt **96% và 91%**. Mạng sâu nhìn thấy đúng cái đặc điểm (số
khoang trắng) mà cả từ vựng ngữ nghĩa lẫn đặc trưng màu đều bỏ sót.

### 3.5 Những gì vẫn còn khó

| Loài | Top-1 | Nhầm chủ yếu sang |
|---|---|---|
| Cá rô phi vằn | 53% | **cá rô phi đen** (13 ca, cùng chi) |
| Cá rô phi đen | 57% | **cá rô phi vằn** (7 ca, cùng chi) |
| Cá chép | 60% | cá rô đồng, cá hồi Đại Tây Dương |
| Cá tai tượng | 60% | cá rô phi vằn |

Trong 148 lỗi top-1, **41 lỗi (28%) là nhầm sang loài cùng họ** — hệ sai theo kiểu "có lý"
chứ không ngẫu nhiên. Hai loài *Oreochromis* cùng chi vẫn là cặp khó nhất, đúng như dự
đoán khi chọn danh sách loài. Đây chính là phần đất của các đặc trưng còn lại trong Bộ A:
hoa văn `vach_dung` của rô phi vằn là **kết cấu**, không phải màu, nên ⑤ GLCM và ⑥ Gabor
được kỳ vọng cứu đúng cặp này.

---

## 4. Kiến trúc và mô hình dữ liệu

### 4.1 Kiến trúc (theo khung Bài giảng 4)

| Trục phân loại | Lựa chọn |
|---|---|
| Architectural style | **Centralized** |
| Storage principle | **Homogeneity** |
| Tổ chức | Client–server **3 tầng**: giao diện Streamlit / logic `fishcbir` / lưu trữ |

Lưu ý một điểm dễ nhầm: việc tách metadata khỏi file ảnh **không phải** separation
principle. Separation là tách theo **loại phương tiện**, mà hệ này chỉ có một loại là ảnh.

### 4.2 Mô hình dữ liệu (theo khung Bài giảng 5)

Nhóm chọn **Object-Relational (ORDBMS) + Vector**, cụ thể là **PostgreSQL 17 + pgvector**.

Neo trực tiếp vào bài giảng: slide 40 liệt kê PostgreSQL làm ví dụ ORDBMS; slide 42 nói
"Extensions (PostGIS, pgvector) push ORDBMS further toward multimedia & similarity"; và
**slide 55 mô tả gần như nguyên văn đề tài này** — truy hồi ảnh bằng vector nhúng với câu
truy vấn `SELECT id FROM images ORDER BY embedding <=> :q LIMIT 5`.

Lý do bác các mô hình khác:

| Mô hình | Vì sao không |
|---|---|
| Quan hệ thuần | Không có toán tử khoảng cách trên vector |
| Hướng đối tượng | Bài toán không có phân cấp kế thừa hay OID |
| NoSQL | Lược đồ ở đây cố định, chỉ 1.085 bản ghi, lại cần ACID |
| Đồ thị | Không có quan hệ giữa các ảnh; slide 52 ghi rõ "weaker alone for pure k-NN on high-dim vectors" |
| Vector DB thuần | Slide 56: "still needs metadata store for rich filters" → phải quản hai hệ, mất ACID |

Ảnh lưu trên hệ thống file, tên file là **SHA-256** của nội dung; CSDL giữ đường dẫn và
hash. Hàm `verify_integrity` sẽ đối chiếu bảng với thư mục ảnh.

---

## 5. Quá trình thực hiện và bài học

Phần này nhóm ghi lại trung thực, vì bản thân quá trình cũng là nội dung cần trình bày.

**Sự cố 1 — thu thập bằng công cụ tìm kiếm thất bại hoàn toàn.** Lần thử đầu dùng Bing
Image để tải theo tên Latin. Bing bỏ qua tên khoa học ít phổ biến và trả về nội dung
thương mại không liên quan (tai nghe, mỹ phẩm, sơ đồ cầu lông). Nhóm đã **xóa 2.152 ảnh
rác** và chuyển hẳn sang API iNaturalist có lọc theo `taxon_id`.
→ *Bài học: luôn dựng contact sheet và xem tận mắt trước khi chạy một lô lớn.*

**Sự cố 2 — nhãn tiếng Việt gán nhầm loài.** Dòng `AST_OCE` ghi tên khoa học
*Astronotus ocellatus* (cá Oscar) cạnh tên tiếng Việt "cá hồng két" — nhưng cá hồng két là
**cá lai blood parrot**, một loài hoàn toàn khác và không có tên khoa học hợp lệ. Nhóm dựng
contact sheet 24/96 ảnh để phân xử: ảnh đúng là *Astronotus ocellatus*, nên **tên khoa học
đúng, tên tiếng Việt sai**. Đã sửa thành "cá hoàng bảo yến".
→ *Bài học: cùng một bài học với sự cố 1, và lần này dự đoán ban đầu còn sai cả chiều.*

**Quyết định 1 — không bổ sung ảnh để cân bằng lớp.** Nhóm đã tính: nâng 7 loài dưới 30
ảnh lên 40 ảnh cần tải thêm ~1.040 ảnh và duyệt tay ~700 ảnh, tốn khoảng 2 giờ, mà chỉ
giảm sai số 1,41 lần. Chuyển sang 5-fold đạt hiệu quả tương đương với **0 phút duyệt**.

**Quyết định 2 — giữ nguyên hạn chế thay vì che đi.** Cặp cá hề chỉ tách được bằng 1 thuộc
tính ngữ nghĩa. Nhóm không thêm giá trị từ vựng để "chữa" con số, mà giữ nguyên và báo cáo,
vì chính nó là bằng chứng cho việc phải có nhiều bộ đặc trưng.

**Kiểm thử.** Dự án có 10 bộ kiểm thử tự động (`python scripts/kiem_tra.py --day-du`), gồm
cả bộ đối chiếu với dữ liệu thật trên đĩa (đếm đúng 1.085 ảnh, mọi loài có mặt ở cả 5 fold).
Phép kiểm quan trọng nhất của khối đặc trưng màu là: **đổi màu nền ngoài mask không được
làm đổi kết quả** — nếu phép kiểm này hỏng nghĩa là nền đang rò vào đặc trưng.

---

## 6. Hạn chế đã biết

| Hạn chế | Ảnh hưởng |
|---|---|
| `SYM_SPP` là **nhãn cấp chi** (*Symphysodon spp*), không phải cấp loài | Thuộc tính của nó là trung bình của nhiều dạng lai |
| Từ vựng `soc` không mã hóa **số lượng** vạch | Cặp cá hề chỉ còn 1 thuộc tính phân biệt |
| Không có thuộc tính **râu** | Cá chép có 2 đôi râu, cá vàng không — mất một dấu hiệu chắc chắn |
| Bộ C gán theo **loài**, không theo ảnh | **Không dùng được để truy vấn** ảnh loài lạ; chỉ dùng phân tích và giải thích |
| rembg làm **mất vây** mỏng và trong suốt | Giới hạn cố hữu của u2net; đã thử alpha matting và isnet, không cải thiện |
| Mất cân bằng lớp 8,5 lần | Xử lý bằng macro-average, không xóa ảnh |
| `BET_SPL`, `POE_RET`, `CAR_AUR` biến dị màu/đuôi rất lớn | Giá trị ngữ nghĩa chỉ đúng với phần lớn ảnh |

---

## 7. Kế hoạch tới mốc 2 (26/11)

| Việc | Nội dung |
|---|---|
| T5–T7 | Hoàn thiện Bộ A: màu ②③, kết cấu ④⑤⑥, hình dáng ⑦⑧⑨⑩ |
| T10 | Chuẩn hóa khối + độ đo theo loại + hợp nhất có trọng số → Bộ D |
| T11–T13 | Docker PostgreSQL 17 + pgvector, nạp dữ liệu, chỉ mục HNSW |
| T14–T15 | Web demo Streamlit: tab Tìm kiếm và tab Giải thích |
| T17 | **Bảng Fisher ba cột** + ablation 6 cấu hình + Fisher theo cặp loài cùng họ |
| T18 | Ma trận nhầm lẫn chuẩn hóa theo hàng + P@5 theo họ + ảnh loài ngoài CSDL |

Hai câu hỏi nhóm sẽ trả lời bằng số đo ở mốc 2:

1. **Đặc trưng kết cấu có cứu được cặp rô phi không?** Giả thuyết: có, vì `vach_dung` là
   hoa văn chứ không phải màu.
2. **Hợp nhất A ⊕ B có tốt hơn riêng B không?** Nếu không, nhóm sẽ báo cáo đúng như vậy.

---

## Phụ lục — tái lập kết quả

```bash
python -m pip install -r requirements.txt
python scripts/kiem_tra.py --day-du     # 10/10 bộ kiểm thử
python scripts/bo_c.py --kiem-tra       # bảng entropy Bộ C
python scripts/danh_gia.py              # mọi bảng số ở mục 3
```

Xuất bản nộp định dạng Word:

```bash
python -m pip install pypandoc_binary       # pandoc kèm sẵn, không cần cài riêng
python -c "import pypandoc; pypandoc.convert_file('docs/bao-cao/tien-do-1.md','docx',  outputfile='docs/bao-cao/Bao-cao-tien-do-1.docx',format='gfm',  extra_args=['--toc','--toc-depth=2','--standalone','--metadata','lang=vi-VN'])"
```

| Tạo ra | Nội dung |
|---|---|
| `data_meta/splits/folds.csv` | Phép chia 5-fold, 1.085 dòng |
| `ket_qua/chi_so.csv` | Chỉ số từng fold cho từng khối |
| `ket_qua/p5_theo_loai.csv` | P@5 theo loài |

**Tài liệu kèm theo:** `docs/kien-truc-va-mo-hinh-du-lieu.md` · `docs/bo-c-ngu-nghia.md` ·
`docs/intent/fish-image-retrieval.md` · `tasks/plan.md`
