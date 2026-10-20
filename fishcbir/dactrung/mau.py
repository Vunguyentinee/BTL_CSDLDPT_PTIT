"""Đặc trưng ① — Color moments trong không gian Lab (9 chiều).

Đây là đặc trưng đầu tiên của Bộ A, và là lát cắt dọc đầu tiên của cả hệ:
nếu đường ống chạy thông từ ảnh đến Precision@5 với 9 chiều này thì thêm 492
chiều còn lại chỉ là lặp lại cùng một khuôn.

Vì sao Lab chứ không phải RGB: Lab tách độ sáng (L) khỏi màu (a, b), và
khoảng cách Euclid trong Lab xấp xỉ khác biệt màu mà mắt người cảm nhận. Ảnh
cá chụp ở điều kiện sáng rất khác nhau, nên tách được độ sáng ra là quan trọng.

Vì sao moment chứ không phải histogram: ba moment đầu (trung bình, độ lệch
chuẩn, độ xiên) tóm tắt phân bố màu bằng 9 số, không cần chọn số ngăn và
không bị thưa. Histogram HSV theo dải dọc thân là đặc trưng ② riêng, làm sau.

Chỉ tính trên điểm ảnh trong mask. Nền xám (128,128,128) nếu lọt vào sẽ kéo
mọi ảnh về cùng một màu trung tính và xóa sạch khác biệt giữa các loài.
"""

from __future__ import annotations

import numpy as np

TEN: list[str] = [f"{m}_{c}" for c in "Lab" for m in ("tb", "lech", "xien")]
SO_CHIEU = len(TEN)

# Điểm trắng D65 và hai hằng số của CIE Lab.
_TRANG_D65 = np.array([0.95047, 1.00000, 1.08883])
_EPS = 216.0 / 24389.0
_KAPPA = 24389.0 / 27.0

# sRGB tuyến tính → XYZ (D65).
_M = np.array([
    [0.4124564, 0.3575761, 0.1804375],
    [0.2126729, 0.7151522, 0.0721750],
    [0.0193339, 0.1191920, 0.9503041],
])


def rgb_sang_lab(rgb: np.ndarray) -> np.ndarray:
    """RGB uint8 (..., 3) → Lab float (..., 3). L trong [0,100], a/b khoảng [-128,127]."""
    c = np.asarray(rgb, np.float64) / 255.0
    # Gỡ gamma sRGB. Ngưỡng 0,04045 là chỗ nối đoạn tuyến tính với đoạn lũy thừa.
    tt = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    xyz = tt @ _M.T / _TRANG_D65
    f = np.where(xyz > _EPS, np.cbrt(xyz), (_KAPPA * xyz + 16.0) / 116.0)
    fx, fy, fz = f[..., 0], f[..., 1], f[..., 2]
    return np.stack([116.0 * fy - 16.0, 500.0 * (fx - fy), 200.0 * (fy - fz)], axis=-1)


