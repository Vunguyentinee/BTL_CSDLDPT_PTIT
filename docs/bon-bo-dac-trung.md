# Bốn bộ đặc trưng — công nghệ và cách trích rút

> Bản giải thích ngắn. Chi tiết Bộ C xem `docs/bo-c-ngu-nghia.md`;
> số liệu thực nghiệm xem `docs/bao-cao/tien-do-1.md`.

## Tổng quan

"Trích rút đặc trưng" là biến **một tấm ảnh** thành **một dãy số** để máy so sánh được.
Hai ảnh giống nhau phải cho hai dãy số gần nhau.

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

Chia theo **ba kênh thị giác độc lập**: màu, kết cấu, hình dáng. Cá có thể giống nhau ở
một kênh mà khác hẳn ở kênh kia — cá thu và cá ngừ cùng màu bạc (màu giống) nhưng hoa văn
khác phương (kết cấu khác).

### Nhóm màu — 285 chiều

| | Đặc trưng | Đo cái gì | Cách làm | Chiều |
|---|---|---|---|---|
| ① | **Color moments Lab** | Màu trung bình và độ dao động của nó | Đổi sang hệ màu Lab, tính 3 con số thống kê cho mỗi kênh | 9 |
| ② | **Histogram HSV 4 dải** | Màu **ở đâu** trên thân cá | Chia cá thành 4 khúc từ đầu đến đuôi, mỗi khúc đếm phân bố màu | 256 |
| ③ | **Màu trội k-means** | 5 màu chủ đạo và tỉ lệ mỗi màu | Gom mọi điểm ảnh thành 5 cụm màu, lấy tâm cụm | 20 |

**Hệ màu Lab** tách độ sáng (L) khỏi màu (a: xanh↔đỏ, b: lam↔vàng). Quan trọng vì ảnh cá
chụp ở điều kiện sáng rất khác nhau — tách được độ sáng ra thì so màu mới công bằng.

**Ba con số thống kê** của ①: trung bình (màu nào), độ lệch chuẩn (màu có đều không), độ
xiên (lệch về phía sáng hay tối).

**Vì sao cần ② khi đã có ①:** ① trộn cả con cá thành một màu trung bình, nên cá "đầu đỏ
đuôi vàng" và cá "đầu vàng đuôi đỏ" cho kết quả **y hệt nhau**. ② chia thân thành 4 dải
nên giữ được thông tin vị trí.

**Lưu ý kỹ thuật ③:** k-means trả về 5 cụm theo thứ tự ngẫu nhiên mỗi lần chạy, nên
**bắt buộc sắp xếp lại theo tỉ lệ giảm dần**, nếu không hai ảnh giống hệt nhau sẽ cho hai
vector khác nhau.

### Nhóm kết cấu — 118 chiều

Kết cấu là **hoa văn bề mặt**: vảy, sọc, chấm, độ gồ ghề.

| | Đặc trưng | Đo cái gì | Cách làm | Chiều |
|---|---|---|---|---|
| ④ | **LBP** | Bề mặt gồ ghề hay nhẵn | So mỗi điểm với các điểm xung quanh, sáng hơn ghi 1 tối hơn ghi 0 → được một số nhị phân → đếm tần suất | 54 |
| ⑤ | **GLCM** | Hoa văn thô hay mịn, **theo hướng nào** | Đếm số cặp điểm ảnh kề nhau có độ sáng (i, j) → ma trận đồng hiện | 16 |
| ⑥ | **Gabor** | Có sọc rộng bao nhiêu, nghiêng bao nhiêu độ | Lọc ảnh bằng sóng hình sin có hướng và tần số định sẵn | 48 |

**LBP dùng 3 bán kính** (R1, R2, R3) vì vảy cá nhỏ và sọc cá lớn nằm ở hai thang khác
nhau — một bán kính chỉ bắt được một thang. Biến thể dùng là *uniform, bất biến xoay*:
10 + 18 + 26 = 54 chiều.

**GLCM giữ nguyên 4 hướng** (0°, 45°, 90°, 135°) thay vì lấy trung bình. Lý do nằm ở chính
bộ dữ liệu: **cá thu có vạch đứng, cá ngừ vằn có dải ngang**. Lấy trung bình 4 hướng thì
hai loài này thành giống hệt nhau. 4 thuộc tính × 4 hướng = 16.

**Gabor** giống như hỏi ảnh một loạt câu: *"có bao nhiêu sọc rộng 5 điểm ảnh nghiêng 30°?"*
4 tần số × 6 hướng × 2 thống kê = 48.

### Nhóm hình dáng — 98 chiều

Chỉ dùng **đường viền** con cá (lấy từ mask), bỏ qua hoàn toàn màu sắc.

| | Đặc trưng | Đo cái gì | Cách làm | Chiều |
|---|---|---|---|---|
| ⑦ | **7 tỉ số hình học** | Béo/gầy, tròn/dẹt | Dài/cao, diện tích/chu vi², độ đặc, độ lệch tâm… | 7 |
| ⑧ | **Hu moments** | Dáng tổng thể, **bất biến xoay** | 7 tổ hợp đại số của mô men ảnh | 7 |
| ⑨ | **Fourier descriptors** | Dáng viền từ thô đến chi tiết | Coi đường viền là chuỗi số phức → biến đổi Fourier | 20 |
| ⑩ | **Contour signature** | Hình dạng viền dưới dạng đường cong | Đo khoảng cách từ tâm ra viền tại 64 điểm đều nhau | 64 |

