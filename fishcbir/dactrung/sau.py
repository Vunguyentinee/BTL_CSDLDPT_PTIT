"""Bộ B — đặc trưng sâu từ ResNet18 huấn luyện sẵn trên ImageNet (512 chiều).

Không huấn luyện lại, chỉ dùng mạng làm bộ trích đặc trưng: bỏ lớp phân loại
cuối, lấy vector 512 chiều sau global average pooling, rồi chuẩn hóa L2.

Vì sao không tinh chỉnh (fine-tune): 1.085 ảnh chia 20 loài là quá ít để
huấn luyện mà không học thuộc lòng, và nếu tinh chỉnh thì mỗi fold phải huấn
luyện lại một mô hình riêng để không rò nhãn tập truy vấn vào gallery. Dùng
mạng đông cứng thì đặc trưng của một ảnh không phụ thuộc fold, nên phép đánh
giá 5-fold vẫn trung thực mà chi phí chỉ bằng một lần trích.

Vì sao L2-chuẩn-hóa rồi đo cosine: độ dài vector đặc trưng sâu phản ánh độ
"mạnh" của kích hoạt (ảnh tương phản cao cho vector dài hơn), không phản ánh
loài. Chuẩn hóa L2 bỏ phần đó đi, chỉ giữ lại hướng.

Nền xám (128,128,128) giữ nguyên chứ không tô đen: giá trị đó gần sát màu
trung bình của ImageNet (124,116,104) nên mạng coi như nền trống, trong khi
nền đen tạo biên giả rất mạnh mà mạng sẽ bám vào.
"""

from __future__ import annotations

import numpy as np

SO_CHIEU = 512
# ResNet18 huấn luyện ở 224x224; đưa đúng khổ đó thì đặc trưng mới khớp phân bố
# mà mạng đã học.
KHO_VAO = 224
# Trung bình và độ lệch chuẩn của ImageNet — bắt buộc phải khớp với lúc huấn luyện.
TB_IMAGENET = np.array([0.485, 0.456, 0.406], np.float32)
LECH_IMAGENET = np.array([0.229, 0.224, 0.225], np.float32)

_mo_hinh = None


def nap_mo_hinh():
    """Nạp ResNet18 đã bỏ lớp phân loại, đặt chế độ eval. Nạp một lần rồi giữ lại.

    Lần chạy đầu sẽ tải khoảng 45MB trọng số về thư mục cache của torch.
    """
    global _mo_hinh
    if _mo_hinh is not None:
        return _mo_hinh

    import torch
    from torchvision.models import ResNet18_Weights, resnet18

    m = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
    # Thay lớp phân loại 1000 lớp bằng ánh xạ đồng nhất → đầu ra là 512 chiều
    # ngay sau global average pooling.
    m.fc = torch.nn.Identity()
    m.eval()
    torch.set_grad_enabled(False)
    _mo_hinh = m
    return m


def tien_xu_ly(rgb: np.ndarray) -> np.ndarray:
    """RGB uint8 (H,W,3) → tensor float (3, 224, 224) đã chuẩn hóa theo ImageNet.

    Thu nhỏ bằng nội suy song tuyến tính qua PIL để khớp cách torchvision làm.
    """
    from PIL import Image

    if rgb.shape[:2] != (KHO_VAO, KHO_VAO):
        rgb = np.asarray(
            Image.fromarray(rgb, "RGB").resize((KHO_VAO, KHO_VAO), Image.BILINEAR)
        )
    x = rgb.astype(np.float32) / 255.0
    x = (x - TB_IMAGENET) / LECH_IMAGENET
    return np.ascontiguousarray(x.transpose(2, 0, 1))


def chuan_hoa_l2(X: np.ndarray) -> np.ndarray:
    """Chia mỗi hàng cho độ dài của nó. Hàng toàn 0 giữ nguyên thay vì thành NaN."""
    n = np.linalg.norm(X, axis=-1, keepdims=True)
    return X / np.where(n < 1e-12, 1.0, n)