def color_moments(rgb: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """9 chiều: (trung bình, độ lệch chuẩn, độ xiên) × (L, a, b), chỉ trên mask.

    Độ xiên lấy căn bậc ba có dấu của moment trung tâm bậc ba, theo đúng định
    nghĩa color moments gốc của Stricker & Orengo. Lấy căn bậc ba để đưa về
    cùng đơn vị với hai moment kia, nếu không nó sẽ lớn hơn hàng nghìn lần và
    nuốt trọn khoảng cách.
    """
    mask = np.asarray(mask, bool)
    if mask.shape != rgb.shape[:2]:
        raise ValueError(f"mask {mask.shape} không khớp ảnh {rgb.shape[:2]}")
    if not mask.any():
        raise ValueError("mask rỗng — không có điểm ảnh nào để tính")

    lab = rgb_sang_lab(rgb[mask])            # (N, 3), chỉ lấy điểm trong mask
    tb = lab.mean(axis=0)
    lech_tam = lab - tb
    lech = np.sqrt((lech_tam ** 2).mean(axis=0))
    m3 = (lech_tam ** 3).mean(axis=0)
    xien = np.cbrt(m3)                        # cbrt giữ dấu, khác với m3**(1/3)

    return np.stack([tb, lech, xien], axis=0).T.reshape(-1)


def trich(rgb: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Tên gọi thống nhất cho mọi module đặc trưng."""
    return color_moments(rgb, mask)


# ------------------------------------------------------------- self-test


def _selftest() -> None:
    assert SO_CHIEU == 9 and len(TEN) == 9
    assert TEN[0] == "tb_L" and TEN[-1] == "xien_b"

    # Màu trắng tinh → L=100, a=b=0. Đây là mốc chuẩn của CIE Lab.
    tr = rgb_sang_lab(np.array([[255, 255, 255]], np.uint8))[0]
    # Dung sai 1e-4 chứ không phải 0: ma trận sRGB->XYZ chuẩn chỉ có 7 chữ số
    # sau dấu phẩy nên điểm trắng ra 100,00000004. Sai số của hằng số công bố,
    # không phải của phép tính.
    assert abs(tr[0] - 100.0) < 1e-4, tr
    assert abs(tr[1]) < 1e-3 and abs(tr[2]) < 1e-3, tr
    # Màu đen → L=0.
    assert abs(rgb_sang_lab(np.array([[0, 0, 0]], np.uint8))[0][0]) < 1e-9
    # Xám trung tính → a=b=0 nhưng L nằm giữa.
    x = rgb_sang_lab(np.array([[128, 128, 128]], np.uint8))[0]
    assert abs(x[1]) < 1e-3 and abs(x[2]) < 1e-3, x
    assert 50.0 < x[0] < 56.0, x
    # Đỏ phải có a dương rõ rệt, xanh lam phải có b âm rõ rệt.
    assert rgb_sang_lab(np.array([[255, 0, 0]], np.uint8))[0][1] > 50
    assert rgb_sang_lab(np.array([[0, 0, 255]], np.uint8))[0][2] < -50

    # Vùng mask một màu duy nhất → độ lệch chuẩn và độ xiên đều bằng 0.
    rgb = np.zeros((10, 10, 3), np.uint8)
    rgb[2:8, 2:8] = (200, 50, 50)
    mask = np.zeros((10, 10), bool)
    mask[2:8, 2:8] = True
    v = color_moments(rgb, mask)
    assert v.shape == (9,), v.shape
    assert np.allclose(v[[1, 4, 7]], 0.0), v   # ba độ lệch chuẩn
    assert np.allclose(v[[2, 5, 8]], 0.0), v   # ba độ xiên

    # PHÉP KIỂM QUAN TRỌNG NHẤT: đổi màu nền ngoài mask không được đổi kết quả.
    # Nếu phép kiểm này hỏng nghĩa là nền đang rò vào đặc trưng.
    rgb2 = rgb.copy()
    rgb2[~mask] = (128, 128, 128)
    rgb3 = rgb.copy()
    rgb3[~mask] = (255, 255, 0)
    assert np.allclose(color_moments(rgb2, mask), color_moments(rgb3, mask))
    assert np.allclose(color_moments(rgb, mask), color_moments(rgb3, mask))

    # Đặc trưng không phụ thuộc vị trí điểm ảnh — chuyển vị cho cùng kết quả.
    assert np.allclose(color_moments(rgb, mask),
                       color_moments(np.transpose(rgb, (1, 0, 2)).copy(), mask.T.copy()))

    # Độ xiên phải giữ được dấu: phân bố lệch phải cho giá trị dương.
    ảnh = np.zeros((1, 100, 3), np.uint8)
    ảnh[0, :90] = (10, 128, 128)
    ảnh[0, 90:] = (250, 128, 128)
    m = np.ones((1, 100), bool)
    assert color_moments(ảnh, m)[2] > 0, "độ xiên của phân bố lệch phải phải > 0"
    ảnh2 = ảnh[:, ::-1].copy()
    ảnh2[0, :10] = (10, 128, 128)
    ảnh2[0, 10:] = (250, 128, 128)
    assert color_moments(ảnh2, m)[2] < 0, "độ xiên của phân bố lệch trái phải < 0"

    # Mask rỗng và mask sai khổ phải báo lỗi rõ ràng chứ không trả về NaN.
    for xau, loi in ((np.zeros((10, 10), bool), "rỗng"), (np.ones((5, 5), bool), "không khớp")):
        try:
            color_moments(rgb, xau)
            raise AssertionError(f"mask {loi} phải ném ValueError")
        except ValueError:
            pass

    # Không bao giờ được sinh NaN hay vô cực.
    assert np.all(np.isfinite(color_moments(rgb, mask)))
