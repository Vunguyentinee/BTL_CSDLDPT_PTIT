"""Bước 3 + Bước 4 — Hoàn thiện `data_meta/species.csv`.

    Bước 3: sinh `ma_loai`, `ma_ho`, `chi` từ `ten_khoa_hoc` và `ten_ho`.
    Bước 4: tra iNaturalist để lấy `inat_taxon_id` và **đếm số ảnh ứng viên**
            của từng loài, dùng làm căn cứ loại loài không đủ ảnh.

Cách dùng:

    python scripts/build_species.py                  # làm cả bước 3 và 4
    python scripts/build_species.py --skip-inat      # chỉ bước 3 (không cần mạng)
    python scripts/build_species.py --only-inat      # chỉ bước 4
    python scripts/build_species.py --dry-run        # in ra nhưng không ghi file
    python scripts/build_species.py --refresh-inat   # tra lại cả dòng đã có taxon_id
    python scripts/build_species.py --regen-codes    # sinh lại mã đã có (xem cảnh báo)

Hai điều cần biết trước khi chạy:

*   `ma_loai` là **khóa bất biến** — nó là tên thư mục và một phần tên của hàng
    nghìn file ảnh. Vì vậy script **không bao giờ ghi đè** `ma_loai` đã có sẵn,
    trừ khi truyền `--regen-codes`. Sau khi đã thu thập ảnh thì đừng dùng cờ đó.
*   Số ảnh ứng viên chỉ đếm ảnh **research grade** (loài đã được cộng đồng
    iNaturalist xác nhận) và **có giấy phép cho phép chỉnh sửa**. Giấy phép
    `-nd` (NoDerivatives) bị loại vì pipeline có crop và tách nền, tức là tạo ra
    tác phẩm phái sinh.

Phụ thuộc: `requests` (xem `requirements.txt`). Bước 3 không cần mạng.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from species_codes import (  # noqa: E402
    RE_FAMILY_CODE,
    RE_SPECIES_CODE,
    assign_family_codes,
    assign_species_codes,
    genus_of,
)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV = ROOT / "data_meta" / "species.csv"

COLUMNS = [
    "ma_loai",
    "ten_khoa_hoc",
    "chi",
    "ma_ho",
    "ten_ho",
    "ten_viet",
    "ten_tieng_anh",
    "ten_dong_nghia",
    "fishbase_id",
    "inat_taxon_id",
    "so_anh_inat",
    "so_anh_inat_license_ok",
    "vai_tro",
    "loai_cap_voi",
    "nguoi_phu_trach",
    "trang_thai",
    "ly_do_loai",
    "ghi_chu",
]

# ---------------------------------------------------------------- iNaturalist

API = "https://api.inaturalist.org/v1"
USER_AGENT = "BTL-CSDLDPT-fish-cbir/0.1 (bai tap lon CSDL Da phuong tien)"
# Bỏ mọi giấy phép -nd: ta crop và tách nền, tức là tạo tác phẩm phái sinh.
USABLE_LICENSES = "cc0,cc-by,cc-by-nc,cc-by-sa,cc-by-nc-sa"
SLEEP_BETWEEN_CALLS = 1.1  # iNaturalist đề nghị giữ dưới ~60 lần gọi/phút
MAX_RETRIES = 3

TARGET_CANDIDATES = 100  # dưới ngưỡng này thì cảnh báo nên loại loài
TARGET_LOCKED = 20  # số loài phải chốt


def _get(session: Any, path: str, params: dict) -> dict:
    """Gọi API kèm thử lại khi đứt kết nối, bị giới hạn tần suất, hoặc lỗi server."""
    import requests

    url = API + path
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, params=params, timeout=30)
        except (requests.ConnectionError, requests.Timeout) as exc:
            # iNaturalist đôi khi đóng kết nối giữa một lượt gọi dài.
            if attempt == MAX_RETRIES:
                raise
            wait = 2**attempt
            print(f"    {type(exc).__name__} — chờ {wait}s rồi thử lại")
            time.sleep(wait)
            continue

        if resp.status_code == 200:
            return resp.json()

        if resp.status_code == 429 or resp.status_code >= 500:
            wait = float(resp.headers.get("Retry-After", 2**attempt))
            if attempt == MAX_RETRIES:
                resp.raise_for_status()
            print(f"    HTTP {resp.status_code} — chờ {wait:.0f}s rồi thử lại")
            time.sleep(wait)
            continue

        resp.raise_for_status()

    raise RuntimeError("không tới được đây")


def find_taxon(session: Any, scientific_name: str) -> tuple[dict | None, str]:
    """Tìm taxon đúng cấp loài, khớp chính xác tên khoa học.

    Trả về (taxon hoặc None, ghi chú). Không bao giờ lấy bừa kết quả đầu tiên:
    tìm theo tên rất dễ trả về chi, phân loài, hoặc loài khác gần tên.
    """
    data = _get(
        session, "/taxa", {"q": scientific_name, "rank": "species", "per_page": 10}
    )
    results = data.get("results", [])

    wanted = scientific_name.strip().lower()
    exact = [t for t in results if (t.get("name") or "").strip().lower() == wanted]

    if not exact:
        got = ", ".join((t.get("name") or "?") for t in results[:3]) or "không có"
        return None, f"iNat không có loài khớp chính xác (gần nhất: {got})"

    active = [t for t in exact if t.get("is_active", True)]
    if not active:
        return exact[0], "taxon đã bị iNat vô hiệu hóa — kiểm tra tên đồng nghĩa"

    if len(active) > 1:
        ids = ", ".join(str(t.get("id")) for t in active)
        return active[0], f"iNat có nhiều taxon cùng tên ({ids}) — kiểm tra tay"

    return active[0], ""


def count_photos(session: Any, taxon_id: int, only_usable_license: bool) -> int:
    """Đếm số quan sát research grade có ảnh của một loài."""
    params = {
        "taxon_id": taxon_id,
        "quality_grade": "research",
        "photos": "true",
        "per_page": 1,
    }
    if only_usable_license:
        params["photo_license"] = USABLE_LICENSES
    return int(_get(session, "/observations", params).get("total_results", 0))


# --------------------------------------------------------------------- bước 3


def step3_fill_codes(rows: list[dict], regen: bool) -> list[str]:
    """Điền `chi`, `ma_ho`, `ma_loai`. Không ghi đè mã cũ trừ khi `regen`."""
    problems: list[str] = []

    for i, row in enumerate(rows, start=2):  # dòng 1 là tiêu đề
        name = (row.get("ten_khoa_hoc") or "").strip()
        if not name:
            problems.append(f"LỖI dòng {i}: thiếu `ten_khoa_hoc`")
            continue
        try:
            if not (row.get("chi") or "").strip():
                row["chi"] = genus_of(name)
        except ValueError as exc:
            problems.append(f"LỖI dòng {i}: {exc}")

    usable = [r for r in rows if (r.get("ten_khoa_hoc") or "").strip()]

    # --- mã họ
    fam_names = [(r.get("ten_ho") or "").strip() for r in usable]
    if all(fam_names):
        codes, warns = assign_family_codes(fam_names)
        for row, code in zip(usable, codes):
            old = (row.get("ma_ho") or "").strip()
            if old and not regen:
                if old != code:
                    problems.append(
                        f"CẢNH BÁO {row['ten_khoa_hoc']}: `ma_ho` đang là {old!r} "
                        f"nhưng quy ước sinh ra {code!r} — giữ nguyên {old!r}"
                    )
                continue
            row["ma_ho"] = code
        problems += [f"CẢNH BÁO mã họ: {w}" for w in warns]
    else:
        missing = [
            r["ten_khoa_hoc"] for r, f in zip(usable, fam_names) if not f
        ]
        problems.append(
            "CẢNH BÁO: chưa sinh được `ma_ho` vì thiếu `ten_ho` của: "
            + ", ".join(missing[:5])
            + (" ..." if len(missing) > 5 else "")
        )

    # --- mã loài
    codes, warns = assign_species_codes([r["ten_khoa_hoc"].strip() for r in usable])
    for row, code in zip(usable, codes):
        old = (row.get("ma_loai") or "").strip()
        if old and not regen:
            if old != code:
                problems.append(
                    f"CẢNH BÁO {row['ten_khoa_hoc']}: `ma_loai` đang là {old!r} "
                    f"nhưng quy ước sinh ra {code!r} — GIỮ NGUYÊN {old!r} vì mã là "
                    f"khóa bất biến. Chỉ đổi khi chưa thu thập ảnh nào."
                )
            continue
        row["ma_loai"] = code
        print(f"  + {code:<10} {row['ten_khoa_hoc']}")
    problems += [f"CẢNH BÁO mã loài: {w}" for w in warns]

    return problems


# --------------------------------------------------------------------- bước 4


def step4_fill_inat(rows: list[dict], refresh: bool) -> list[str]:
    """Điền `inat_taxon_id`, `so_anh_inat`, `so_anh_inat_license_ok`."""
    try:
        import requests
    except ImportError:
        return [
            "LỖI: chưa cài `requests`. Chạy: pip install -r requirements.txt "
            "(hoặc dùng --skip-inat để chỉ làm bước 3)"
        ]

    problems: list[str] = []
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    def is_done(row: dict) -> bool:
        """Chỉ coi là xong khi có đủ CẢ BA trường.

        Nếu chỉ kiểm `inat_taxon_id` thì một dòng lỗi mạng giữa đường — đã lấy
        được taxon_id nhưng chưa đếm xong ảnh — sẽ bị bỏ qua ở lượt chạy sau.
        """
        return all(
            (row.get(c) or "").strip()
            for c in ("inat_taxon_id", "so_anh_inat", "so_anh_inat_license_ok")
        )

    todo = [
        r
        for r in rows
        if (r.get("ten_khoa_hoc") or "").strip() and (refresh or not is_done(r))
    ]
    if not todo:
        print("  (mọi dòng đã đủ dữ liệu iNat — dùng --refresh-inat để tra lại)")
        return problems

    print(f"  tra {len(todo)} loài trên iNaturalist (~{len(todo) * 3.3:.0f}s)")

    for row in todo:
        name = row["ten_khoa_hoc"].strip()
        try:
            taxon, note = find_taxon(session, name)
            time.sleep(SLEEP_BETWEEN_CALLS)

            if taxon is None:
                problems.append(f"CẢNH BÁO {name}: {note}")
                print(f"  ! {name:<34} không tìm thấy")
                continue

            taxon_id = int(taxon["id"])
            row["inat_taxon_id"] = str(taxon_id)

            total = count_photos(session, taxon_id, only_usable_license=False)
            time.sleep(SLEEP_BETWEEN_CALLS)
            usable = count_photos(session, taxon_id, only_usable_license=True)
            time.sleep(SLEEP_BETWEEN_CALLS)

            row["so_anh_inat"] = str(total)
            row["so_anh_inat_license_ok"] = str(usable)

            flag = "" if usable >= TARGET_CANDIDATES else "  <-- quá ít"
            print(f"  + {name:<34} id={taxon_id:<9} {usable:>6}/{total:<7}{flag}")

            if note:
                problems.append(f"CẢNH BÁO {name}: {note}")
            if usable < TARGET_CANDIDATES:
                problems.append(
                    f"CẢNH BÁO {name}: chỉ {usable} ảnh dùng được trên iNaturalist "
                    f"(ngưỡng {TARGET_CANDIDATES}) — cân nhắc loại, hoặc bù bằng "
                    f"FishBase và crawl"
                )
        except Exception as exc:  # noqa: BLE001 — một loài lỗi không được dừng cả lượt
            problems.append(f"LỖI {name}: {type(exc).__name__}: {exc}")
            print(f"  ! {name:<34} lỗi: {exc}")

    return problems


# ------------------------------------------------------------------ kiểm tra


def run_checks(rows: list[dict]) -> list[str]:
    """Bảy phép kiểm trên toàn file."""
    out: list[str] = []
    locked = [r for r in rows if (r.get("trang_thai") or "").strip() == "da_chot"]

    # 1 + 2. định dạng mã
    for r in rows:
        code = (r.get("ma_loai") or "").strip()
        if code and not RE_SPECIES_CODE.match(code):
            out.append(f"LỖI: `ma_loai` {code!r} sai định dạng (phải in hoa A-Z và 1 gạch dưới)")
        fam = (r.get("ma_ho") or "").strip()
        if fam and not RE_FAMILY_CODE.match(fam):
            out.append(f"LỖI: `ma_ho` {fam!r} sai định dạng (phải in hoa A-Z không gạch dưới)")

    # 3. trùng mã loài
    seen: dict[str, str] = {}
    for r in rows:
        code = (r.get("ma_loai") or "").strip()
        if not code:
            continue
        if code in seen:
            out.append(f"LỖI: `ma_loai` {code!r} trùng giữa {seen[code]} và {r.get('ten_khoa_hoc')}")
        seen[code] = r.get("ten_khoa_hoc", "?")

    # 4. mỗi họ tối đa 2 loài đã chốt
    per_family: dict[str, list[str]] = {}
    for r in locked:
        per_family.setdefault((r.get("ma_ho") or "").strip(), []).append(
            (r.get("ma_loai") or "?").strip()
        )
    for fam, members in per_family.items():
        if len(members) > 2:
            out.append(
                f"LỖI: họ {fam} có {len(members)} loài đã chốt ({', '.join(members)}) "
                f"— thiết kế chỉ cho phép 1 hoặc 2"
            )

    # 5. loai_cap_voi: tồn tại, cùng họ, đối xứng
    by_code = {(r.get("ma_loai") or "").strip(): r for r in rows if (r.get("ma_loai") or "").strip()}
    for r in locked:
        code = (r.get("ma_loai") or "").strip()
        partner = (r.get("loai_cap_voi") or "").strip()
        if not partner:
            if (r.get("vai_tro") or "").strip().startswith("cap_"):
                out.append(f"LỖI {code}: `vai_tro` là cặp nhưng thiếu `loai_cap_voi`")
            continue
        if partner not in by_code:
            out.append(f"LỖI {code}: `loai_cap_voi` = {partner!r} không tồn tại")
            continue
        other = by_code[partner]
        if (other.get("ma_ho") or "").strip() != (r.get("ma_ho") or "").strip():
            out.append(f"LỖI {code}: ghép cặp với {partner} nhưng khác họ")
        if (other.get("loai_cap_voi") or "").strip() != code:
            out.append(
                f"LỖI {code}: ghép cặp không đối xứng — {partner} đang trỏ tới "
                f"{other.get('loai_cap_voi')!r}"
            )

    # 6. đúng 20 loài đã chốt
    if len(locked) != TARGET_LOCKED:
        level = "CẢNH BÁO" if len(locked) < TARGET_LOCKED else "LỖI"
        out.append(f"{level}: có {len(locked)} loài `da_chot`, cần đúng {TARGET_LOCKED}")

    # 7. phân công đều
    load: dict[str, int] = {}
    for r in locked:
        who = (r.get("nguoi_phu_trach") or "").strip() or "(trống)"
        load[who] = load.get(who, 0) + 1
    if load and max(load.values()) - min(load.values()) > 1:
        detail = ", ".join(f"{k}={v}" for k, v in sorted(load.items()))
        out.append(f"CẢNH BÁO: phân công lệch quá 1 loài ({detail})")

    # loài đã chốt mà thiếu id phải tra tay
    no_fb = [(r.get("ma_loai") or "?").strip() for r in locked if not (r.get("fishbase_id") or "").strip()]
    if no_fb:
        out.append(
            f"CẢNH BÁO: {len(no_fb)} loài đã chốt còn thiếu `fishbase_id` "
            f"(tra tay trên fishbase.se): {' '.join(no_fb)}"
        )

    return out


# ------------------------------------------------------------------- vào/ra


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        sys.exit(f"Không thấy {path}. Tạo file với đúng {len(COLUMNS)} cột tiêu đề trước.")
    # utf-8-sig để Excel trên Windows không làm loạn font tiếng Việt
    with path.open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    missing = [c for c in COLUMNS if rows and c not in rows[0]]
    if missing:
        print(f"  (thêm cột còn thiếu: {', '.join(missing)})")
    return [{c: (r.get(c) or "") for c in COLUMNS} for r in rows]


def write_rows(path: Path, rows: list[dict]) -> None:
    """Ghi qua file tạm rồi thay thế, để không làm hỏng file nếu ghi dở."""
    tmp = path.with_suffix(".csv.tmp")
    with tmp.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, path)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="đường dẫn species.csv")
    ap.add_argument("--skip-inat", action="store_true", help="chỉ làm bước 3")
    ap.add_argument("--only-inat", action="store_true", help="chỉ làm bước 4")
    ap.add_argument("--refresh-inat", action="store_true", help="tra lại cả dòng đã có taxon_id")
    ap.add_argument("--regen-codes", action="store_true", help="sinh lại mã đã có — cẩn thận")
    ap.add_argument("--dry-run", action="store_true", help="không ghi file")
    args = ap.parse_args()

    rows = read_rows(args.csv)
    print(f"Đọc {len(rows)} dòng từ {args.csv}\n")
    problems: list[str] = []

    if not args.only_inat:
        print("Bước 3 — sinh mã loài và mã họ")
        if args.regen_codes:
            print("  !! --regen-codes: sẽ GHI ĐÈ mã cũ. Chỉ dùng khi chưa thu thập ảnh.")
        problems += step3_fill_codes(rows, regen=args.regen_codes)
        print()

    if not args.skip_inat:
        print("Bước 4 — tra iNaturalist")
        problems += step4_fill_inat(rows, refresh=args.refresh_inat)
        print()

    print("Kiểm tra toàn file")
    problems += run_checks(rows)

    errors = [p for p in problems if p.startswith("LỖI")]
    warns = [p for p in problems if not p.startswith("LỖI")]
    for p in warns:
        print(f"  {p}")
    for p in errors:
        print(f"  {p}")
    if not problems:
        print("  không có vấn đề nào.")
    print()

    if args.dry_run:
        print("--dry-run: không ghi file.")
    else:
        write_rows(args.csv, rows)
        print(f"Đã ghi {args.csv}")

    locked = sum(1 for r in rows if (r.get("trang_thai") or "").strip() == "da_chot")
    print(f"Tổng: {len(rows)} dòng, {locked} loài đã chốt, {len(errors)} lỗi, {len(warns)} cảnh báo.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
