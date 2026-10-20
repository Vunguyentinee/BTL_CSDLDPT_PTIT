"""Fisher score — đo giá trị thông tin của từng chiều đặc trưng.

Đây là cách định lượng hai khái niệm mà đề yêu cầu phân biệt:

  * **Đặc trưng tìm tương đồng** — phương sai **nội lớp** thấp: mọi ảnh của
    cùng một loài cho giá trị gần nhau, dù chụp ở điều kiện khác nhau.
  * **Đặc trưng tìm khác biệt** — phương sai **liên lớp** cao: các loài khác
    nhau cho giá trị tách xa nhau.

Một đặc trưng tốt cần cả hai, và tỉ số giữa chúng chính là Fisher score:

    F = phương sai liên lớp / phương sai nội lớp

F lớn nghĩa là các loài tách xa nhau mà trong mỗi loài lại tụm chặt. F ≈ 0
nghĩa là chiều đó không phân biệt được gì.

Fisher **bất biến với phép đổi thang đo** (nhân hoặc cộng hằng số cho cả cột
đều không đổi F), nên so sánh được giữa các khối đặc trưng có đơn vị khác
nhau mà không cần chuẩn hóa trước.

Mọi phép tính ở đây phải chạy trên **mẫu cân bằng**: nếu để nguyên 162 ảnh cá
dĩa cạnh 19 ảnh cá lóc thì trung bình toàn cục bị kéo về phía lớp lớn, và
phương sai liên lớp phản ánh kích thước lớp nhiều hơn phản ánh khác biệt loài.
"""

from __future__ import annotations

import numpy as np


def mau_can_bang(nhan: np.ndarray, moi_loai: int | None = None,
                 seed: int = 20261020) -> np.ndarray:
    """Chỉ số của một mẫu có số ảnh bằng nhau ở mọi loài.

    `moi_loai` mặc định là cỡ lớp nhỏ nhất — lấy tất cả ảnh của loài ít nhất
    và rút ngẫu nhiên bấy nhiêu ảnh ở các loài còn lại.
    """
    rng = np.random.default_rng(seed)
    loai = np.unique(nhan)
    n = moi_loai or min(int((nhan == m).sum()) for m in loai)
    ra = []
    for m in loai:
        idx = np.flatnonzero(nhan == m)
        ra.append(rng.choice(idx, n, replace=False) if len(idx) > n else idx)
    return np.sort(np.concatenate(ra))


def fisher_tung_chieu(X: np.ndarray, nhan: np.ndarray) -> dict[str, np.ndarray]:
    """Ba cột cho từng chiều: phương sai nội lớp, liên lớp, và tỉ số.

    Dùng công thức có trọng số theo cỡ lớp. Với mẫu cân bằng thì trọng số
    bằng nhau, nhưng giữ dạng tổng quát để hàm vẫn đúng khi gọi trên mẫu lệch.
    """
    X = np.asarray(X, np.float64)
    loai = np.unique(nhan)
    N = len(X)
    tb_chung = X.mean(axis=0)

    noi = np.zeros(X.shape[1])
    lien = np.zeros(X.shape[1])
    for m in loai:
        Xm = X[nhan == m]
        w = len(Xm) / N
        noi += w * Xm.var(axis=0)
        lien += w * (Xm.mean(axis=0) - tb_chung) ** 2

    # Chiều nào hằng số trong mọi lớp thì nội lớp = 0; tránh chia 0 bằng cách
    # trả về 0 khi liên lớp cũng bằng 0 (chiều chết), vô cực thì vô nghĩa.
    ti_so = np.where(noi > 1e-15, lien / np.maximum(noi, 1e-15), 0.0)
    return {"noi_lop": noi, "lien_lop": lien, "ti_so": ti_so}


def eta_binh_phuong(X: np.ndarray, nhan: np.ndarray) -> np.ndarray:
    """Tỉ lệ phương sai do loài giải thích, từng chiều. Nằm trong [0; 1].

        eta² = liên lớp / (liên lớp + nội lớp)

    Đây là Fisher đã bóp về thang [0; 1]: eta²=0 nghĩa là chiều đó không biết
    gì về loài, eta²=1 nghĩa là biết hoàn toàn. Dễ đọc hơn tỉ số Fisher thô
    (vốn chạy từ 0 tới vô cực) và vẫn bất biến với phép đổi thang đo.
    """
    f = fisher_tung_chieu(X, nhan)
    tong = f["lien_lop"] + f["noi_lop"]
    return np.where(tong > 1e-15, f["lien_lop"] / np.maximum(tong, 1e-15), 0.0)


