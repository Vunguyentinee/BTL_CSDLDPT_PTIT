"""Vòng đánh giá 5-fold dùng chung cho mọi khối đặc trưng.

Tách khỏi script để T17 (ablation 6 cấu hình) chỉ việc gọi lại hàm này với
từng ma trận đặc trưng, thay vì chép lại vòng lặp fold năm lần.
"""

from __future__ import annotations

import numpy as np

from . import cauhinh, timkiem

KS = (1, 5, 10)


def muc_ngau_nhien(nhan: np.ndarray, fold: np.ndarray) -> float:
    """P@k kỳ vọng khi xếp hạng ngẫu nhiên, trung bình macro theo loài.

    Không phải 1/20: lớp mất cân bằng 8,5 lần nên phải tính thật từ tỉ lệ
    từng loài trong gallery của từng fold.
    """
    ra = []
    for m in np.unique(nhan):
        ra.append(float(np.mean([(nhan[fold != f] == m).sum() / (fold != f).sum()
                                 for f in np.unique(fold)])))
    return float(np.mean(ra))


def danh_gia_5fold(X: np.ndarray, nhan: np.ndarray, fold: np.ndarray, ids: list[str],
                   do_do: str = "l2", z_score: bool = True) -> dict:
    """Chạy đủ 5 fold trên một ma trận đặc trưng.

    do_do:
        "l2"     — Euclid sau chuẩn hóa z-score. Dùng cho đặc trưng cổ điển,
                   nơi các chiều có đơn vị và biên độ rất khác nhau.
        "cosine" — chỉ so hướng. Dùng cho đặc trưng sâu đã chuẩn hóa L2; với
                   chúng, z-score sẽ phá mất phép chuẩn hóa nên z_score=False.

    Trả về: chỉ số theo fold, P@5 từng ảnh, và nhãn dự đoán top-1 (cho ma
    trận nhầm lẫn ở T18).
    """
    if do_do not in ("l2", "cosine"):
        raise ValueError(f"do_do phải là 'l2' hoặc 'cosine', nhận {do_do!r}")
    if len(X) != len(nhan) or len(X) != len(fold) or len(X) != len(ids):
        raise ValueError("X, nhan, fold, ids phải cùng độ dài")

    gom: dict[str, list[float]] = {f"P@{k}": [] for k in KS}
    gom["R@10"], gom["mAP"] = [], []
    p5 = np.zeros(len(X))
    du_doan = np.empty(len(X), dtype=object)

    for f in np.unique(fold):
        la_tv = fold == f
        # Quy tắc trung thực số 1: không ảnh nào vừa ở gallery vừa ở truy vấn.
        timkiem.kiem_tra_tach_biet([i for i, t in zip(ids, la_tv) if t],
                                   [i for i, t in zip(ids, la_tv) if not t])

        gal, tv = X[~la_tv], X[la_tv]
        if z_score:
            # Quy tắc trung thực số 3: mean/std lấy từ gallery của CHÍNH fold này.
            tb, sd = timkiem.tham_so_chuan_hoa(gal)
            gal, tv = timkiem.chuan_hoa(gal, tb, sd), timkiem.chuan_hoa(tv, tb, sd)

        d = (timkiem.khoang_cach_l2(tv, gal) if do_do == "l2"
             else timkiem.khoang_cach_cosine(tv, gal))
        idx = timkiem.xep_hang(d, d.shape[1])

        nhan_gal, nhan_tv = nhan[~la_tv], nhan[la_tv]
        for k in KS:
            p = timkiem.precision_at_k(nhan_tv, nhan_gal, idx, k)
            gom[f"P@{k}"].append(timkiem.macro_theo_loai(p, nhan_tv))
            if k == 5:
                p5[la_tv] = p
        gom["R@10"].append(timkiem.macro_theo_loai(
            timkiem.recall_at_k(nhan_tv, nhan_gal, idx, 10), nhan_tv))
        gom["mAP"].append(timkiem.macro_theo_loai(
            timkiem.average_precision(nhan_tv, nhan_gal, idx), nhan_tv))
        du_doan[la_tv] = nhan_gal[idx[:, 0]]

    return {
        "chi_so": {t: (float(np.mean(v)), float(np.std(v))) for t, v in gom.items()},
        "theo_fold": gom,
        "p5_moi_anh": p5,
        "du_doan_top1": du_doan,
        "do_chinh_xac_top1": timkiem.macro_theo_loai((du_doan == nhan).astype(float), nhan),
    }


def _selftest() -> None:
    rng = np.random.default_rng(7)
    # Ba cụm tách biệt hẳn nhau → hệ phải gần như hoàn hảo.
    tam = np.array([[0.0, 0.0], [50.0, 0.0], [0.0, 50.0]])
    nhan = np.repeat(["A", "B", "C"], 20)
    X = np.repeat(tam, 20, axis=0) + rng.normal(0, 0.5, (60, 2))
    fold = np.tile(np.arange(5), 12)
    ids = [f"i{i}" for i in range(60)]

    kq = danh_gia_5fold(X, nhan, fold, ids)
    assert kq["chi_so"]["P@5"][0] > 0.95, kq["chi_so"]["P@5"]
    assert kq["do_chinh_xac_top1"] > 0.95
    assert kq["p5_moi_anh"].shape == (60,)
    assert len(kq["theo_fold"]["P@5"]) == 5
    assert all(np.isfinite(v) for v, _ in kq["chi_so"].values())

    # Đặc trưng ngẫu nhiên không mang thông tin → phải về sát mức ngẫu nhiên.
    Xr = rng.normal(0, 1, (60, 2))
    kqr = danh_gia_5fold(Xr, nhan, fold, ids)
    assert kqr["chi_so"]["P@5"][0] < 0.6, kqr["chi_so"]["P@5"]
    assert abs(muc_ngau_nhien(nhan, fold) - 1 / 3) < 0.02

    # cosine: nhân một hàng với hằng số dương không được đổi kết quả.
    kc1 = danh_gia_5fold(X, nhan, fold, ids, do_do="cosine", z_score=False)
    X2 = X * rng.uniform(1.0, 9.0, (60, 1))
    kc2 = danh_gia_5fold(X2, nhan, fold, ids, do_do="cosine", z_score=False)
    assert np.allclose(kc1["p5_moi_anh"], kc2["p5_moi_anh"]), "cosine phải bất biến với độ dài"
    # Còn L2 thì KHÔNG bất biến — đó chính là lý do phải chọn độ đo theo loại.
    assert not np.allclose(danh_gia_5fold(X2, nhan, fold, ids)["p5_moi_anh"],
                           kc2["p5_moi_anh"])

    # Tham số sai phải báo lỗi.
    for sai in (dict(do_do="hamming"), dict()):
        try:
            if sai:
                danh_gia_5fold(X, nhan, fold, ids, **sai)
            else:
                danh_gia_5fold(X[:10], nhan, fold, ids)
            raise AssertionError("phải ném ValueError")
        except ValueError:
            pass
