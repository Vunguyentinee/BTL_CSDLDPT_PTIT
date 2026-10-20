"""Cân bằng số ảnh giữa các loài — bước cuối trước khi chốt bộ dữ liệu.

Vì sao cần: Precision@5 tính theo từng loài chỉ so sánh được với nhau khi các
lớp có cỡ tương đương. Lớp 162 ảnh và lớp 11 ảnh cho hai con số không cùng thang
đo — lớp nhỏ chia gallery/query 80/20 chỉ còn 2 ảnh truy vấn, sai một ảnh là tụt
50%. Ma trận nhầm lẫn cũng bị lớp lớn áp đảo.

Cách làm: đặt một mức trần, loài nào vượt thì **rút ngẫu nhiên** xuống bằng trần.

Hai nguyên tắc:

*   **Rút ngẫu nhiên với seed cố định, KHÔNG chọn tay.** Chọn tay những ảnh
    "đẹp" sẽ làm bộ dữ liệu dễ hơn thực tế và thổi phồng mọi chỉ số. Cũng không
    chọn theo `do_net` hay chỉ số nào khác, vì chúng tương quan với nguồn ảnh —
    giữ toàn ảnh nét là vô tình giữ toàn ảnh Archive.
*   **Chuyển sang `work/du/`, không xóa.** Đổi mức trần thì lấy lại được, và
    phần dư vẫn dùng được làm tập truy vấn mở rộng nếu cần.

    python scripts/can_bang.py                    # xem gợi ý mức trần
    python scripts/can_bang.py --muc-tieu 60 --thu
    python scripts/can_bang.py --muc-tieu 60
    python scripts/can_bang.py --hoan-tac         # đưa hết từ work/du về
"""

from __future__ import annotations

import argparse
import csv
import os
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPECIES_CSV = ROOT / "data_meta" / "species.csv"
CHUAN_DIR = ROOT / "work" / "chuan"
DU_DIR = ROOT / "work" / "du"
SEED = 20261013          # cố định để lần chạy nào cũng ra cùng kết quả


def dem_theo_loai() -> dict[str, tuple[str, list[Path]]]:
    out: dict[str, tuple[str, list[Path]]] = {}
    with SPECIES_CSV.open(newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            if (r.get("trang_thai") or "").strip() != "da_chot":
                continue
            ma = r["ma_loai"].strip()
            d = CHUAN_DIR / ma
            if d.exists():
                out[ma] = (r.get("ten_viet", ""), sorted(d.glob("*.png")))
    return out


def goi_y(so_anh: list[int]) -> None:
    """In bảng: ứng với mỗi mức trần thì tổng còn bao nhiêu ảnh."""
    print(f"{'mức trần':>10}{'tổng ảnh':>11}{'số loài bị cắt':>17}{'ảnh bị cắt':>13}")
    print("-" * 52)
    for t in (30, 40, 50, 60, 70, 80, 100, 120):
        tong = sum(min(n, t) for n in so_anh)
        cat = sum(1 for n in so_anh if n > t)
        bo = sum(max(0, n - t) for n in so_anh)
        canh = "   <-- dưới 1000" if tong < 1000 else ""
        print(f"{t:>10}{tong:>11}{cat:>17}{bo:>13}{canh}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--muc-tieu", type=int, help="số ảnh tối đa mỗi loài")
    ap.add_argument("--thu", action="store_true", help="chỉ in ra, không di chuyển gì")
    ap.add_argument("--hoan-tac", action="store_true", help="đưa hết ảnh từ work/du về")
    args = ap.parse_args()

    if args.hoan_tac:
        n = 0
        for p in sorted(DU_DIR.rglob("*.png")) if DU_DIR.exists() else []:
            dich = CHUAN_DIR / p.parent.name / p.name
            dich.parent.mkdir(parents=True, exist_ok=True)
            if not args.thu:
                os.replace(p, dich)
            n += 1
        print(f"Đưa về {n} ảnh" + (" (chạy thử)" if args.thu else ""))
        return 0

    ds = dem_theo_loai()
    if not ds:
        sys.exit("Không thấy ảnh nào trong work/chuan")
    so_anh = [len(v[1]) for v in ds.values()]

    if not args.muc_tieu:
        print(f"Hiện có {sum(so_anh)} ảnh / {len(ds)} loài "
              f"(ít nhất {min(so_anh)}, nhiều nhất {max(so_anh)}, "
              f"chênh {max(so_anh) / max(min(so_anh), 1):.1f} lần)\n")
        goi_y(so_anh)
        print("\nChọn mức rồi chạy lại:  --muc-tieu N --thu")
        return 0

    rng = random.Random(SEED)
    t = args.muc_tieu
    print(f"{'loài':<9}{'tên':<20}{'đang có':>9}{'giữ':>6}{'chuyển sang du':>17}")
    print("-" * 62)
    tong_giu = tong_bo = 0
    for ma, (ten, ps) in sorted(ds.items()):
        if len(ps) <= t:
            tong_giu += len(ps)
            print(f"{ma:<9}{ten[:19]:<20}{len(ps):>9}{len(ps):>6}{0:>17}")
            continue
        # rút ngẫu nhiên có seed: cùng đầu vào thì cùng kết quả, tái lập được
        chon = set(rng.sample([p.name for p in ps], t))
        bo = [p for p in ps if p.name not in chon]
        if not args.thu:
            (DU_DIR / ma).mkdir(parents=True, exist_ok=True)
            for p in bo:
                os.replace(p, DU_DIR / ma / p.name)
        tong_giu += t
        tong_bo += len(bo)
        print(f"{ma:<9}{ten[:19]:<20}{len(ps):>9}{t:>6}{len(bo):>17}")
    print("-" * 62)
    print(f"{'TỔNG':<29}{sum(so_anh):>9}{tong_giu:>6}{tong_bo:>17}")
    print()
    if tong_giu < 1000:
        print(f"⚠ Chỉ còn {tong_giu} ảnh — DƯỚI mức 1000 của đề bài. Nâng mức trần lên.")
    else:
        print(f"Còn {tong_giu} ảnh, đạt yêu cầu ≥1000 của đề bài.")
    if args.thu:
        print("\n--thu: không di chuyển gì.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
