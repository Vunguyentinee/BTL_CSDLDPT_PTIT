"""Chạy toàn tuyến: chia fold → trích đặc trưng → tìm kiếm → đo chỉ số.

Đây là lát cắt dọc đầu tiên của hệ (việc T2, T3, T4 trong tasks/plan.md). Mục
tiêu không phải điểm số cao mà là **toàn tuyến thông**: nếu 9 chiều color
moments đã cho P@5 cao hơn hẳn mức ngẫu nhiên thì phần còn lại của Bộ A chỉ
là lặp lại cùng một khuôn.

    python scripts/danh_gia.py              # chạy đủ, dùng lại đặc trưng đã trích
    python scripts/danh_gia.py --trich-lai  # bỏ cache, trích lại từ ảnh
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

from fishcbir import cauhinh, chia_fold, danhmuc, timkiem  # noqa: E402
from fishcbir.dactrung import mau  # noqa: E402

CACHE = cauhinh.KET_QUA / "dactrung_mau.npz"


def trich_tat_ca(anh: list[danhmuc.Anh], trich_lai: bool) -> np.ndarray:
    """Ma trận đặc trưng (n_anh, 9), hàng thứ i ứng với anh[i]."""
    ids = [a.image_id for a in anh]
    if CACHE.exists() and not trich_lai:
        d = np.load(CACHE, allow_pickle=False)
        if list(d["image_id"]) == ids:
            print(f"Dùng lại đặc trưng đã trích: {CACHE.relative_to(ROOT)}")
            return d["X"]
        print("Cache không khớp danh sách ảnh hiện tại — trích lại.")

    print(f"Trích color moments cho {len(anh)} ảnh...")
    t0 = time.time()
    X = np.empty((len(anh), mau.SO_CHIEU), np.float64)
    for i, a in enumerate(anh):
        rgb, mask = danhmuc.nap_anh(a.duong_dan)
        X[i] = mau.trich(rgb, mask)
        if (i + 1) % 200 == 0:
            print(f"  {i + 1}/{len(anh)}")
    giay = time.time() - t0
    print(f"  xong trong {giay:.1f}s ({giay / len(anh) * 1000:.1f} ms/ảnh)")

    if not np.all(np.isfinite(X)):
        raise SystemExit("LỖI: đặc trưng có NaN hoặc vô cực")
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(CACHE, X=X, image_id=np.array(ids))
    return X


def muc_ngau_nhien(nhan: np.ndarray, fold: np.ndarray, k: int) -> float:
    """P@k kỳ vọng nếu xếp hạng hoàn toàn ngẫu nhiên, trung bình macro.

    Mốc so sánh bắt buộc. Lớp mất cân bằng nên con số này KHÔNG phải 1/20;
    phải tính thật từ tỉ lệ từng loài trong gallery của từng fold.
    """
    ra = []
    for m in np.unique(nhan):
        theo_fold = []
        for f in np.unique(fold):
            gal = fold != f
            if not (fold == f).any():
                continue
            theo_fold.append((nhan[gal] == m).sum() / gal.sum())
        ra.append(float(np.mean(theo_fold)))
    return float(np.mean(ra))


def main() -> int:
    ap = argparse.ArgumentParser(description="Đánh giá 5-fold cho đặc trưng color moments")
    ap.add_argument("--trich-lai", action="store_true", help="bỏ cache, trích lại từ ảnh")
    a = ap.parse_args()

    # --- T2: chia fold ---
    anh = danhmuc.liet_ke_anh()
    print(f"{len(anh)} ảnh / {len(set(x.ma_loai for x in anh))} loài")
    f_map = chia_fold.chia(anh)
    chia_fold.ghi_csv(cauhinh.FOLDS_CSV, anh, f_map)
    print(f"Đã ghi {cauhinh.FOLDS_CSV.relative_to(ROOT)}")

    nhan = np.array([x.ma_loai for x in anh])
    fold = np.array([f_map[x.image_id] for x in anh])
    ids = [x.image_id for x in anh]
    tong = [int((fold == k).sum()) for k in range(cauhinh.SO_FOLD)]
    print(f"Kích thước 5 fold: {tong}")

    # --- T3: trích đặc trưng ---
    X = trich_tat_ca(anh, a.trich_lai)
    print(f"Ma trận đặc trưng {X.shape}")

    # --- T4: tìm kiếm + đo ---
    KS = (1, 5, 10)
    gom: dict[str, list[float]] = {f"P@{k}": [] for k in KS}
    gom["R@10"] = []
    gom["mAP"] = []
    p5_moi_anh = np.zeros(len(anh))

    for f in range(cauhinh.SO_FOLD):
        la_tv = fold == f
        gal, tv = X[~la_tv], X[la_tv]
        nhan_gal, nhan_tv = nhan[~la_tv], nhan[la_tv]

        # Quy tắc trung thực số 1: không ảnh nào vừa ở gallery vừa ở truy vấn.
        timkiem.kiem_tra_tach_biet(
            [i for i, t in zip(ids, la_tv) if t],
            [i for i, t in zip(ids, la_tv) if not t],
        )
        # Quy tắc trung thực số 3: mean/std lấy từ gallery của CHÍNH fold này.
        tb, sd = timkiem.tham_so_chuan_hoa(gal)
        gal_z, tv_z = timkiem.chuan_hoa(gal, tb, sd), timkiem.chuan_hoa(tv, tb, sd)

        d = timkiem.khoang_cach_l2(tv_z, gal_z)
        idx_day = timkiem.xep_hang(d, d.shape[1])

        for k in KS:
            p = timkiem.precision_at_k(nhan_tv, nhan_gal, idx_day, k)
            gom[f"P@{k}"].append(timkiem.macro_theo_loai(p, nhan_tv))
            if k == 5:
                p5_moi_anh[la_tv] = p
        gom["R@10"].append(timkiem.macro_theo_loai(
            timkiem.recall_at_k(nhan_tv, nhan_gal, idx_day, 10), nhan_tv))
        gom["mAP"].append(timkiem.macro_theo_loai(
            timkiem.average_precision(nhan_tv, nhan_gal, idx_day), nhan_tv))

    nn5 = muc_ngau_nhien(nhan, fold, 5)

    print("\n" + "=" * 62)
    print("CHI SO 5-FOLD — Bo A dac trung (1) color moments Lab, 9 chieu")
    print("Trung binh macro theo loai, +- do lech chuan giua 5 fold")
    print("=" * 62)
    print(f"{'chi so':<10}{'trung binh':>14}{'do lech':>12}{'ngau nhien':>14}{'gap':>10}")
    print("-" * 62)
    for ten, gt in gom.items():
        v = np.array(gt)
        if ten == "P@5":
            print(f"{ten:<10}{v.mean():>13.1%}{v.std():>12.1%}{nn5:>13.1%}{v.mean() / nn5:>9.1f}x")
        else:
            print(f"{ten:<10}{v.mean():>13.1%}{v.std():>12.1%}{'':>14}{'':>10}")
    print("-" * 62)
    print(f"Tong truy van: {len(anh)} (moi anh lam truy van dung mot lan)")

    # P@5 theo loài, xếp từ thấp lên — loài nào đang khó nhất.
    pl = timkiem.theo_loai(p5_moi_anh, nhan)
    ten_viet = danhmuc.ten_hien_thi()
    dem = danhmuc.dem_theo_loai(anh)
    print(f"\n{'ma loai':<10}{'ten':<22}{'so anh':>8}{'P@5':>9}")
    print("-" * 49)
    for m, v in sorted(pl.items(), key=lambda kv: kv[1]):
        print(f"{m:<10}{ten_viet.get(m, ''):<22}{dem[m]:>8}{v:>8.0%}")
    print("-" * 49)

    cauhinh.KET_QUA.mkdir(parents=True, exist_ok=True)
    with (cauhinh.KET_QUA / "chi_so_mau.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["chi_so", "trung_binh", "do_lech_chuan"] +
                   [f"fold{i}" for i in range(cauhinh.SO_FOLD)])
        for ten, gt in gom.items():
            w.writerow([ten, f"{np.mean(gt):.6f}", f"{np.std(gt):.6f}"] +
                       [f"{x:.6f}" for x in gt])
        w.writerow(["P@5_ngau_nhien", f"{nn5:.6f}", "0"] + [""] * cauhinh.SO_FOLD)
    with (cauhinh.KET_QUA / "p5_theo_loai.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["ma_loai", "ten_viet", "so_anh", "p_at_5"])
        for m, v in sorted(pl.items(), key=lambda kv: kv[1]):
            w.writerow([m, ten_viet.get(m, ""), dem[m], f"{v:.6f}"])
    print(f"\nDa ghi ket qua vao {cauhinh.KET_QUA.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
