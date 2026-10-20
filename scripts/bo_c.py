"""Bộ C — thuộc tính ngữ nghĩa gán theo LOÀI (không theo từng ảnh).

Mục 2 của đề yêu cầu "xây bộ thuộc tính nhận diện" và trình bày "giá trị
thông tin" của chúng. Bộ A (501 chiều cổ điển) và Bộ B (512 chiều ResNet18)
đều học từ điểm ảnh. Bộ C là bộ duy nhất do người mô tả, nên nó trả lời được
hai thứ hai bộ kia không trả lời được:

  1. Mục 1 của đề đòi "mô tả điểm giống và khác nhau" giữa các loài — bảng
     này CHÍNH LÀ bản mô tả đó, ở dạng máy đọc được.
  2. Giá trị thông tin của một đặc trưng do người chọn đo được bằng entropy
     và bằng số cặp loài mà nó tách được, không cần chạy mô hình nào.

Gán theo loài chứ không theo ảnh là có chủ đích: 10 thuộc tính này là tính
trạng của loài (tra từ trang loài FishBase), không phải thuộc tính của một
tấm ảnh cụ thể. Hệ quả phải ghi rõ trong phần hạn chế: Bộ C KHÔNG dùng được
để truy vấn ảnh loài ngoài CSDL, vì ảnh mới không có nhãn loài để tra bảng.
Nó dùng để phân tích giá trị thông tin và để giải thích kết quả, không phải
để tìm kiếm.

Cách dùng:
    python scripts/bo_c.py --kiem-tra      # kiểm bảng + in báo cáo giá trị thông tin
    python scripts/bo_c.py                 # chạy self-test
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

# Console Windows mặc định không phải UTF-8, thông báo lỗi tiếng Việt sẽ thành rác.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

ROOT = Path(__file__).resolve().parent.parent
SPECIES_CSV = ROOT / "data_meta" / "species.csv"
BO_C_CSV = ROOT / "data_meta" / "thuoc_tinh_ngu_nghia.csv"

# --------------------------------------------------------------- từ vựng

# Từ vựng có kiểm soát. Thứ tự trong danh sách là thứ tự dùng để mã hóa, nên
# với các thuộc tính CÓ THỨ TỰ (xem THU_TU) phải xếp từ nhỏ đến lớn.
TU_VUNG: dict[str, list[str]] = {
    # hình dáng tổng thể của thân
    "dang_than": ["thoi", "det_cao", "det_tron", "det_dai", "tru_dai"],
    # tỉ lệ dài:cao — rat_cao <1,5 · cao 1,5-2,5 · trung_binh 2,5-3,5 · dai 3,5-5 · rat_dai >5
    "ti_le_dai_cao": ["rat_cao", "cao", "trung_binh", "dai", "rat_dai"],
    "mau_nen": ["bac", "vang", "cam", "do", "nau", "xanh_luc", "xanh_lam", "den", "da_mau"],
    # vach_dung = sọc thẳng đứng · dai_ngang = dải chạy dọc thân · van_luoi = vân mắt lưới
    "soc": ["khong", "vach_dung", "dai_ngang", "van_luoi"],
    "cham": ["khong", "thua", "day", "dom_mat"],
    "tuong_phan_lung_bung": ["yeu", "vua", "manh"],
    "dang_duoi": ["chia_sau", "chia_nhe", "cat_bang", "tron", "xoe_dai"],
    # co_vay_mo = có vây mỡ (adipose fin) — họ cá hồi và họ cá tra đều có
    "vay_lung": ["ngan", "dai_lien", "gai_cung", "co_vay_mo"],
    # kich_thuoc theo chiều dài tối đa — rat_nho <10cm · nho 10-30 · trung_binh 30-60
    # · lon 60-120 · rat_lon >120
    "kich_thuoc": ["rat_nho", "nho", "trung_binh", "lon", "rat_lon"],
    "moi_truong": ["nuoc_ngot", "nuoc_lo", "nuoc_man"],
}

# Thuộc tính có thứ tự: mã hóa thành MỘT số đã chuẩn hóa về [0,1] thay vì
# one-hot. Lý do: one-hot coi "rat_nho" và "rat_lon" cách nhau đúng bằng
# "rat_nho" và "nho", mà thực tế không phải vậy.
THU_TU = {"ti_le_dai_cao", "tuong_phan_lung_bung", "kich_thuoc", "moi_truong"}

THUOC_TINH = list(TU_VUNG)
SO_CHIEU = sum(1 if t in THU_TU else len(TU_VUNG[t]) for t in THUOC_TINH)


# ------------------------------------------------------------ đọc dữ liệu


def loai_da_chot(path: Path = SPECIES_CSV) -> list[str]:
    """Danh sách mã loài có trang_thai=da_chot, giữ đúng thứ tự trong file."""
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [d["ma_loai"] for d in csv.DictReader(f) if d["trang_thai"] == "da_chot"]


def ho_cua_loai(path: Path = SPECIES_CSV) -> dict[str, str]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return {d["ma_loai"]: d["ma_ho"] for d in csv.DictReader(f)}


def doc_bo_c(path: Path = BO_C_CSV) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return {d["ma_loai"]: {t: d[t] for t in THUOC_TINH} for d in csv.DictReader(f)}


# -------------------------------------------------------------- kiểm tra


def kiem_tra(bang: dict[str, dict[str, str]], ma_chot: list[str]) -> list[str]:
    """Trả về danh sách lỗi. Rỗng nghĩa là bảng dùng được.

    Bốn điều phải đúng. Ba điều đầu là vệ sinh dữ liệu. Điều thứ tư mới là
    điều đáng kiểm: nếu hai loài có vector thuộc tính y hệt nhau thì Bộ C
    không thể tách chúng, và phải biết điều đó TRƯỚC khi đem đi phân tích.
    """
    loi: list[str] = []

    thieu = [m for m in ma_chot if m not in bang]
    if thieu:
        loi.append(f"thiếu dòng cho loài: {', '.join(thieu)}")
    la = [m for m in bang if m not in ma_chot]
    if la:
        loi.append(f"có dòng cho loài không ở trạng thái da_chot: {', '.join(la)}")

    for ma, hang in sorted(bang.items()):
        for t in THUOC_TINH:
            gt = (hang.get(t) or "").strip()
            if not gt:
                loi.append(f"{ma}.{t} bỏ trống")
            elif gt not in TU_VUNG[t]:
                loi.append(f"{ma}.{t} = {gt!r} không có trong từ vựng {TU_VUNG[t]}")

    nhom: dict[tuple[str, ...], list[str]] = {}
    for ma, hang in bang.items():
        nhom.setdefault(tuple(hang[t] for t in THUOC_TINH), []).append(ma)
    for ma_list in nhom.values():
        if len(ma_list) > 1:
            loi.append(f"các loài trùng hoàn toàn 10 thuộc tính: {', '.join(sorted(ma_list))}")

    return loi


# -------------------------------------------------------------- mã hóa


def ma_hoa(hang: dict[str, str]) -> list[float]:
    """Một hàng thuộc tính → vector số. Nominal thành one-hot, ordinal thành 1 số."""
    v: list[float] = []
    for t in THUOC_TINH:
        tv = TU_VUNG[t]
        i = tv.index(hang[t])
        if t in THU_TU:
            v.append(i / (len(tv) - 1) if len(tv) > 1 else 0.0)
        else:
            v.extend(1.0 if j == i else 0.0 for j in range(len(tv)))
    return v


# ------------------------------------------------- giá trị thông tin


def entropy(gia_tri: list[str]) -> float:
    """Entropy Shannon theo bit. 0 nghĩa là mọi loài giống nhau → vô dụng."""
    n = len(gia_tri)
    if n == 0:
        return 0.0
    return -sum((c / n) * math.log2(c / n) for c in Counter(gia_tri).values())


def so_cap_tach_duoc(bang: dict[str, dict[str, str]], t: str) -> int:
    """Số cặp loài mà thuộc tính này một mình đã phân biệt được."""
    mas = sorted(bang)
    return sum(1 for a, b in combinations(mas, 2) if bang[a][t] != bang[b][t])


def bao_cao(bang: dict[str, dict[str, str]], ho: dict[str, str]) -> None:
    mas = sorted(bang)
    tong_cap = len(mas) * (len(mas) - 1) // 2

    print(f"\nBộ C — {len(mas)} loài x {len(THUOC_TINH)} thuộc tính "
          f"-> {SO_CHIEU} chiều sau mã hóa")
    print(f"(ordinal {len(THU_TU)} thuộc tính mã hóa thành 1 số, "
          f"nominal {len(THUOC_TINH) - len(THU_TU)} thuộc tính one-hot)\n")

    print("GIA TRI THONG TIN TUNG THUOC TINH")
    print(f"{'thuoc tinh':<24}{'gia tri dung':>16}{'entropy (bit)':>15}"
          f"{'cap tach duoc':>16}{'ti le':>8}")
    print("-" * 79)
    hang_bc = []
    for t in THUOC_TINH:
        gt = [bang[m][t] for m in mas]
        e = entropy(gt)
        c = so_cap_tach_duoc(bang, t)
        hang_bc.append((e, c, t, len(set(gt))))
        print(f"{t:<24}{len(set(gt)):>7}/{len(TU_VUNG[t]):<8}{e:>15.2f}"
              f"{c:>12}/{tong_cap:<4}{c / tong_cap:>7.0%}")
    print("-" * 79)
    e_max = math.log2(len(mas))
    print(f"entropy toi da co the (moi loai mot gia tri rieng) = {e_max:.2f} bit\n")

    xep = sorted(hang_bc, reverse=True)
    print(f"Manh nhat:  {', '.join(t for _, _, t, _ in xep[:3])}")
    print(f"Yeu nhat:   {', '.join(t for _, _, t, _ in xep[-3:])}\n")

    print("CAC CAP LOAI CUNG HO — Bo C tach duoc bang may thuoc tinh?")
    print("(day la cac cap kho nhat; 0 nghia la Bo C bat luc, 1 nghia la rat mong manh)")
    print(f"\n{'ho':<7}{'loai A':<10}{'loai B':<10}{'so tt khac':>12}   thuoc tinh nao")
    print("-" * 95)
    cap_cung_ho = [(a, b) for a, b in combinations(mas, 2) if ho[a] == ho[b]]
    for a, b in sorted(cap_cung_ho, key=lambda p: (ho[p[0]], p[0], p[1])):
        khac = [t for t in THUOC_TINH if bang[a][t] != bang[b][t]]
        canh = "  <- MONG MANH" if len(khac) <= 2 else ""
        print(f"{ho[a]:<7}{a:<10}{b:<10}{len(khac):>12}   {', '.join(khac)}{canh}")
    print("-" * 95)
    print(f"{len(cap_cung_ho)} cap cung ho / {tong_cap} cap tong\n")


# ------------------------------------------------------------- self-test


def _selftest() -> None:
    # Từ vựng không được có giá trị trùng trong cùng một thuộc tính.
    for t, tv in TU_VUNG.items():
        assert len(tv) == len(set(tv)), t
    assert THU_TU <= set(TU_VUNG), "THU_TU trỏ tới thuộc tính không tồn tại"
    assert SO_CHIEU == 35, SO_CHIEU

    bang = {
        "AAA_AAA": dict(dang_than="thoi", ti_le_dai_cao="dai", mau_nen="bac", soc="khong",
                        cham="thua", tuong_phan_lung_bung="manh", dang_duoi="chia_sau",
                        vay_lung="co_vay_mo", kich_thuoc="lon", moi_truong="nuoc_lo"),
        "BBB_BBB": dict(dang_than="det_tron", ti_le_dai_cao="rat_cao", mau_nen="da_mau",
                        soc="vach_dung", cham="khong", tuong_phan_lung_bung="yeu",
                        dang_duoi="tron", vay_lung="dai_lien", kich_thuoc="nho",
                        moi_truong="nuoc_ngot"),
    }
    assert kiem_tra(bang, ["AAA_AAA", "BBB_BBB"]) == []

    # Thiếu loài thì phải báo.
    assert any("thiếu dòng" in e for e in kiem_tra(bang, ["AAA_AAA", "BBB_BBB", "CCC_CCC"]))
    # Có loài lạ thì phải báo.
    assert any("không ở trạng thái da_chot" in e for e in kiem_tra(bang, ["AAA_AAA"]))
    # Giá trị ngoài từ vựng thì phải báo.
    xau = {"AAA_AAA": dict(bang["AAA_AAA"], mau_nen="tim")}
    assert any("không có trong từ vựng" in e for e in kiem_tra(xau, ["AAA_AAA"]))
    # Bỏ trống thì phải báo.
    rong = {"AAA_AAA": dict(bang["AAA_AAA"], soc="")}
    assert any("bỏ trống" in e for e in kiem_tra(rong, ["AAA_AAA"]))
    # Hai loài trùng hoàn toàn thì phải báo — đây là phép kiểm quan trọng nhất.
    trung = {"AAA_AAA": bang["AAA_AAA"], "BBB_BBB": dict(bang["AAA_AAA"])}
    assert any("trùng hoàn toàn" in e for e in kiem_tra(trung, ["AAA_AAA", "BBB_BBB"]))

    # Mã hóa: đúng số chiều, mọi giá trị trong [0,1].
    v = ma_hoa(bang["AAA_AAA"])
    assert len(v) == SO_CHIEU, len(v)
    assert all(0.0 <= x <= 1.0 for x in v)
    # Ordinal: bậc thấp nhất ra 0,0 và bậc cao nhất ra 1,0.
    thap = dict(bang["AAA_AAA"], kich_thuoc="rat_nho")
    cao = dict(bang["AAA_AAA"], kich_thuoc="rat_lon")
    i_kt = sum(1 if t in THU_TU else len(TU_VUNG[t])
               for t in THUOC_TINH[:THUOC_TINH.index("kich_thuoc")])
    assert ma_hoa(thap)[i_kt] == 0.0
    assert ma_hoa(cao)[i_kt] == 1.0
    # Nominal: khối one-hot của mau_nen phải cộng lại đúng 1.
    i_mn = sum(1 if t in THU_TU else len(TU_VUNG[t])
               for t in THUOC_TINH[:THUOC_TINH.index("mau_nen")])
    assert sum(v[i_mn:i_mn + len(TU_VUNG["mau_nen"])]) == 1.0

    # Entropy: hai giá trị khác nhau trên 2 loài = 1 bit; giống nhau = 0 bit.
    assert abs(entropy(["a", "b"]) - 1.0) < 1e-9
    assert entropy(["a", "a"]) == 0.0
    assert abs(entropy(["a", "a", "b", "b"]) - 1.0) < 1e-9
    assert so_cap_tach_duoc(bang, "mau_nen") == 1
    assert so_cap_tach_duoc(trung, "mau_nen") == 0

    print("bo_c.py: self-test OK")


def main() -> int:
    ap = argparse.ArgumentParser(description="Bộ C — thuộc tính ngữ nghĩa theo loài")
    ap.add_argument("--kiem-tra", action="store_true",
                    help="kiểm bảng thuộc tính rồi in báo cáo giá trị thông tin")
    a = ap.parse_args()

    if not a.kiem_tra:
        _selftest()
        return 0

    if not BO_C_CSV.exists():
        print(f"LOI: chua co {BO_C_CSV.relative_to(ROOT)}", file=sys.stderr)
        return 1

    ma_chot = loai_da_chot()
    bang = doc_bo_c()
    loi = kiem_tra(bang, ma_chot)
    if loi:
        print(f"LOI: bang thuoc tinh co {len(loi)} van de\n", file=sys.stderr)
        for e in loi:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(f"OK: {len(bang)} loai, moi gia tri nam trong tu vung, khong loai nao trung nhau")
    bao_cao(bang, ho_cua_loai())
    return 0


if __name__ == "__main__":
    sys.exit(main())
