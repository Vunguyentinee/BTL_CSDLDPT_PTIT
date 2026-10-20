"""Chạy toàn tuyến và so sánh các khối đặc trưng.

    python scripts/danh_gia.py                 # cả Bộ A① và Bộ B
    python scripts/danh_gia.py --bo mau        # chỉ color moments
    python scripts/danh_gia.py --trich-lai     # bỏ cache, trích lại từ ảnh

Khối "mau"  = Bộ A đặc trưng ① color moments Lab, 9 chiều, L2 sau z-score.
Khối "sau"  = Bộ B ResNet18 512 chiều, cosine, không z-score (đã chuẩn hóa L2).
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

from fishcbir import cauhinh, chia_fold, danhgia, danhmuc  # noqa: E402
from fishcbir.dactrung import mau, sau  # noqa: E402

# Mỗi khối: (nhãn in ra, module, độ đo, có z-score không)
KHOI = {
    "mau": ("Bộ A① color moments Lab 9 chiều", mau, "l2", True),
    "sau": ("Bộ B ResNet18 512 chiều", sau, "cosine", False),
}


def cache_cua(ten: str) -> Path:
    return cauhinh.KET_QUA / f"dactrung_{ten}.npz"


def trich_tat_ca(ten: str, anh: list[danhmuc.Anh], trich_lai: bool) -> np.ndarray:
    ids = [a.image_id for a in anh]
    c = cache_cua(ten)
    if c.exists() and not trich_lai:
        d = np.load(c, allow_pickle=False)
        if list(d["image_id"]) == ids:
            print(f"  dùng lại {c.relative_to(ROOT)}")
            return d["X"]
        print("  cache không khớp danh sách ảnh — trích lại")

    mo_dun = KHOI[ten][1]
    print(f"  trích {len(anh)} ảnh...")
    t0 = time.time()
    if ten == "sau":
        # Trích theo lô để tận dụng phép nhân ma trận; nạp ảnh theo từng khúc
        # để không giữ cả 1.085 ảnh 384x384 trong RAM cùng lúc.
        X = np.empty((len(anh), mo_dun.SO_CHIEU), np.float32)
        KHUC = 64
        for i in range(0, len(anh), KHUC):
            lo = [danhmuc.nap_anh(a.duong_dan)[0] for a in anh[i:i + KHUC]]
            X[i:i + len(lo)] = mo_dun.trich_lo(lo)
            print(f"    {min(i + KHUC, len(anh))}/{len(anh)}")
    else:
        X = np.empty((len(anh), mo_dun.SO_CHIEU), np.float64)
        for i, a in enumerate(anh):
            rgb, mask = danhmuc.nap_anh(a.duong_dan)
            X[i] = mo_dun.trich(rgb, mask)
            if (i + 1) % 400 == 0:
                print(f"    {i + 1}/{len(anh)}")
    giay = time.time() - t0
    print(f"  xong {giay:.1f}s ({giay / len(anh) * 1000:.1f} ms/ảnh)")

    if not np.all(np.isfinite(X)):
        raise SystemExit(f"LỖI: đặc trưng {ten} có NaN hoặc vô cực")
    c.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(c, X=X, image_id=np.array(ids))
    return X


def main() -> int:
    ap = argparse.ArgumentParser(description="Đánh giá 5-fold các khối đặc trưng")
    ap.add_argument("--bo", nargs="*", choices=list(KHOI), default=list(KHOI))
    ap.add_argument("--trich-lai", action="store_true")
    a = ap.parse_args()

    anh = danhmuc.liet_ke_anh()
    f_map = chia_fold.chia(anh)
    chia_fold.ghi_csv(cauhinh.FOLDS_CSV, anh, f_map)
    nhan = np.array([x.ma_loai for x in anh])
    fold = np.array([f_map[x.image_id] for x in anh])
    ids = [x.image_id for x in anh]
    print(f"{len(anh)} ảnh / {len(set(nhan))} loài / 5 fold "
          f"{[int((fold == k).sum()) for k in range(cauhinh.SO_FOLD)]}")

    nn = danhgia.muc_ngau_nhien(nhan, fold)
    kq: dict[str, dict] = {}
    for ten in a.bo:
        nhan_in, _, do_do, zs = KHOI[ten]
        print(f"\n[{ten}] {nhan_in}")
        X = trich_tat_ca(ten, anh, a.trich_lai)
        kq[ten] = danhgia.danh_gia_5fold(X, nhan, fold, ids, do_do=do_do, z_score=zs)
        kq[ten]["nhan_in"] = nhan_in
        kq[ten]["so_chieu"] = X.shape[1]

    # --- bảng so sánh ---
    print("\n" + "=" * 78)
    print("SO SANH CAC KHOI DAC TRUNG — 5-fold, 1.085 truy van, trung binh macro")
    print("=" * 78)
    cot = list(a.bo)
    print(f"{'chi so':<12}" + "".join(f"{c:>20}" for c in cot) + f"{'ngau nhien':>14}")
    print(f"{'':12}" + "".join(f"{kq[c]['so_chieu']:>17} chieu" for c in cot))
    print("-" * 78)
    for ten_cs in ("P@1", "P@5", "P@10", "R@10", "mAP"):
        d = f"{ten_cs:<12}"
        for c in cot:
            tb, sd = kq[c]["chi_so"][ten_cs]
            d += f"{tb:>13.1%} ±{sd:>4.1%}"
        d += f"{nn:>13.1%}" if ten_cs == "P@5" else f"{'':>14}"
        print(d)
    print("-" * 78)
    d = f"{'top-1 acc':<12}"
    for c in cot:
        d += f"{kq[c]['do_chinh_xac_top1']:>19.1%}"
    print(d)
    print("=" * 78)

    if len(cot) == 2:
        a5, b5 = (kq[c]["chi_so"]["P@5"][0] for c in cot)
        print(f"\nP@5: {cot[1]} / {cot[0]} = {b5 / a5:.2f} lan  "
              f"(chenh {b5 - a5:+.1%} diem)")

    # --- P@5 theo loài, đặt cạnh nhau ---
    ten_viet = danhmuc.ten_hien_thi()
    dem = danhmuc.dem_theo_loai(anh)
    from fishcbir.timkiem import theo_loai
    bang = {c: theo_loai(kq[c]["p5_moi_anh"], nhan) for c in cot}
    sap = sorted(dem, key=lambda m: bang[cot[-1]][m])
    print(f"\n{'ma loai':<10}{'ten':<22}{'anh':>5}" +
          "".join(f"{c:>10}" for c in cot) + (f"{'chenh':>9}" if len(cot) == 2 else ""))
    print("-" * (37 + 10 * len(cot) + (9 if len(cot) == 2 else 0)))
    for m in sap:
        d = f"{m:<10}{ten_viet.get(m, ''):<22}{dem[m]:>5}"
        d += "".join(f"{bang[c][m]:>10.0%}" for c in cot)
        if len(cot) == 2:
            d += f"{bang[cot[1]][m] - bang[cot[0]][m]:>+9.0%}"
        print(d)
    print("-" * (37 + 10 * len(cot) + (9 if len(cot) == 2 else 0)))

    # --- ghi file ---
    cauhinh.KET_QUA.mkdir(parents=True, exist_ok=True)
    with (cauhinh.KET_QUA / "chi_so.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["khoi", "so_chieu", "chi_so", "trung_binh", "do_lech_chuan"] +
                   [f"fold{i}" for i in range(cauhinh.SO_FOLD)])
        for c in cot:
            for ten_cs, v in kq[c]["theo_fold"].items():
                w.writerow([c, kq[c]["so_chieu"], ten_cs, f"{np.mean(v):.6f}",
                            f"{np.std(v):.6f}"] + [f"{x:.6f}" for x in v])
            w.writerow([c, kq[c]["so_chieu"], "top1_acc",
                        f"{kq[c]['do_chinh_xac_top1']:.6f}", "", *[""] * cauhinh.SO_FOLD])
        w.writerow(["-", "-", "P@5_ngau_nhien", f"{nn:.6f}", "", *[""] * cauhinh.SO_FOLD])
    with (cauhinh.KET_QUA / "p5_theo_loai.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["ma_loai", "ten_viet", "so_anh"] + [f"p5_{c}" for c in cot])
        for m in sap:
            w.writerow([m, ten_viet.get(m, ""), dem[m]] + [f"{bang[c][m]:.6f}" for c in cot])
    print(f"\nDa ghi {cauhinh.KET_QUA.relative_to(ROOT)}/chi_so.csv va p5_theo_loai.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
