"""Chạy toàn bộ self-test của package fishcbir.

Dự án không dùng pytest (xem requirements.txt), mà theo quy ước có sẵn trong
scripts/species_codes.py: mỗi module có hàm _selftest() dùng assert. File này
gom chúng lại thành một lệnh:

    python scripts/kiem_tra.py          # chỉ test đơn vị, không đụng đĩa
    python scripts/kiem_tra.py --day-du # thêm test đối chiếu dữ liệu thật

Test đơn vị dùng dữ liệu tự sinh nên chạy trong vài phần nghìn giây và không
phụ thuộc work/chuan. Test --day-du mới đọc ảnh thật.
"""

from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass


def chay(ten: str, ham) -> bool:
    try:
        ham()
    except Exception:
        print(f"  THAT BAI  {ten}")
        traceback.print_exc()
        return False
    print(f"  ok        {ten}")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Chạy self-test của fishcbir")
    ap.add_argument("--day-du", action="store_true",
                    help="chạy thêm test đối chiếu dữ liệu thật trên đĩa")
    a = ap.parse_args()

    from fishcbir import cauhinh, chia_fold, danhgia, danhmuc, fisher, timkiem
    from fishcbir.dactrung import mau, sau

    bo = [
        ("cauhinh", cauhinh._selftest),
        ("danhmuc", danhmuc._selftest),
        ("chia_fold", chia_fold._selftest),
        ("dactrung.mau", mau._selftest),
        ("dactrung.sau", sau._selftest),
        ("timkiem", timkiem._selftest),
        ("danhgia", danhgia._selftest),
        ("fisher", fisher._selftest),
    ]
    if a.day_du:
        bo += [
            ("danhmuc [dữ liệu thật]", danhmuc._selftest_du_lieu_that),
            ("chia_fold [dữ liệu thật]", chia_fold._selftest_du_lieu_that),
            ("dactrung.sau [tải mô hình]", sau._selftest_mo_hinh),
        ]

    print(f"Chạy {len(bo)} bộ self-test\n")
    ok = sum(chay(t, f) for t, f in bo)
    print(f"\n{ok}/{len(bo)} bộ đạt")
    return 0 if ok == len(bo) else 1


if __name__ == "__main__":
    sys.exit(main())
