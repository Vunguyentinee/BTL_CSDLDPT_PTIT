"""Giá trị thông tin của các bộ đặc trưng — bảng Fisher ba cột (việc T17).

    python scripts/gia_tri_thong_tin.py

Cần chạy scripts/danh_gia.py trước để có cache đặc trưng trong ket_qua/.

Mọi phép tính chạy trên **mẫu cân bằng** 19 ảnh mỗi loài (bằng cỡ lớp nhỏ
nhất là cá lóc). Nếu để nguyên 162 ảnh cá dĩa cạnh 19 ảnh cá lóc thì phương
sai liên lớp phản ánh kích thước lớp nhiều hơn phản ánh khác biệt loài.
"""

from __future__ import annotations

import csv
import sys
from itertools import combinations
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

from fishcbir import cauhinh, danhmuc, fisher  # noqa: E402
from fishcbir.dactrung import mau  # noqa: E402

sys.path.insert(0, str(ROOT / "scripts"))
import bo_c  # noqa: E402


def nap_khoi(anh: list[danhmuc.Anh]) -> dict[str, tuple[np.ndarray, list[str]]]:
    """Ma trận đặc trưng + tên chiều cho từng khối."""
    ids = [a.image_id for a in anh]
    ra: dict[str, tuple[np.ndarray, list[str]]] = {}

    for ten, ten_chieu in (("mau", mau.TEN), ("sau", None)):
        c = cauhinh.KET_QUA / f"dactrung_{ten}.npz"
        if not c.exists():
            print(f"THIEU {c.relative_to(ROOT)} — chay scripts/danh_gia.py truoc", file=sys.stderr)
            continue
        d = np.load(c, allow_pickle=False)
        if list(d["image_id"]) != ids:
            print(f"CANH BAO: cache {ten} khong khop danh sach anh", file=sys.stderr)
            continue
        X = d["X"]
        ra[ten] = (X, ten_chieu or [f"d{i:03d}" for i in range(X.shape[1])])

    # Bộ C: mỗi ảnh nhận vector của LOÀI nó thuộc về.
    bang = bo_c.doc_bo_c()
    ten_c = [f"{t}={v}" if t not in bo_c.THU_TU else t
             for t in bo_c.THUOC_TINH
             for v in (bo_c.TU_VUNG[t] if t not in bo_c.THU_TU else [None])]
    vec = {m: np.array(bo_c.ma_hoa(h)) for m, h in bang.items()}
    ra["ngu_nghia"] = (np.array([vec[a.ma_loai] for a in anh]), ten_c)
    return ra