**Hu moments** cho cùng kết quả dù ảnh bị xoay, dịch hay phóng to — hữu ích khi hướng cá
chưa chuẩn. Giá trị chúng chênh nhau hàng triệu lần nên phải nén bằng
`-sign(h)·log₁₀|h|` trước khi dùng.

**Fourier descriptors** hay ở chỗ hệ số thấp mô tả **dáng tổng thể**, hệ số cao mô tả
**chi tiết răng cưa**. Lấy 20 hệ số đầu là bỏ nhiễu mà giữ dáng. Ba phép chuẩn hóa làm nó
bất biến: bỏ F(0) → bất biến vị trí; chia cho |F(1)| → bất biến kích thước; lấy modulus →
bất biến xoay.

**Contour signature** vẽ ra thành một đường cong: cá đuôi dài cho đỉnh nhọn, cá tròn cho
đường gần phẳng.

---

## Bộ B — 512 chiều, ResNet18

Dùng mạng nơ-ron **đã huấn luyện sẵn trên ImageNet** (1,2 triệu ảnh, 1000 loại vật thể).
Không huấn luyện lại, chỉ dùng làm bộ trích đặc trưng.

```
ảnh 384×384 → thu nhỏ 224×224 → chuẩn hóa theo ImageNet
            → ResNet18 (đã bỏ lớp phân loại cuối)
            → 512 số sau global average pooling
            → chuẩn hóa L2 → so bằng cosine
```

**Vì sao bỏ lớp cuối:** lớp cuối của ResNet trả lời "đây là con chó hay cái ô tô" — vô
dụng với cá. Nhưng các lớp **trước** nó đã học được cạnh, góc, hoa văn, bố cục — những thứ
dùng chung cho mọi loại ảnh. 512 số ngay trước lớp cuối chính là phần hữu ích đó.

**Vì sao không huấn luyện lại:** 1.085 ảnh chia 20 loài là quá ít, mạng sẽ học thuộc lòng.
Và nếu huấn luyện thì mỗi fold phải huấn luyện lại một mô hình riêng để khỏi rò nhãn —
đắt gấp 5 lần mà kết quả kém tin cậy hơn.

**Vì sao chuẩn hóa L2 rồi so cosine:** **độ dài** vector ResNet phản ánh ảnh tương phản
mạnh hay yếu, không phản ánh loài. Chỉ **hướng** mới mang thông tin loài. Chuẩn hóa L2 là
vứt độ dài đi, chỉ giữ hướng.

**Điểm mạnh:** không cần người thiết kế công thức, bắt được cả những đặc điểm khó diễn
đạt. Thực tế đạt P@5 72,2% so với 32,2% của ① — gấp 2,24 lần.
**Điểm yếu:** không giải thích được vì sao hai ảnh được coi là giống nhau.

---

## Bộ C — 35 chiều, do người mô tả

Bảng **20 loài × 10 thuộc tính**, mỗi ô chọn từ một từ vựng cố định, tra từ FishBase:
dáng thân, tỉ lệ dài:cao, màu nền, sọc, chấm, tương phản lưng–bụng, dáng đuôi, vây lưng,
kích thước, môi trường.

**Mã hóa 10 thuộc tính → 35 số:**

- 6 thuộc tính **danh nghĩa** (màu, sọc…) → **one-hot**: mỗi giá trị một ô, đúng thì 1
- 4 thuộc tính **có thứ tự** (kích thước, tỉ lệ…) → **một số** trong [0; 1]

Tách hai cách là có lý do: one-hot coi `rat_nho` và `rat_lon` cách nhau đúng bằng
`rat_nho` và `nho`, mà thực tế không phải vậy.

**Gán theo loài, không theo từng ảnh** → hệ quả quan trọng: **Bộ C không dùng để truy vấn
được**, vì ảnh mới không có nhãn loài để tra bảng. Nó dùng để **đo giá trị thông tin** và
**giải thích** kết quả.

---

## Bộ D — 1.013 chiều, hợp nhất A ⊕ B

Ghép Bộ A và Bộ B. Không phải nối thẳng hai dãy số, mà **cộng khoảng cách có trọng số**:

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
| **Độ đo chọn theo loại đặc trưng** | Histogram → Chi-square · Moments và đặc trưng sâu → cosine · Tỉ số hình học → L2 |

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

## Hiện trạng

| Bộ | Đã cài | P@5 đo được |
|---|---|---|
| A ① color moments | ✓ | **32,2%** |
| A ②–⑩ | thiết kế xong | — |
| B ResNet18 | ✓ | **72,2%** |
| C ngữ nghĩa | ✓ | không áp dụng |
| D hợp nhất | chưa | — |

Mức ngẫu nhiên là 5,0%.
