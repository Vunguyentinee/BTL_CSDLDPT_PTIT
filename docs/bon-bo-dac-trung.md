# Bốn bộ đặc trưng — tên gọi, công nghệ và cách trích rút

> Bản giải thích ngắn. Chi tiết Bộ C xem `docs/bo-c-ngu-nghia.md`;
> số liệu thực nghiệm xem `docs/bao-cao/tien-do-1.md`.
> Mục [Thuật ngữ](#thuật-ngữ) ở cuối giải nghĩa các từ viết tắt dùng chung.

## Tổng quan

"Trích rút đặc trưng" (*feature extraction*) là biến **một tấm ảnh** thành **một dãy số**
để máy so sánh được. Hai ảnh giống nhau phải cho hai dãy số gần nhau. Dãy số đó gọi là
**vector đặc trưng** (*feature vector*), độ dài của nó gọi là **số chiều** (*dimension*).

| Bộ | Cách lấy số | Chiều | Trạng thái |
|---|---|---|---|
| **A** | Công thức toán do người viết, 10 đặc trưng | 501 | ① xong, ②–⑩ thiết kế |
| **B** | Mạng nơ-ron ResNet18 tự học | 512 | **xong** |
| **C** | Người đọc tài liệu rồi điền bảng | 35 | **xong** |
| **D** | Ghép A với B | 1.013 | chưa làm |

Ba cách hoàn toàn khác nhau: **A** người hiểu được từng con số, **B** máy tự quyết định,
**C** người viết ra bằng chữ. Chúng bù nhau chứ không thay nhau.

---

## Bộ A — 501 chiều, công thức cổ điển

Còn gọi là **đặc trưng thủ công** (*hand-crafted features*): người thiết kế viết sẵn công
thức, máy chỉ thi hành. Chia theo **ba kênh thị giác độc lập** — màu, kết cấu, hình dáng.
Cá có thể giống nhau ở một kênh mà khác hẳn ở kênh kia: cá thu và cá ngừ cùng màu bạc
(màu giống) nhưng hoa văn khác phương (kết cấu khác).

### Nhóm màu — 285 chiều

#### ① Color moments — *mô men màu* · 9 chiều

**Là gì:** ba con số thống kê tóm tắt toàn bộ phân bố màu của con cá — **trung bình**
(màu nào), **độ lệch chuẩn** (màu có đều không), **độ xiên** (lệch về phía sáng hay tối).
Gọi là "mô men" vì trong xác suất, ba đại lượng này là mô men bậc 1, 2, 3 của một phân bố.

**Trích thế nào:** đổi ảnh sang hệ màu **Lab**, rồi tính 3 con số đó cho từng kênh L, a, b
— chỉ trên các điểm ảnh nằm trong mask. 3 × 3 = 9 số.

#### ② Histogram HSV theo dải — *biểu đồ tần suất màu theo dải dọc thân* · 256 chiều

**Là gì:** **histogram** là biểu đồ đếm xem mỗi khoảng màu xuất hiện bao nhiêu lần. Ở đây
không đếm cho cả con cá mà đếm riêng cho **4 khúc** từ đầu đến đuôi, nên giữ được thông
tin **màu nằm ở đâu**.

**Trích thế nào:** đổi sang hệ màu **HSV**, chia thân cá thành 4 dải dọc đều nhau, mỗi dải
đếm 32 ngăn cho H + 16 ngăn cho S + 16 ngăn cho V = 64. 4 × 64 = 256 số.

> **Vì sao cần ② khi đã có ①:** ① trộn cả con cá thành một màu trung bình, nên cá
> *đầu đỏ đuôi vàng* và cá *đầu vàng đuôi đỏ* cho kết quả **y hệt nhau**.

#### ③ Dominant colors — *màu trội* · 20 chiều

**Là gì:** 5 màu chủ đạo của con cá và tỉ lệ diện tích mỗi màu chiếm.

**Trích thế nào:** dùng thuật toán **k-means** gom mọi điểm ảnh thành 5 cụm màu trong
không gian Lab, lấy tâm mỗi cụm (3 số) kèm tỉ lệ (1 số). 5 × 4 = 20 số.

> **Bẫy:** k-means trả về 5 cụm theo thứ tự **ngẫu nhiên** mỗi lần chạy, nên bắt buộc
> **sắp xếp lại theo tỉ lệ giảm dần** — nếu không, hai ảnh giống hệt nhau cho hai vector
> khác nhau.

### Nhóm kết cấu — 118 chiều

**Kết cấu** (*texture*) là **hoa văn bề mặt**: vảy, sọc, chấm, độ gồ ghề. Khác với màu ở
chỗ nó mô tả **quan hệ giữa các điểm ảnh kề nhau**, không phải giá trị từng điểm.

#### ④ LBP — *Local Binary Pattern*, mẫu nhị phân cục bộ · 54 chiều

**Là gì:** một cách mô tả bề mặt gồ ghề hay nhẵn bằng cách chỉ so **sáng hơn hay tối hơn**,
không quan tâm sáng hơn bao nhiêu — nhờ vậy không bị ảnh hưởng bởi điều kiện chiếu sáng.

**Trích thế nào:** với mỗi điểm ảnh, so nó với các điểm xung quanh; điểm nào sáng hơn ghi
**1**, tối hơn ghi **0**. Ghép lại thành một số nhị phân, rồi đếm tần suất các số đó trên
cả con cá.

> Dùng **3 bán kính** (R1, R2, R3) vì vảy cá nhỏ và sọc cá lớn nằm ở hai thang kích thước
> khác nhau — một bán kính chỉ bắt được một thang. Biến thể dùng là *uniform, bất biến
> xoay*: 10 + 18 + 26 = 54.

#### ⑤ GLCM — *Gray-Level Co-occurrence Matrix*, ma trận đồng hiện mức xám · 16 chiều

**Là gì:** một bảng đếm xem **cặp điểm ảnh kề nhau** có độ sáng (i, j) xuất hiện bao nhiêu
lần. Từ bảng đó rút ra 4 thuộc tính: *contrast* (tương phản), *correlation* (tương quan),
*energy* (năng lượng), *homogeneity* (đồng nhất).

**Trích thế nào:** lập bảng đếm theo 4 hướng — 0°, 45°, 90°, 135° — rồi tính 4 thuộc tính
cho mỗi hướng. 4 × 4 = 16 số.

> **Vì sao giữ nguyên 4 hướng, không lấy trung bình:** đúng bộ dữ liệu này có
> **cá thu vạch đứng** và **cá ngừ vằn dải ngang**. Lấy trung bình 4 hướng là tự tay xóa
> mất thứ phân biệt chúng.

#### ⑥ Gabor filters — *bộ lọc Gabor* · 48 chiều

**Là gì:** một bộ lọc dò **sóng hình sin** có hướng và độ rộng định sẵn. Dùng nó giống như
hỏi ảnh một loạt câu: *"có bao nhiêu sọc rộng 5 điểm ảnh nghiêng 30°?"* Mô phỏng khá sát
cách tế bào thị giác người phản ứng với hoa văn.

**Trích thế nào:** lọc ảnh bằng 4 tần số × 6 hướng = 24 bộ lọc, mỗi kết quả lấy 2 thống kê
(trung bình, độ lệch chuẩn). 24 × 2 = 48 số.

### Nhóm hình dáng — 98 chiều

Chỉ dùng **đường viền** (*contour*) con cá lấy từ mask, **bỏ qua hoàn toàn màu sắc**.

#### ⑦ Geometric ratios — *tỉ số hình học* · 7 chiều

**Là gì:** 7 tỉ lệ mô tả cá béo hay gầy, tròn hay dẹt. Ví dụ dài/cao, diện tích/chu vi²,
*solidity* (độ đặc — diện tích cá chia diện tích bao lồi), *eccentricity* (độ lệch tâm).

**Trích thế nào:** đo trực tiếp trên mask. Đây là nhóm **dễ giải thích nhất** cho người đọc.

#### ⑧ Hu moments — *mô men bất biến Hu* · 7 chiều

**Là gì:** 7 con số tổ hợp từ mô men ảnh, có tính chất đặc biệt là **không đổi khi ảnh bị
dịch, xoay, hoặc phóng to thu nhỏ**. Do Ming-Kuei Hu đề xuất năm 1962.

**Trích thế nào:** tính mô men trung tâm của mask rồi ghép theo 7 công thức của Hu. Giá trị
chúng chênh nhau hàng triệu lần nên phải nén bằng `-sign(h)·log₁₀|h|` trước khi dùng.

#### ⑨ Fourier descriptors — *mô tả tử Fourier* · 20 chiều

**Là gì:** mô tả đường viền bằng cách phân tích nó thành **tổng của các dao động tròn**.
Hệ số **thấp** cho dáng tổng thể, hệ số **cao** cho chi tiết răng cưa — nên lấy 20 hệ số
đầu là bỏ nhiễu mà giữ dáng.

**Trích thế nào:** lấy mẫu lại đường viền thành 256 điểm đều, coi mỗi điểm (x, y) là một
**số phức** x + iy, rồi biến đổi Fourier. Ba phép chuẩn hóa làm nó bất biến: bỏ F(0) →
bất biến vị trí; chia cho |F(1)| → bất biến kích thước; lấy modulus → bất biến xoay.

#### ⑩ Contour signature — *chữ ký đường viền* · 64 chiều

**Là gì:** biến hình dạng con cá thành một **đường cong một chiều** bằng cách đo khoảng
cách từ tâm ra viền. Cá đuôi dài cho đỉnh nhọn, cá tròn cho đường gần phẳng.

**Trích thế nào:** từ tâm mask, quét đều 64 góc quanh một vòng, mỗi góc ghi khoảng cách ra
tới viền.

---

## Bộ B — 512 chiều, ResNet18

**ResNet** = *Residual Network*, mạng phần dư — một kiến trúc **mạng nơ-ron tích chập**
(*CNN, Convolutional Neural Network*) do Microsoft Research công bố năm 2015. Số **18** là
số lớp. Chữ "phần dư" chỉ các **đường tắt** nối thẳng qua vài lớp, giúp huấn luyện được
mạng sâu mà không bị mất tín hiệu.

Bản dùng ở đây **đã huấn luyện sẵn trên ImageNet** — bộ dữ liệu 1,2 triệu ảnh thuộc 1000
loại vật thể. Nhóm **không huấn luyện lại**, chỉ dùng làm bộ trích đặc trưng đông cứng
(*frozen feature extractor*).

```
ảnh 384×384 → thu nhỏ 224×224 → chuẩn hóa theo ImageNet
            → ResNet18 (đã bỏ lớp phân loại cuối)
            → 512 số sau global average pooling
            → chuẩn hóa L2 → so bằng cosine
```

**Vì sao bỏ lớp cuối:** lớp cuối trả lời "đây là con chó hay cái ô tô" — vô dụng với cá.
Nhưng các lớp **trước** nó đã học được cạnh, góc, hoa văn, bố cục — những thứ dùng chung
cho mọi loại ảnh. 512 số ngay trước lớp cuối chính là phần hữu ích đó.

**Vì sao không huấn luyện lại:** 1.085 ảnh chia 20 loài là quá ít, mạng sẽ học thuộc lòng.
Và nếu huấn luyện thì mỗi fold phải huấn luyện lại một mô hình riêng để khỏi rò nhãn —
đắt gấp 5 lần mà kết quả kém tin cậy hơn.

**Vì sao chuẩn hóa L2 rồi so cosine:** **độ dài** vector ResNet phản ánh ảnh tương phản
mạnh hay yếu, không phản ánh loài. Chỉ **hướng** mới mang thông tin loài.

**Mạnh:** không cần người thiết kế công thức, bắt được cả đặc điểm khó diễn đạt — đạt P@5
72,2% so với 32,2% của ①. **Yếu:** không giải thích được vì sao hai ảnh được coi là giống
nhau.

---

## Bộ C — 35 chiều, do người mô tả

Còn gọi là **đặc trưng ngữ nghĩa** (*semantic features*) hay **thuộc tính cấp cao**
(*high-level attributes*): thứ con người diễn đạt được bằng lời, khác với các con số máy
tính ra ở Bộ A và B.

Bảng **20 loài × 10 thuộc tính**, mỗi ô chọn từ một **từ vựng có kiểm soát** (*controlled
vocabulary* — danh sách giá trị hợp lệ định trước, không cho nhập tự do), tra từ FishBase:
dáng thân, tỉ lệ dài:cao, màu nền, sọc, chấm, tương phản lưng–bụng, dáng đuôi, vây lưng,
kích thước, môi trường.

**Mã hóa 10 thuộc tính → 35 số:**

- 6 thuộc tính **danh nghĩa** (*nominal* — chỉ khác nhau, không hơn kém: màu, sọc…)
  → **one-hot**: mỗi giá trị một ô, đúng thì ghi 1, còn lại 0
- 4 thuộc tính **có thứ tự** (*ordinal* — có hơn kém: kích thước, tỉ lệ…)
  → **một số** trong [0; 1]

Tách hai cách là có lý do: one-hot coi `rat_nho` và `rat_lon` cách nhau đúng bằng
`rat_nho` và `nho`, mà thực tế không phải vậy.

**Gán theo loài, không theo từng ảnh** → hệ quả quan trọng: **Bộ C không dùng để truy vấn
được**, vì ảnh mới không có nhãn loài để tra bảng. Nó dùng để **đo giá trị thông tin** và
**giải thích** kết quả.

---

## Bộ D — 1.013 chiều, hợp nhất A ⊕ B

**Hợp nhất** (*feature fusion*) là gộp nhiều nguồn đặc trưng thành một. Ở đây dùng kiểu
**late fusion** — không nối thẳng hai dãy số lại, mà tính khoảng cách riêng từng khối rồi
**cộng có trọng số**:

$$d_{\text{tổng}} = w_1 d_{\text{màu}} + w_2 d_{\text{kết cấu}} + w_3 d_{\text{hình dáng}} + w_4 d_{\text{sâu}}$$

Hai việc phải làm đúng:

1. **Chuẩn hóa từng khối riêng** (z-score), vì 256 chiều histogram và 7 chiều tỉ số hình
   học có biên độ khác nhau hàng trăm lần — không chuẩn hóa thì khối lớn nuốt khối nhỏ.
2. **Trọng số `w` dò bên trong từng fold, chỉ trên gallery** — dò trên toàn bộ dữ liệu là
   gian lận, vì đã nhìn trộm đáp án của tập truy vấn.

---

## Bốn quy tắc áp dụng cho mọi bộ

| Quy tắc | Vì sao |
|---|---|
| **Chỉ tính trong vùng mask** | Nền xám lọt vào sẽ kéo mọi ảnh về cùng một màu, xóa sạch khác biệt |
| **Kết cấu phải co mask vào ~5 px** | Cửa sổ LBP/GLCM sát biên hút nền vào, sinh hoa văn giả |
| **z-score lấy mean/std từ gallery** | Lấy từ toàn bộ dữ liệu là rò thông tin tập truy vấn |
| **Độ đo chọn theo loại đặc trưng** | Histogram → Chi-square · Mô men và đặc trưng sâu → cosine · Tỉ số hình học → L2 |

## Luồng chạy đầy đủ

```
            ảnh PNG 384×384 RGBA (kênh alpha = mask)
                           │
        ┌──────────────────┼──────────────────┬──────────────┐
        ▼                  ▼                  ▼              ▼
    Bộ A 501          Bộ B 512           Bộ C 35      (tra bảng loài)
  công thức toán      ResNet18         bảng người gán
        │                  │                  │
        │                  │                  └─► phân tích + giải thích
        └────────┬─────────┘                      (KHÔNG truy vấn)
                 ▼
           Bộ D hợp nhất ──► khoảng cách ──► top-5
```

---

## Thuật ngữ

### Không gian màu

| Tên | Viết tắt của | Là gì |
|---|---|---|
| **RGB** | Red, Green, Blue | Cách máy lưu ảnh: 3 kênh đỏ, lục, lam |
| **Lab** | CIELAB (L\*a\*b\*) | L = độ sáng, a = xanh↔đỏ, b = lam↔vàng. **Tách độ sáng khỏi màu**, nên so màu công bằng dù ảnh chụp sáng tối khác nhau |
| **HSV** | Hue, Saturation, Value | H = sắc màu (vòng 0–360°), S = độ đậm, V = độ sáng. Gần với cách người mô tả màu |

### Xử lý ảnh

| Tên | Là gì |
|---|---|
| **mask** | Ảnh đen trắng đánh dấu điểm nào là cá, điểm nào là nền. Lưu trong **kênh alpha** của PNG |
| **kênh alpha** | Kênh thứ 4 của ảnh RGBA, vốn dùng cho độ trong suốt; ở đây mượn để lưu mask |
| **rembg / u2net** | Thư viện và mô hình dùng để **tách nền**, sinh ra mask |
| **phép affine** | Phép biến đổi gộp xoay + phóng to/thu nhỏ + dịch chuyển + lật thành **một bước duy nhất** |
| **contour** | Đường viền ngoài của vật thể |

### Học máy

| Tên | Viết tắt của | Là gì |
|---|---|---|
| **CNN** | Convolutional Neural Network | Mạng nơ-ron tích chập — kiến trúc chuyên xử lý ảnh |
| **ResNet** | Residual Network | Một kiến trúc CNN; số 18 là số lớp |
| **ImageNet** | — | Bộ dữ liệu 1,2 triệu ảnh / 1000 loại vật thể, chuẩn để huấn luyện sẵn |
| **GAP** | Global Average Pooling | Lấy trung bình toàn bản đồ đặc trưng → biến ảnh thành một dãy số cố định |
| **k-means** | — | Thuật toán gom dữ liệu thành k cụm, mỗi cụm có một tâm |
| **PCA** | Principal Component Analysis | Giảm số chiều bằng cách giữ lại các hướng biến thiên mạnh nhất |

### Chuẩn hóa và khoảng cách

| Tên | Là gì |
|---|---|
| **z-score** | Trừ trung bình rồi chia độ lệch chuẩn → mọi chiều về cùng thang đo |
| **chuẩn hóa L2** | Chia vector cho độ dài của nó → mọi vector dài đúng bằng 1, chỉ còn khác hướng |
| **khoảng cách L2** | Khoảng cách Euclid — đường chim bay giữa hai điểm |
| **cosine** | Đo **góc** giữa hai vector, bỏ qua độ dài |
| **Chi-square** | Độ đo chuyên dùng để so hai histogram |
| **one-hot** | Mã hóa giá trị phân loại: mỗi giá trị một ô, đúng ghi 1, còn lại 0 |

### Đánh giá

| Tên | Là gì |
|---|---|
| **gallery** | Kho ảnh để tìm trong đó |
| **query** | Ảnh truy vấn, ảnh người dùng đưa vào |
| **fold** | Một phần trong phép chia 5 phần; mỗi lượt một phần làm query, 4 phần làm gallery |
| **P@k** | Trong k ảnh trả về, bao nhiêu phần đúng loài |
| **mAP** | *mean Average Precision* — điểm tổng hợp, thưởng cho việc đẩy ảnh đúng lên hạng cao |
| **HNSW** | *Hierarchical Navigable Small World* — cấu trúc chỉ mục giúp tìm k láng giềng gần nhanh hơn quét tuần tự |

---

## Hiện trạng

| Bộ | Đã cài | P@5 đo được |
|---|---|---|
| A ① color moments | ✓ | **32,2%** |
| A ②–⑩ | thiết kế xong | — |
| B ResNet18 | ✓ | **72,2%** |
| C ngữ nghĩa | ✓ | không áp dụng |
| D hợp nhất | chưa | — |

Mức ngẫu nhiên là 5,0%.