def fisher_khoi(X: np.ndarray, nhan: np.ndarray) -> dict[str, float]:
    """Gộp cả khối thành vài con số so sánh được giữa các bộ đặc trưng.

    Con số chính là `eta2_tb` — trung bình eta² trên mọi chiều. Chọn nó chứ
    KHÔNG chọn tỉ số Fisher gộp (tổng liên lớp / tổng nội lớp) vì tỉ số gộp
    **không bất biến thang đo**: Bộ A① có kênh L trong [0;100] còn a, b trong
    [-128;127], nên chiều nào biên độ lớn sẽ thống trị con số gộp, và đem so
    với Bộ B đã chuẩn hóa L2 là so sai.

    Một con số không đủ: khối 512 chiều mà chỉ vài chục chiều mạnh sẽ có
    trung bình thấp dù truy hồi rất tốt. Vì vậy trả về cả phân vị, giá trị
    cao nhất và số chiều mạnh để thấy hình dạng phân bố.
    """
    f = fisher_tung_chieu(X, nhan)
    e = eta_binh_phuong(X, nhan)
    return {
        "eta2_tb": float(e.mean()),
        "eta2_cao_nhat": float(e.max()),
        "fisher_trung_vi": float(np.median(f["ti_so"])),
        "fisher_cao_nhat": float(f["ti_so"].max()),
        "so_chieu": int(X.shape[1]),
        "so_chieu_manh": int((f["ti_so"] >= 1.0).sum()),
    }


def eta2_top(X: np.ndarray, nhan: np.ndarray, k: int) -> float:
    """Trung bình eta² của **k chiều mạnh nhất**.

    Đây là thước đo phải dùng khi so hai khối có số chiều khác nhau. Trung
    bình trên TOÀN BỘ chiều bị loãng: Bộ B có 512 chiều, với một cặp loài cụ
    thể thì phần lớn chúng không liên quan, nên trung bình tụt xuống dù vài
    chục chiều còn lại tách cặp đó rất tốt. Bộ A① chỉ có 9 chiều và cả 9 đều
    nói về màu nên không bị loãng.

    Đo đúng: lấy cùng một số chiều ở cả hai bên. Thực tế với cặp cá hề, trung
    bình toàn bộ cho Bộ A① 0,103 và Bộ B 0,161 — gần như hòa; còn top-9 cho
    0,103 và 0,665, khớp với chênh lệch P@5 thật (19% so với 96%).
    """
    e = eta_binh_phuong(X, nhan)
    k = min(k, len(e))
    return float(np.sort(e)[::-1][:k].mean())


def fisher_cap(X: np.ndarray, nhan: np.ndarray, a: str, b: str,
               k: int | None = None) -> float:
    """eta² của riêng hai loài — dùng cho các cặp cùng họ, chỗ khó nhất.

    `k` là số chiều mạnh nhất đem trung bình. Khi so nhiều khối với nhau thì
    **bắt buộc truyền k bằng nhau**, nếu không kết quả sẽ lệch về khối ít
    chiều. Bỏ trống thì lấy trung bình toàn bộ chiều.
    """
    chon = (nhan == a) | (nhan == b)
    if not chon.any():
        raise ValueError(f"không có ảnh nào của {a} hoặc {b}")
    if k is not None:
        return eta2_top(X[chon], nhan[chon], k)
    return fisher_khoi(X[chon], nhan[chon])["eta2_tb"]


# ------------------------------------------------------------- self-test


