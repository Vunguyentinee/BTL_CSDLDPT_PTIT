# Bộ C — thuộc tính ngữ nghĩa và giá trị thông tin

> Nguồn số: `python scripts/bo_c.py --kiem-tra` · Bảng: `data_meta/thuoc_tinh_ngu_nghia.csv`
> Đo ngày 20/10/2026 trên 20 loài đã chốt.

Tài liệu này phục vụ **mục 1** của đề ("mô tả điểm giống và khác nhau") và **mục 2**
("trình bày giá trị thông tin của đặc trưng").

## 1. Vì sao cần một bộ đặc trưng do người mô tả

Bộ A (501 chiều cổ điển) và Bộ B (512 chiều ResNet18) đều suy ra từ điểm ảnh. Chúng
cho số đo nhưng không cho lời giải thích, và không trả lời được câu hỏi của mục 1 là
*hai loài này giống nhau và khác nhau ở chỗ nào*.

Bộ C là bảng 20 loài × 10 thuộc tính, mỗi giá trị lấy từ một **từ vựng có kiểm soát**,
tra từ trang loài FishBase chứ không nhìn từng ảnh. Vì thế nó đo được giá trị thông tin
mà **không cần chạy mô hình nào** — chỉ cần entropy và phép đếm cặp.

### Gán theo loài, không theo ảnh — và hệ quả

10 thuộc tính này là tính trạng của **loài**, không phải của một tấm ảnh. Hệ quả phải
nói rõ khi báo cáo:

> Bộ C **không dùng được để truy vấn**. Ảnh đầu vào mới không có nhãn loài nên không tra
> được bảng. Nó dùng để phân tích giá trị thông tin và để giải thích kết quả tìm kiếm,
> không phải để tính khoảng cách với ảnh truy vấn.

Đây là lý do Bộ C không nằm trong Bộ D (fusion A⊕B).

## 2. Mười thuộc tính và từ vựng

| # | Thuộc tính | Loại | Từ vựng |
|---|---|---|---|
| 1 | `dang_than` | nominal | thoi · det_cao · det_tron · det_dai · tru_dai |
| 2 | `ti_le_dai_cao` | **ordinal** | rat_cao <1,5 · cao 1,5–2,5 · trung_binh 2,5–3,5 · dai 3,5–5 · rat_dai >5 |
| 3 | `mau_nen` | nominal | bac · vang · cam · do · nau · xanh_luc · xanh_lam · den · da_mau |
| 4 | `soc` | nominal | khong · vach_dung · dai_ngang · van_luoi |
| 5 | `cham` | nominal | khong · thua · day · dom_mat |
| 6 | `tuong_phan_lung_bung` | **ordinal** | yeu · vua · manh |
| 7 | `dang_duoi` | nominal | chia_sau · chia_nhe · cat_bang · tron · xoe_dai |
| 8 | `vay_lung` | nominal | ngan · dai_lien · gai_cung · co_vay_mo |
| 9 | `kich_thuoc` | **ordinal** | rat_nho <10cm · nho 10–30 · trung_binh 30–60 · lon 60–120 · rat_lon >120 |
| 10 | `moi_truong` | **ordinal** | nuoc_ngot · nuoc_lo · nuoc_man |

**Mã hóa → 35 chiều.** Bốn thuộc tính có thứ tự thành **một số** chuẩn hóa về [0,1];
sáu thuộc tính danh nghĩa thành **one-hot**. Lý do tách hai cách: one-hot coi `rat_nho`
và `rat_lon` cách nhau đúng bằng `rat_nho` và `nho`, mà thực tế không phải vậy.

## 3. Giá trị thông tin từng thuộc tính

20 loài → **190 cặp loài**. Entropy tối đa về lý thuyết là log₂20 = **4,32 bit**.

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

**Đọc bảng này thế nào:**

- **Mạnh nhất là `mau_nen`** — một mình nó tách được 85% cặp loài. Hợp lý: bộ dữ liệu
  có nhiều loài cảnh màu rực (cá hề cam, cá hề cà chua đỏ, đuôi gai vàng, đuôi gai xanh).
- **Yếu nhất là `cham`** — chỉ 1,02 bit và 36% cặp, vì 14/20 loài không có chấm. Một
  thuộc tính mà đa số loài cùng một giá trị thì mang ít thông tin, **dù nó rất hữu ích
  cho đúng cái cặp nó phân biệt được** (`dom_mat` chỉ AST_OCE có, `day` chỉ ONC_MYK và
  POE_RET có). Đây là điểm đáng nói trong báo cáo: entropy thấp ≠ vô dụng.
- **Không thuộc tính nào đạt tới 4,32 bit**, nên không có thuộc tính nào một mình phân
  loại được 20 loài. Phải phối hợp — và đó là lập luận cho việc ghép nhiều khối đặc trưng.

## 4. Mười hai cặp loài cùng họ — chỗ khó nhất

Cặp cùng họ là cặp dễ nhầm nhất. Bảng dưới đếm **số thuộc tính khác nhau** trong 10 cột:

| Họ | Loài A | Loài B | Số TT khác | Khác ở đâu |
|---|---|---|---|---|
| POMA | AMP_FRE | AMP_OCE | **1** ⚠ | `mau_nen` |
| SCOM | KAT_PEL | SCO_COM | 3 | `ti_le_dai_cao`, `soc`, `kich_thuoc` |
| ACAN | PAR_HEP | ZEB_FLA | 4 | `dang_than`, `ti_le_dai_cao`, `mau_nen`, `soc` |
| CICH | ORE_MOS | ORE_NIL | 4 | `mau_nen`, `soc`, `tuong_phan_lung_bung`, `moi_truong` |
| OSPH | BET_SPL | OSP_GOR | 4 | `dang_than`, `mau_nen`, `dang_duoi`, `kich_thuoc` |
| CICH | AST_OCE | ORE_MOS | 5 | `mau_nen`, `cham`, `dang_duoi`, `vay_lung`, `moi_truong` |
| CICH | AST_OCE | SYM_SPP | 5 | `dang_than`, `ti_le_dai_cao`, `soc`, `cham`, `kich_thuoc` |
| SALM | ONC_MYK | SAL_SAL | 5 | `soc`, `cham`, `dang_duoi`, `kich_thuoc`, `moi_truong` |
| CICH | AST_OCE | ORE_NIL | 6 | 6 thuộc tính |
| CYPR | CAR_AUR | CYP_CAR | 7 | 7 thuộc tính |
| CICH | ORE_NIL | SYM_SPP | 7 | 7 thuộc tính |
| CICH | ORE_MOS | SYM_SPP | 8 | 8 thuộc tính |

### Phát hiện quan trọng: cặp cá hề

**AMP_OCE (cá hề) và AMP_FRE (cá hề cà chua) chỉ khác nhau ở đúng 1 trong 10 thuộc tính.**

Thực tế hai loài này còn khác ở **số khoang trắng** — cá hề có 3, cá hề cà chua có 1 — và
đó chính là dấu hiệu nhận dạng ngoài thực địa. Nhưng từ vựng của `soc` chỉ có `vach_dung`
mà không mã hóa được **số lượng** vạch, nên cả hai cùng nhận một giá trị.

Đây không phải lỗi cần sửa gấp, mà là **kết luận có giá trị cho báo cáo**: bộ thuộc tính
ngữ nghĩa do người mô tả thì dễ hiểu nhưng **dung lượng thông tin thấp**, và có những
phân biệt thị giác nó không biểu diễn được. Chính khoảng trống này là lý do tồn tại của
Bộ A (histogram theo dải dọc thân đếm được vùng sáng/tối) và Bộ B (ResNet18 học trực tiếp
từ điểm ảnh). Ba bộ bù nhau, không thay nhau.

## 5. Hạn chế đã biết

| Hạn chế | Ảnh hưởng |
|---|---|
| `soc` không mã hóa **số lượng** vạch | Cặp AMP_OCE/AMP_FRE chỉ còn 1 thuộc tính phân biệt |
| Không có thuộc tính **râu** (barbel) | CYP_CAR có 2 đôi râu, CAR_AUR không — mất một dấu hiệu chắc chắn |
| `vay_lung=co_vay_mo` trùng giữa SALM và PANG | PAN_HYP mang cùng giá trị với SAL_SAL và ONC_MYK dù khác họ; giữ cố ý để thấy giới hạn |
| SYM_SPP là **nhãn cấp chi**, không phải cấp loài | Thuộc tính của `Symphysodon spp` là trung bình của nhiều dạng lai |
| BET_SPL, POE_RET, CAR_AUR **biến dị màu/đuôi rất lớn** | Giá trị `da_mau` và `xoe_dai` chỉ đúng với phần lớn ảnh, không phải mọi ảnh |
| `ti_le_dai_cao` của BET_SPL tính **theo mask** (gộp vây) | Không so sánh trực tiếp được với số đo thân cá trong tài liệu sinh học |
| AST_OCE có nhiều dòng màu nhân tạo | Chỉ ~1/3 ảnh là dạng hoang dã nâu sẫm, còn lại bạch tạng và đỏ-cam → `mau_nen=da_mau`; đốm mắt gần như mất ở dòng bạch tạng |

## 6. Một lỗi nhãn đã phát hiện và sửa (20/10)

Dòng `AST_OCE` ban đầu ghi `ten_viet = "Cá hồng két"` cạnh `ten_khoa_hoc = Astronotus ocellatus`.
Đó là **hai con cá khác nhau**:

- *Astronotus ocellatus* — cá Oscar, ở Việt Nam gọi **cá hoàng bảo yến** (hoặc cá heo lửa). Dài tới
  45cm, thân bầu dục thon, vây lưng dài liền, đốm đen viền cam ở gốc đuôi.
- **Cá hồng két** — cá lai *blood parrot*, thân tròn như quả bóng, trán dốc, miệng hình mỏ không khép
  kín. Là con lai nhân tạo nên **không có tên khoa học hợp lệ**.

Cách phân xử: dựng **contact sheet 24/96 ảnh** của `work/chuan/AST_OCE/` và xem tận mắt. Kết quả là
ảnh đúng *Astronotus ocellatus*, nên **tên khoa học đúng, tên tiếng Việt sai**. Đã sửa `ten_viet`
thành *Cá hoàng bảo yến*; `ma_loai`, `ten_khoa_hoc`, `ma_ho` giữ nguyên.

Cùng lúc phát hiện `mau_nen` ghi `nau` theo mô tả sách giáo khoa là không khớp ảnh thật trong CSDL —
đã đổi sang `da_mau`.

> **Bài học ghi vào phần quy trình của báo cáo:** đây là lần thứ hai trong dự án mà việc mở ảnh ra xem
> sửa được một kết luận rút ra từ tên thư mục (lần đầu là sự cố crawl Bing trả về ảnh rác). Dự đoán ban
> đầu còn sai cả chiều — ngờ ảnh sai, hóa ra nhãn sai.

---

Các hạn chế ở mục 5 là việc **cần xử lý trước khi báo cáo tổng** — xem `tasks/todo.md`.