def trich_lo(danh_sach_rgb: list[np.ndarray], co_lo: int = 32) -> np.ndarray:
    """Trích đặc trưng cho một danh sách ảnh → (n, 512) đã chuẩn hóa L2."""
    import torch

    m = nap_mo_hinh()
    ra = np.empty((len(danh_sach_rgb), SO_CHIEU), np.float32)
    for i in range(0, len(danh_sach_rgb), co_lo):
        lo = danh_sach_rgb[i:i + co_lo]
        x = torch.from_numpy(np.stack([tien_xu_ly(r) for r in lo]))
        ra[i:i + len(lo)] = m(x).numpy()
    return chuan_hoa_l2(ra)


def trich(rgb: np.ndarray, mask: np.ndarray | None = None) -> np.ndarray:
    """Một ảnh → vector 512 chiều. `mask` không dùng: nền xám đã trung tính sẵn.

    Giữ tham số mask để mọi module đặc trưng có cùng chữ ký hàm.
    """
    return trich_lo([rgb])[0]


# ------------------------------------------------------------- self-test


def _selftest() -> None:
    """Chỉ kiểm phần thuần numpy. Phần cần mô hình nằm ở _selftest_mo_hinh."""
    assert SO_CHIEU == 512 and KHO_VAO == 224

    # tien_xu_ly: đúng khổ, đúng thứ tự trục, đúng phép chuẩn hóa.
    rgb = np.full((384, 384, 3), 128, np.uint8)
    x = tien_xu_ly(rgb)
    assert x.shape == (3, KHO_VAO, KHO_VAO), x.shape
    assert x.dtype == np.float32
    mong_doi = (128 / 255.0 - TB_IMAGENET) / LECH_IMAGENET
    assert np.allclose(x[:, 0, 0], mong_doi, atol=1e-5), (x[:, 0, 0], mong_doi)

    # Ảnh đã đúng khổ thì không thu nhỏ lại lần nữa.
    assert tien_xu_ly(np.zeros((224, 224, 3), np.uint8)).shape == (3, 224, 224)

    # Kênh phải tách đúng, không bị trộn: tô mỗi kênh một giá trị khác nhau.
    r = np.zeros((224, 224, 3), np.uint8)
    r[:, :, 0], r[:, :, 1], r[:, :, 2] = 255, 0, 0
    y = tien_xu_ly(r)
    assert y[0, 0, 0] > y[1, 0, 0] and y[0, 0, 0] > y[2, 0, 0]

    # chuan_hoa_l2: mọi hàng có độ dài 1; hàng 0 không sinh NaN.
    X = np.array([[3.0, 4.0], [0.0, 0.0], [-1.0, 0.0]])
    Z = chuan_hoa_l2(X)
    assert np.allclose(np.linalg.norm(Z[[0, 2]], axis=1), 1.0)
    assert np.allclose(Z[0], [0.6, 0.8])
    assert np.all(np.isfinite(Z)), "hàng toàn 0 sinh NaN"
    assert np.allclose(Z[1], 0.0)
    # Chuẩn hóa hai lần cho cùng kết quả.
    assert np.allclose(chuan_hoa_l2(Z), Z)


def _selftest_mo_hinh() -> None:
    """Cần tải trọng số ResNet18. Chỉ chạy với kiem_tra.py --day-du."""
    rng = np.random.default_rng(0)
    a = rng.integers(0, 256, (384, 384, 3), dtype=np.uint8)
    b = np.full((384, 384, 3), 128, np.uint8)

    V = trich_lo([a, b, a])
    assert V.shape == (3, SO_CHIEU), V.shape
    assert np.all(np.isfinite(V))
    assert np.allclose(np.linalg.norm(V, axis=1), 1.0, atol=1e-5)
    # Đông cứng và ở chế độ eval → cùng ảnh phải cho cùng vector.
    assert np.allclose(V[0], V[2], atol=1e-6), "mô hình không tất định"
    # Hai ảnh khác hẳn nhau phải cho hai vector khác nhau.
    assert not np.allclose(V[0], V[1], atol=1e-3)
    # Chia lô không được làm đổi kết quả.
    assert np.allclose(trich_lo([a, b], co_lo=1), V[:2], atol=1e-6)
