"""Tìm kiếm top-k và các chỉ số đánh giá.

Toàn bộ là hàm thuần trên mảng numpy, không đụng đĩa và không biết gì về cá —
nhờ vậy test được bằng dữ liệu tự sinh, và sau này thay NumPy bằng pgvector
chỉ cần đổi hàm `xep_hang`, phần đo đếm giữ nguyên.

Ba quy tắc trung thực được cài thẳng vào code chứ không chỉ ghi trong tài liệu:
  1. Ảnh truy vấn không bao giờ nằm trong gallery của cùng fold — `kiem_tra_tach_biet`.
  2. Trung bình macro theo loài, không phải theo ảnh — loài 162 ảnh không được
     lấn át loài 19 ảnh.
  3. Chuẩn hóa z-score lấy mean/std từ GALLERY, không phải từ toàn bộ dữ liệu —
     nếu lấy từ toàn bộ thì thông tin của tập truy vấn rò vào gallery.
"""

from __future__ import annotations

import numpy as np


def tham_so_chuan_hoa(gallery: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """mean và std tính TRÊN GALLERY. std bằng 0 thì thay bằng 1 để khỏi chia 0.

    Chiều nào có std = 0 trên gallery là chiều không mang thông tin; đặt std=1
    biến nó thành hằng số 0 sau chuẩn hóa, không ảnh hưởng khoảng cách.
    """
    tb = gallery.mean(axis=0)
    sd = gallery.std(axis=0)
    return tb, np.where(sd < 1e-12, 1.0, sd)


def chuan_hoa(X: np.ndarray, tb: np.ndarray, sd: np.ndarray) -> np.ndarray:
    return (X - tb) / sd


def khoang_cach_l2(truy_van: np.ndarray, gallery: np.ndarray) -> np.ndarray:
    """Ma trận khoảng cách Euclid (n_truy_van, n_gallery).

    Khai triển ||q-g||² = ||q||² - 2q·g + ||g||² để dùng một phép nhân ma trận
    thay vì vòng lặp Python. Kẹp về >= 0 vì sai số dấu phẩy động có thể cho ra
    số âm rất nhỏ, và căn của số âm thành NaN.
    """
    q2 = (truy_van ** 2).sum(axis=1)[:, None]
    g2 = (gallery ** 2).sum(axis=1)[None, :]
    d2 = np.maximum(q2 - 2.0 * truy_van @ gallery.T + g2, 0.0)
    return np.sqrt(d2)


def xep_hang(d: np.ndarray, k: int) -> np.ndarray:
    """Chỉ số của k gallery gần nhất cho mỗi truy vấn, đã sắp từ gần đến xa.

    argpartition lấy k phần tử nhỏ nhất với chi phí O(n) rồi mới sắp k phần tử
    đó — nhanh hơn argsort toàn bộ khi k nhỏ, mà kết quả giống hệt.
    """
    k = min(k, d.shape[1])
    tho = np.argpartition(d, k - 1, axis=1)[:, :k]
    thu_tu = np.argsort(np.take_along_axis(d, tho, axis=1), axis=1, kind="stable")
    return np.take_along_axis(tho, thu_tu, axis=1)


def kiem_tra_tach_biet(id_truy_van: list[str], id_gallery: list[str]) -> None:
    """Ném lỗi nếu một ảnh vừa ở gallery vừa ở truy vấn. Quy tắc trung thực số 1."""
    chung = set(id_truy_van) & set(id_gallery)
    if chung:
        vd = ", ".join(sorted(chung)[:5])
        raise ValueError(f"{len(chung)} ảnh vừa ở gallery vừa ở truy vấn: {vd}")


def precision_at_k(nhan_tv: np.ndarray, nhan_gal: np.ndarray, idx: np.ndarray,
                   k: int) -> np.ndarray:
    """P@k cho từng truy vấn: tỉ lệ trong k kết quả đầu có cùng nhãn với truy vấn."""
    k = min(k, idx.shape[1])
    trung = nhan_gal[idx[:, :k]] == nhan_tv[:, None]
    return trung.sum(axis=1) / k


def recall_at_k(nhan_tv: np.ndarray, nhan_gal: np.ndarray, idx: np.ndarray,
                k: int) -> np.ndarray:
    """Tỉ lệ ảnh cùng loài trong gallery được tìm thấy trong k kết quả đầu."""
    k = min(k, idx.shape[1])
    trung = nhan_gal[idx[:, :k]] == nhan_tv[:, None]
    tong = (nhan_gal[None, :] == nhan_tv[:, None]).sum(axis=1)
    return np.where(tong > 0, trung.sum(axis=1) / np.maximum(tong, 1), 0.0)


def average_precision(nhan_tv: np.ndarray, nhan_gal: np.ndarray,
                      idx: np.ndarray) -> np.ndarray:
    """AP cho từng truy vấn trên toàn bộ danh sách đã xếp hạng."""
    trung = nhan_gal[idx] == nhan_tv[:, None]
    tich_luy = np.cumsum(trung, axis=1)
    hang = np.arange(1, trung.shape[1] + 1)[None, :]
    p_tai_moi_hit = tich_luy / hang * trung
    tong_lien_quan = (nhan_gal[None, :] == nhan_tv[:, None]).sum(axis=1)
    return np.where(tong_lien_quan > 0,
                    p_tai_moi_hit.sum(axis=1) / np.maximum(tong_lien_quan, 1), 0.0)


def macro_theo_loai(gia_tri: np.ndarray, nhan: np.ndarray) -> float:
    """Trung bình theo loài rồi mới trung bình giữa các loài. Quy tắc trung thực số 2.

    Trung bình thẳng trên 1.085 ảnh sẽ để SYM_SPP (162 ảnh) có tiếng nói gấp
    8,5 lần CHA_STR (19 ảnh). Macro cho mỗi loài đúng một phiếu.
    """
    loai = np.unique(nhan)
    return float(np.mean([gia_tri[nhan == m].mean() for m in loai]))


def theo_loai(gia_tri: np.ndarray, nhan: np.ndarray) -> dict[str, float]:
    return {str(m): float(gia_tri[nhan == m].mean()) for m in np.unique(nhan)}


# ------------------------------------------------------------- self-test


def _selftest() -> None:
    # --- chuẩn hóa ---
    g = np.array([[0.0, 5.0], [2.0, 5.0], [4.0, 5.0]])
    tb, sd = tham_so_chuan_hoa(g)
    assert np.allclose(tb, [2.0, 5.0])
    assert np.allclose(sd, [np.sqrt(8 / 3), 1.0])     # cột hằng số → std thay bằng 1
    z = chuan_hoa(g, tb, sd)
    assert np.allclose(z[:, 1], 0.0), "cột hằng số phải thành 0, không phải NaN"
    assert abs(z[:, 0].mean()) < 1e-12
    # Truy vấn dùng ĐÚNG tham số của gallery, nên trung bình của nó không bắt buộc bằng 0.
    q = np.array([[10.0, 7.0]])
    assert np.allclose(chuan_hoa(q, tb, sd), [[(10 - 2) / np.sqrt(8 / 3), 2.0]])

    # --- khoảng cách ---
    a = np.array([[0.0, 0.0], [3.0, 4.0]])
    b = np.array([[0.0, 0.0], [1.0, 0.0], [3.0, 4.0]])
    d = khoang_cach_l2(a, b)
    assert d.shape == (2, 3)
    assert np.allclose(d[0], [0.0, 1.0, 5.0]), d[0]
    assert np.allclose(d[1], [5.0, np.sqrt(4 + 16), 0.0]), d[1]
    assert np.all(np.isfinite(d)) and np.all(d >= 0)
    # Điểm trùng nhau phải cho khoảng cách đúng 0, không phải số âm nhỏ rồi NaN.
    lon = np.full((1, 50), 1e3)
    assert khoang_cach_l2(lon, lon)[0, 0] == 0.0

    # --- xếp hạng ---
    d = np.array([[5.0, 1.0, 3.0, 2.0], [0.5, 9.0, 0.1, 7.0]])
    idx = xep_hang(d, 3)
    assert idx.shape == (2, 3)
    assert list(idx[0]) == [1, 3, 2], idx[0]
    assert list(idx[1]) == [2, 0, 3], idx[1]
    # k lớn hơn số gallery thì bị kẹp lại chứ không nổ.
    assert xep_hang(d, 99).shape == (2, 4)

    # --- tách biệt gallery / truy vấn ---
    kiem_tra_tach_biet(["a", "b"], ["c", "d"])
    try:
        kiem_tra_tach_biet(["a", "b"], ["b", "c"])
        raise AssertionError("phải ném ValueError khi có ảnh chung")
    except ValueError as e:
        assert "b" in str(e)

    # --- các chỉ số ---
    nhan_gal = np.array(["X", "X", "Y", "Y", "Y"])
    nhan_tv = np.array(["X", "Y"])
    # Truy vấn 1 xếp hạng: X, Y, X, Y, Y  → P@1=1, P@2=1/2, P@4=2/4
    # Truy vấn 2 xếp hạng: Y, Y, Y, X, X  → P@1=1, P@3=1, recall@3=1
    idx = np.array([[0, 2, 1, 3, 4], [2, 3, 4, 0, 1]])
    assert np.allclose(precision_at_k(nhan_tv, nhan_gal, idx, 1), [1.0, 1.0])
    assert np.allclose(precision_at_k(nhan_tv, nhan_gal, idx, 2), [0.5, 1.0])
    assert np.allclose(precision_at_k(nhan_tv, nhan_gal, idx, 4), [0.5, 0.75])
    # Truy vấn 1 (X) có 2 ảnh cùng loài, truy vấn 2 (Y) có 3.
    # top-2 của TV1 bắt 1/2; top-2 của TV2 bắt 2/3.
    assert np.allclose(recall_at_k(nhan_tv, nhan_gal, idx, 2), [0.5, 2.0 / 3.0])
    # top-3 bắt hết cả hai bên.
    assert np.allclose(recall_at_k(nhan_tv, nhan_gal, idx, 3), [1.0, 1.0])
    # AP của truy vấn 2: hit ở hạng 1,2,3 → (1/1+2/2+3/3)/3 = 1
    ap = average_precision(nhan_tv, nhan_gal, idx)
    assert abs(ap[1] - 1.0) < 1e-12, ap
    # AP của truy vấn 1: hit ở hạng 1 và 3 → (1/1 + 2/3)/2
    assert abs(ap[0] - (1.0 + 2.0 / 3.0) / 2.0) < 1e-12, ap

    # --- macro ---
    # Lớp lớn 4 ảnh toàn 0, lớp nhỏ 1 ảnh được 1. Trung bình thường = 0,2;
    # macro = 0,5. Chênh lệch này chính là lý do phải dùng macro.
    gt = np.array([0.0, 0.0, 0.0, 0.0, 1.0])
    nh = np.array(["to", "to", "to", "to", "nho"])
    assert abs(gt.mean() - 0.2) < 1e-12
    assert abs(macro_theo_loai(gt, nh) - 0.5) < 1e-12
    assert theo_loai(gt, nh) == {"nho": 1.0, "to": 0.0}