def main() -> int:
    anh = danhmuc.liet_ke_anh()
    nhan = np.array([a.ma_loai for a in anh])
    khoi = nap_khoi(anh)
    if "mau" not in khoi:
        return 1

    idx = fisher.mau_can_bang(nhan)
    nhan_cb = nhan[idx]
    n_moi_loai = int((nhan_cb == nhan_cb[0]).sum())
    print(f"Mau can bang: {len(idx)} anh = {len(np.unique(nhan_cb))} loai x {n_moi_loai} anh\n")

    # ---------- bảng gộp theo khối ----------
    print("=" * 86)
    print("GIA TRI THONG TIN THEO KHOI")
    print("=" * 86)
    K_CHUNG = min(X.shape[1] for X, _ in khoi.values())
    print(f"{'khoi':<14}{'chieu':>7}{'eta2 TB':>10}{f'eta2 top-{K_CHUNG}':>12}"
          f"{'eta2 max':>10}{'Fisher max':>12}{'chieu manh':>12}")
    print("-" * 86)
    gop = {}
    for ten, (X, _) in khoi.items():
        k = fisher.fisher_khoi(X[idx], nhan_cb)
        gop[ten] = k
        t = fisher.eta2_top(X[idx], nhan_cb, K_CHUNG)
        k["eta2_top_chung"] = t
        print(f"{ten:<14}{k['so_chieu']:>7}{k['eta2_tb']:>10.3f}{t:>12.3f}"
              f"{k['eta2_cao_nhat']:>10.3f}{k['fisher_cao_nhat']:>12.1f}"
              f"{k['so_chieu_manh']:>7}/{k['so_chieu']:<4}")
    print("-" * 86)
    print("eta2 = ti le phuong sai do LOAI giai thich, trong [0;1]. Bat bien thang do.")
    print(f"eta2 top-{K_CHUNG} = trung binh {K_CHUNG} chieu manh nhat. DAY MOI LA COT DE SO")
    print("   GIUA CAC KHOI: trung binh toan bo bi loang khi khoi co nhieu chieu.")
    print("chieu manh = so chieu co ti so Fisher >= 1 (lien lop vuot noi lop).")
    print("LUU Y: khoi ngu_nghia gan theo LOAI nen phuong sai noi lop = 0 => eta2 = 1")
    print("       theo dinh nghia. Day la he qua cua cach gan, khong phai thanh tich.\n")

    # ---------- Bộ A①: bảng ba cột đầy đủ ----------
    X, ten_chieu = khoi["mau"]
    f = fisher.fisher_tung_chieu(X[idx], nhan_cb)
    e = fisher.eta_binh_phuong(X[idx], nhan_cb)
    print("=" * 74)
    print("BO A (1) COLOR MOMENTS — BANG BA COT, DU CA 9 CHIEU")
    print("=" * 74)
    print(f"{'chieu':<10}{'phuong sai NOI lop':>22}{'LIEN lop':>14}{'ti so':>10}{'eta2':>10}")
    print("-" * 74)
    for j in np.argsort(-f["ti_so"]):
        print(f"{ten_chieu[j]:<10}{f['noi_lop'][j]:>22.2f}{f['lien_lop'][j]:>14.2f}"
              f"{f['ti_so'][j]:>10.2f}{e[j]:>10.3f}")
    print("-" * 74)
    print("Noi lop THAP = dac trung tim TUONG DONG (anh cung loai tum chat)")
    print("Lien lop CAO = dac trung tim KHAC BIET (cac loai tach xa nhau)\n")

    # ---------- Bộ B: 10 chiều mạnh nhất ----------
    if "sau" in khoi:
        Xs, _ = khoi["sau"]
        fs = fisher.fisher_tung_chieu(Xs[idx], nhan_cb)
        es = fisher.eta_binh_phuong(Xs[idx], nhan_cb)
        top = np.argsort(-fs["ti_so"])[:10]
        print("=" * 74)
        print("BO B RESNET18 — 10 CHIEU MANH NHAT trong 512")
        print("=" * 74)
        print(f"{'chieu':<10}{'phuong sai NOI lop':>22}{'LIEN lop':>14}{'ti so':>10}{'eta2':>10}")
        print("-" * 74)
        for j in top:
            print(f"d{j:<9}{fs['noi_lop'][j]:>22.5f}{fs['lien_lop'][j]:>14.5f}"
                  f"{fs['ti_so'][j]:>10.2f}{es[j]:>10.3f}")
        print("-" * 74)
        q = np.percentile(fs["ti_so"], [25, 50, 75, 95])
        print(f"Phan vi ti so Fisher tren 512 chieu: "
              f"25%={q[0]:.2f}  50%={q[1]:.2f}  75%={q[2]:.2f}  95%={q[3]:.2f}")
        print(f"So chieu gan nhu vo dung (ti so < 0,1): "
              f"{int((fs['ti_so'] < 0.1).sum())}/512\n")

    # ---------- theo cặp loài cùng họ ----------
    ho = danhmuc.ho_cua_loai()
    cap = [(a, b) for a, b in combinations(sorted(np.unique(nhan)), 2) if ho[a] == ho[b]]
    cot = [t for t in ("mau", "sau") if t in khoi]
    print("=" * 78)
    print(f"CAC CAP LOAI CUNG HO — eta2 top-{K_CHUNG} cua tung khoi (cao = tach duoc)")
    print("=" * 78)
    print(f"{'ho':<7}{'loai A':<10}{'loai B':<10}" + "".join(f"{c:>12}" for c in cot) +
          f"{'chenh':>10}")
    print("-" * 78)
    hang_cap = []
    for a, b in sorted(cap, key=lambda p: ho[p[0]]):
        v = [fisher.fisher_cap(khoi[c][0][idx], nhan_cb, a, b, k=K_CHUNG) for c in cot]
        hang_cap.append((ho[a], a, b, v))
        d = f"{ho[a]:<7}{a:<10}{b:<10}" + "".join(f"{x:>12.3f}" for x in v)
        if len(v) == 2:
            d += f"{v[1] - v[0]:>+10.3f}"
        print(d)
    print("-" * 78)

    # ---------- ghi file ----------
    cauhinh.KET_QUA.mkdir(parents=True, exist_ok=True)
    with (cauhinh.KET_QUA / "fisher_khoi.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["khoi", "so_chieu", "eta2_tb", "eta2_top_chung", "eta2_cao_nhat",
                    "fisher_trung_vi", "fisher_cao_nhat", "so_chieu_manh"])
        for t, k in gop.items():
            w.writerow([t, k["so_chieu"], f"{k['eta2_tb']:.6f}",
                        f"{k['eta2_top_chung']:.6f}", f"{k['eta2_cao_nhat']:.6f}",
                        f"{k['fisher_trung_vi']:.6f}", f"{k['fisher_cao_nhat']:.6f}",
                        k["so_chieu_manh"]])
    with (cauhinh.KET_QUA / "fisher_bo_a1.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["chieu", "phuong_sai_noi_lop", "phuong_sai_lien_lop", "ti_so_fisher", "eta2"])
        for j in np.argsort(-f["ti_so"]):
            w.writerow([ten_chieu[j], f"{f['noi_lop'][j]:.6f}", f"{f['lien_lop'][j]:.6f}",
                        f"{f['ti_so'][j]:.6f}", f"{e[j]:.6f}"])
    with (cauhinh.KET_QUA / "fisher_cap_cung_ho.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["ma_ho", "loai_a", "loai_b"] + [f"eta2_top{K_CHUNG}_{c}" for c in cot])
        for h, a, b, v in hang_cap:
            w.writerow([h, a, b] + [f"{x:.6f}" for x in v])
    print(f"\nDa ghi 3 file vao {cauhinh.KET_QUA.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
