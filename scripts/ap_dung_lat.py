"""Áp dụng kết quả duyệt: lật ảnh sai hướng và dọn ảnh bị loại.

Chạy sau `review_tool.py`. Hai việc:

1.  **Lật ngang** những ảnh người duyệt đánh dấu `can_lat=1`, để mọi con cá cùng
    quay đầu sang trái như đề bài yêu cầu.
2.  **Chuyển ảnh bị loại** sang `work/loai/<ma_loai>/` thay vì xóa, để còn đối
    chiếu lại và còn tính được tỉ lệ đạt chuẩn theo nguồn cho báo cáo.

Lật ảnh PNG đã chuẩn hóa là phép **không mất mát và không lấy mẫu lại** — chỉ đổi
chỗ các pixel. Nhờ vậy không phải chạy lại `rembg` (vốn mất ~45 phút cho cả bộ),
và chất lượng kết cấu không suy giảm thêm lần nào.

    python scripts/ap_dung_lat.py                 # mọi loài đã có file duyệt
    python scripts/ap_dung_lat.py --loai CYP_CAR
    python scripts/ap_dung_lat.py --thu           # chỉ in ra, không đổi gì
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
CHUAN_DIR = ROOT / "work" / "chuan"
LOAI_DIR = ROOT / "work" / "loai"
REVIEW_DIR = ROOT / "data_meta" / "review"

# Đưa tất cả về **đầu bên trái, lưng ở trên**.
#
# Người duyệt ghi hai thứ: `xoay` (0/90/180/270) và `lat_ngang` (0/1). Hai cái
# đó sinh ra đủ 8 phép đối xứng của hình vuông, nên sửa được mọi tư thế sai —
# kể cả ảnh bị bước chuẩn hóa bỏ qua xoay vì bóng cá quá tròn.
#
# Mọi phép đều chỉ ĐỔI CHỖ pixel, không nội suy: ảnh vuông nên xoay 90° cũng
# không mất mát. Nhờ vậy không làm nhòe thêm kết cấu và không phải chạy lại rembg.
PHEP = {
    "ngang": Image.Transpose.FLIP_LEFT_RIGHT,   # đầu phải, lưng trên
    "doc": Image.Transpose.FLIP_TOP_BOTTOM,     # đầu trái, lưng dưới
    "180": Image.Transpose.ROTATE_180,          # đầu phải, lưng dưới
}


def xu_ly_mot_loai(ma_loai: str, thu: bool) -> tuple[int, int, int]:
    f = REVIEW_DIR / f"{ma_loai}.r1.csv"
    if not f.exists():
        return 0, 0, 0
    with f.open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))

    thu_muc = CHUAN_DIR / ma_loai
    meta_path = thu_muc / "_meta.jsonl"

    # Nạp metadata một lần, tra theo tên ảnh. Dấu `da_lat_theo_duyet` là thứ giữ
    # cho thao tác này **lặp lại được**: thiếu nó thì chạy lần hai sẽ lật ảnh
    # ngược về chỗ cũ, mà chạy lại là chuyện thường vì người duyệt sửa dần.
    meta_rows: list[dict] = []
    theo_ten: dict[str, dict] = {}
    if meta_path.exists():
        for l in meta_path.read_text(encoding="utf-8").splitlines():
            if l.strip():
                r = json.loads(l)
                meta_rows.append(r)
                theo_ten[Path(r.get("ten_file_ra", "")).stem] = r

    da_lat = da_loai = giu = bo_qua = dua_ve = 0
    meta_doi = False

    for r in rows:
        stem = r["image_id"]
        p = thu_muc / f"{stem}.png"
        if r["quyet_dinh"] == "loai":
            if p.exists():
                da_loai += 1
                if not thu:
                    dich = LOAI_DIR / ma_loai
                    dich.mkdir(parents=True, exist_ok=True)
                    # os.replace thay cho Path.rename: trên Windows, rename báo
                    # FileExistsError khi đích đã tồn tại, còn trên Linux thì ghi
                    # đè. Chuyện đích đã tồn tại là có thật khi một ảnh bị sinh
                    # lại trong lúc bản cũ vẫn nằm ở work/loai.
                    os.replace(p, dich / p.name)
            continue

        giu += 1
        # Đổi ý từ `loại` sang `nhận`: ảnh đang nằm ở work/loai từ lượt chạy
        # trước, phải đưa về. Thiếu nhánh này thì mỗi lần người duyệt bấm Z sửa
        # lại quyết định là mất luôn một ảnh khỏi bộ dữ liệu.
        bi_loai_nham = LOAI_DIR / ma_loai / f"{stem}.png"
        if not p.exists() and bi_loai_nham.exists():
            dua_ve += 1
            if not thu:
                os.replace(bi_loai_nham, p)

        bien_doi = (r.get("bien_doi") or "").strip()
        if not bien_doi or not p.exists():
            continue
        if theo_ten.get(stem, {}).get("da_bien_doi"):
            bo_qua += 1       # đã xử lý ở lượt trước
            continue

        da_lat += 1
        if not thu:
            with Image.open(p) as im:
                im.transpose(PHEP[bien_doi]).save(p, "PNG")
            if stem in theo_ten:
                theo_ten[stem].update(
                    da_bien_doi=bien_doi,
                    tu_the_chuan="dau_trai_lung_tren",
                    huong="L", huong_nguon="review",
                )
                meta_doi = True

    if meta_doi and not thu:
        meta_path.write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in meta_rows), encoding="utf-8"
        )
    return giu, da_lat, da_loai, dua_ve


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--loai", nargs="*")
    ap.add_argument("--thu", action="store_true", help="chỉ in ra, không thay đổi gì")
    args = ap.parse_args()

    ds = args.loai or sorted(p.stem.replace(".r1", "") for p in REVIEW_DIR.glob("*.r1.csv"))
    if not ds:
        sys.exit("Chưa có file duyệt nào trong data_meta/review/")

    tong = [0, 0, 0, 0]
    print(f"{'loai':<9}{'giu':>7}{'lat/xoay':>10}{'-> work/loai':>14}{'dua ve lai':>12}")
    print("-" * 53)
    for ma in ds:
        ma = ma.upper()
        giu, lat, loai, ve = xu_ly_mot_loai(ma, args.thu)
        if giu or loai or ve:
            print(f"{ma:<9}{giu:>7}{lat:>10}{loai:>14}{ve:>12}")
        for i, v in enumerate((giu, lat, loai, ve)):
            tong[i] += v
    print("-" * 53)
    print(f"{'TONG':<9}{tong[0]:>7}{tong[1]:>10}{tong[2]:>14}{tong[3]:>12}")
    if args.thu:
        print("\n--thu: không thay đổi gì.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