def _selftest() -> None:
    rng = np.random.default_rng(3)
    nhan = np.repeat(["A", "B", "C"], 40)

    # Chiều 0: ba lớp tách xa, trong lớp tụm chặt  → Fisher rất cao.
    # Chiều 1: ba lớp trùng nhau hoàn toàn          → Fisher ~ 0.
    # Chiều 2: hằng số tuyệt đối                    → chiều chết, trả về 0.
    X = np.empty((120, 3))
    X[:, 0] = np.repeat([0.0, 10.0, 20.0], 40) + rng.normal(0, 0.5, 120)
    X[:, 1] = rng.normal(0, 1.0, 120)
    X[:, 2] = 7.0

    f = fisher_tung_chieu(X, nhan)
    assert set(f) == {"noi_lop", "lien_lop", "ti_so"}
    assert all(v.shape == (3,) for v in f.values())
    # Cột ba phải đúng bằng cột hai chia cột một.
    assert np.allclose(f["ti_so"][:2], f["lien_lop"][:2] / f["noi_lop"][:2])
    assert f["ti_so"][0] > 50, f["ti_so"][0]
    assert f["ti_so"][1] < 1.0, f["ti_so"][1]
    assert f["ti_so"][2] == 0.0, "chiều hằng số phải cho 0 chứ không phải vô cực"
    assert np.all(np.isfinite(f["ti_so"]))
    # Phương sai không bao giờ âm.
    assert np.all(f["noi_lop"] >= 0) and np.all(f["lien_lop"] >= 0)

    # Bất biến thang đo: nhân và cộng hằng số không đổi tỉ số.
    f2 = fisher_tung_chieu(X * 1000.0 + 5.0, nhan)
    assert np.allclose(f["ti_so"], f2["ti_so"], rtol=1e-9)
    # Nhưng hai cột phương sai thì PHẢI đổi — nếu không là tính sai.
    assert not np.allclose(f["noi_lop"][:2], f2["noi_lop"][:2])

    # Đảo thứ tự ảnh không đổi kết quả.
    hv = rng.permutation(120)
    assert np.allclose(fisher_tung_chieu(X[hv], nhan[hv])["ti_so"], f["ti_so"])

    # --- gộp khối ---
    # eta²: chiều tách tốt về gần 1, chiều vô dụng về gần 0, chiều chết đúng 0.
    e = eta_binh_phuong(X, nhan)
    assert np.all((e >= 0) & (e <= 1)), e
    assert e[0] > 0.98, e[0]
    assert e[1] < 0.1, e[1]
    assert e[2] == 0.0

    k = fisher_khoi(X, nhan)
    assert k["so_chieu"] == 3
    assert k["so_chieu_manh"] == 1, k["so_chieu_manh"]
    assert k["fisher_cao_nhat"] == f["ti_so"].max()
    assert 0.0 <= k["eta2_tb"] <= 1.0
    assert k["eta2_tb"] < k["eta2_cao_nhat"]

    # Con số gộp phải BẤT BIẾN THANG ĐO — đây là lý do chọn eta² thay vì tỉ số
    # Fisher gộp. Phóng đại một cột lên 1000 lần không được đổi kết quả.
    Xl = X.copy()
    Xl[:, 1] *= 1000.0
    assert abs(fisher_khoi(Xl, nhan)["eta2_tb"] - k["eta2_tb"]) < 1e-9,         "con số gộp bị thang đo của một chiều chi phối"

    # Nhãn ngẫu nhiên → không còn cấu trúc lớp → phải sụp về gần 0.
    nhan_lung_tung = rng.permutation(nhan)
    assert fisher_khoi(X, nhan_lung_tung)["eta2_tb"] < 0.1

    # --- mẫu cân bằng ---
    lech = np.array(["A"] * 100 + ["B"] * 20 + ["C"] * 7)
    idx = mau_can_bang(lech)
    u, c = np.unique(lech[idx], return_counts=True)
    assert list(c) == [7, 7, 7], c          # rút về cỡ lớp nhỏ nhất
    assert len(set(idx.tolist())) == len(idx), "có chỉ số bị lặp"
    assert np.array_equal(idx, mau_can_bang(lech)), "không tái lập được"
    assert not np.array_equal(idx, mau_can_bang(lech, seed=99))
    # Chỉ định cỡ mẫu: lớp nhỏ hơn mức đó thì lấy hết, không nhân bản.
    c2 = np.unique(lech[mau_can_bang(lech, 20)], return_counts=True)[1]
    assert list(c2) == [20, 20, 7], c2

    # --- eta2_top: thước đo công bằng giữa các khối khác số chiều ---
    # Khối 3 chiều: một chiều tốt, hai chiều vô dụng.
    # Khối 12 chiều: cùng một chiều tốt đó, thêm 11 chiều rác.
    # Trung bình toàn bộ sẽ nói khối 3 chiều tốt hơn — đó là ảo giác do loãng.
    # Trung bình top-1 phải nói hai khối NGANG NHAU.
    X_it = X.copy()
    X_nhieu = np.hstack([X, rng.normal(0, 1, (120, 9))])
    assert fisher_khoi(X_it, nhan)["eta2_tb"] > fisher_khoi(X_nhieu, nhan)["eta2_tb"],         "thêm chiều rác phải làm trung bình toàn bộ tụt"
    assert abs(eta2_top(X_it, nhan, 1) - eta2_top(X_nhieu, nhan, 1)) < 1e-9,         "top-k phải miễn nhiễm với chiều rác thêm vào"
    # k lớn hơn số chiều thì kẹp lại, không nổ.
    assert eta2_top(X_it, nhan, 999) == eta_binh_phuong(X_it, nhan).mean()
    # top-k luôn >= trung bình toàn bộ.
    assert eta2_top(X_nhieu, nhan, 3) >= fisher_khoi(X_nhieu, nhan)["eta2_tb"]

    # --- theo cặp ---
    # A và C cách nhau 20 đơn vị, A và B cách 10 → cặp xa phải cho Fisher lớn hơn.
    assert fisher_cap(X[:, :1], nhan, "A", "C") > fisher_cap(X[:, :1], nhan, "A", "B")
    assert fisher_cap(X, nhan, "A", "C", k=1) >= fisher_cap(X, nhan, "A", "C")
    try:
        fisher_cap(X, nhan, "X", "Y")
        raise AssertionError("loài không tồn tại phải ném ValueError")
    except ValueError:
        pass
