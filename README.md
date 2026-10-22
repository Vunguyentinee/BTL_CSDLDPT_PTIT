# Hệ cơ sở dữ liệu lưu trữ và tìm kiếm ảnh cá

Bài tập lớn môn **Cơ sở dữ liệu đa phương tiện** (INT1418), Học viện Công nghệ
Bưu chính Viễn thông — Khoa Công nghệ Thông tin 1. Nhóm 18, lớp
INT1418-20261-03. Giảng viên hướng dẫn: TS. Nguyễn Đình Hóa.

Hệ thống nhận một ảnh cá bất kỳ và trả về những ảnh giống nhất trong cơ sở dữ
liệu, dựa trên **nội dung ảnh** chứ không dựa trên tên file hay thẻ mô tả —
tức một hệ **CBIR** (Content-Based Image Retrieval).

Thành viên: Nguyễn Tiến Vũ · Trần Trung Kiên · Vũ Đặng Thọ.

> **Ảnh không kèm trong repo.** Bộ ảnh đã chuẩn hóa nặng khoảng 1,1 GB nên
> thư mục `work/` bị loại khỏi git. Repo này chứa mã nguồn, siêu dữ liệu,
> kết quả đo và tài liệu. Xem [Dựng lại bộ dữ liệu](#dựng-lại-bộ-dữ-liệu).

## Kết quả hiện tại

Đo trên **1.085 truy vấn** bằng 5-fold phân tầng, trung bình macro theo loài.
Mỗi ảnh lần lượt làm truy vấn đúng một lần; không ảnh nào vừa ở gallery vừa ở
tập truy vấn trong cùng một fold.

| Chỉ số | Bộ A① — 9 chiều | Bộ B — 512 chiều | Ngẫu nhiên |
|---|---|---|---|
| Precision@1 | 37,1% ± 2,8% | 80,9% ± 2,1% | |
| **Precision@5** | **32,2% ± 1,2%** | **72,2% ± 1,1%** | **5,0%** |
| Precision@10 | 28,6% ± 1,2% | 66,3% ± 1,2% | |
| Recall@10 | 8,1% ± 0,4% | 20,8% ± 0,5% | |
| mAP | 18,7% ± 0,9% | 52,1% ± 0,8% | |

Mốc ngẫu nhiên 5,0% được tính từ tỉ lệ thật của từng lớp trong gallery của
từng fold, không lấy 1/20, vì bộ dữ liệu mất cân bằng 8,5 lần.

Thời gian trích đặc trưng trên CPU: 29 ms/ảnh (Bộ A①) và 37 ms/ảnh (Bộ B).

## Bộ dữ liệu

4.768 ảnh thô từ iNaturalist, Archive và FishBase; sau chuẩn hóa tự động và
duyệt tay từng tấm còn **1.085 ảnh / 20 loài / 11 họ**.

Mỗi ảnh là PNG **384×384 RGBA**: nền đã tách bằng rembg (u2net) và lưu ở kênh
alpha làm mask, cá dài 348 px, nằm giữa khung, đầu bên trái, lưng lên trên.
Mọi đặc trưng chỉ tính trong vùng mask.

Số ảnh mỗi loài: trung vị 37, nhiều nhất 162 (cá dĩa), ít nhất 19 (cá lóc).
Hai mươi loài được chọn để vừa có cặp dễ nhầm vừa có cặp khác xa, trong đó
cặp khó nhất là hai loài cùng chi *Oreochromis*.

## Bốn bộ đặc trưng

| Bộ | Nội dung | Chiều | Trạng thái |
|---|---|---|---|
| **A** | 10 đặc trưng cổ điển do người viết công thức: màu, kết cấu, hình dáng | 501 | ① đã cài và đo · ②–⑩ đã thiết kế |
| **B** | ResNet18 đông cứng, vector sau global average pooling, chuẩn hóa L2, so bằng cosine | 512 | đã cài và đo |
| **C** | 20 loài × 10 thuộc tính ngữ nghĩa lấy từ từ vựng có kiểm soát | 35 | đã cài, đã đo entropy |
| **D** | Hợp nhất có trọng số các khối trên | — | chưa làm |

Ba họ đặc trưng của Bộ A theo khung MPEG-7 Visual:

- **màu** — ① color moments Lab · ② histogram HSV theo 4 dải dọc thân ·
  ③ màu trội k-means
- **kết cấu** — ④ LBP 3 bán kính · ⑤ GLCM 4 hướng · ⑥ bộ lọc Gabor
- **hình dáng** — ⑦ tỉ số hình học · ⑧ mô men Hu · ⑨ mô tả tử Fourier ·
  ⑩ chữ ký đường viền

Giải thích từng đặc trưng: [`docs/bon-bo-dac-trung.md`](docs/bon-bo-dac-trung.md).

## Chạy

```bash
python -m pip install -r requirements.txt
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

python scripts/kiem_tra.py              # 8 bộ self-test
python scripts/kiem_tra.py --day-du     # thêm 3 bộ đối chiếu dữ liệu thật

python scripts/danh_gia.py              # bảng P@k, R@10, mAP cho Bộ A① và Bộ B
python scripts/gia_tri_thong_tin.py     # bảng Fisher và η² cho các khối
python scripts/bo_c.py --kiem-tra       # soát bảng thuộc tính ngữ nghĩa
```

Hai lệnh `danh_gia.py` và `gia_tri_thong_tin.py` sinh lại toàn bộ số liệu
trong `ket_qua/`. Chúng cần bộ ảnh trong `work/chuan/`.

Dự án không dùng pytest; mỗi module tự mang hàm `_selftest()` và
`scripts/kiem_tra.py` gọi hết.

## Cấu trúc

```
fishcbir/            thư viện
  cauhinh.py         đường dẫn và hằng số
  danhmuc.py         liệt kê và nạp ảnh, đọc mask từ kênh alpha
  chia_fold.py       chia 5-fold phân tầng, seed cố định
  dactrung/mau.py    Bộ A① color moments Lab, 9 chiều
  dactrung/sau.py    Bộ B ResNet18, 512 chiều
  timkiem.py         khoảng cách, xếp hạng, P@k, mAP
  danhgia.py         vòng 5-fold dùng chung
  fisher.py          Fisher score và η² — đo giá trị thông tin

scripts/             công cụ dòng lệnh
  tai_anh.py         tải ảnh thô từ ba nguồn
  chuan_hoa.py       tách nền, xoay, căn giữa, xuất 384×384
  review_tool.py     duyệt tay từng ảnh theo bảng kiểm
  bo_c.py            Bộ C — mã hóa và soát bảng ngữ nghĩa
  danh_gia.py        chạy toàn tuyến, in bảng so sánh
  gia_tri_thong_tin.py   bảng Fisher ba cột
  kiem_tra.py        chạy mọi self-test

data_meta/           siêu dữ liệu (có trong repo)
  species.csv        20 loài: mã, tên Việt, tên khoa học, họ
  thuoc_tinh_ngu_nghia.csv   bảng Bộ C, 20 loài × 10 thuộc tính
  splits/folds.csv   phân fold cố định

ket_qua/             số liệu đo (.csv có trong repo, .npz thì không)
docs/                tài liệu thiết kế và báo cáo
tasks/               kế hoạch và danh sách việc
work/                ảnh — KHÔNG có trong repo
```

## Mô hình dữ liệu và kiến trúc

Mô hình **đối tượng - quan hệ kết hợp vector**: PostgreSQL 17 với phần mở rộng
pgvector, mỗi khối đặc trưng một cột vector, chỉ mục HNSW cho tìm k láng giềng
gần. Kiến trúc tập trung và đồng nhất.

Chi tiết và căn cứ theo khung bài giảng:
[`docs/kien-truc-va-mo-hinh-du-lieu.md`](docs/kien-truc-va-mo-hinh-du-lieu.md).

## Dựng lại bộ dữ liệu

```bash
python scripts/tai_anh.py        # tải ảnh thô về work/tho/
python scripts/chuan_hoa.py      # tách nền và chuẩn hóa về work/chuan/
python scripts/review_tool.py    # duyệt tay, ghi kết quả vào data_meta/review/
```

Kết quả duyệt tay đã có sẵn trong `data_meta/review/`, nên nếu tải lại đúng
nguồn thì không phải duyệt lại từ đầu.

## Trạng thái

- **Giai đoạn 1** — bộ dữ liệu và bộ thuộc tính nhận diện: đã xong, có số đo.
  Báo cáo: [`docs/bao-cao/tien-do-1.md`](docs/bao-cao/tien-do-1.md)
- **Giai đoạn 2** — hoàn thiện Bộ A ②–⑩, hợp nhất thành Bộ D, dựng
  PostgreSQL + pgvector, đo chỉ mục HNSW
- **Giai đoạn 3** — giao diện demo và bộ chỉ số đánh giá đầy đủ

Đây là bài tập của một môn học, không phải thư viện dùng cho sản xuất. Ảnh
thu từ iNaturalist, Archive và FishBase theo giấy phép của từng nguồn.
