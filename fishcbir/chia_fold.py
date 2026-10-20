"""Chia 5-fold phân tầng theo loài.

Vì sao 5-fold chứ không chia 80/20 một lần: chia một lần chỉ cho ~217 truy
vấn, và loài ít ảnh nhất (CHA_STR, 19 ảnh) chỉ còn 4 truy vấn — sai số trên
loài đó lớn tới mức con số không nói lên điều gì. Với 5-fold, **mọi** ảnh đều
lần lượt làm truy vấn đúng một lần, cho 1.085 truy vấn, mà không tốn thêm
phút duyệt ảnh nào.

Phân tầng theo loài nghĩa là mỗi loài được rải đều vào cả 5 fold, nên không
fold nào thiếu hẳn một loài trong gallery.
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

from . import cauhinh
from .danhmuc import Anh


def chia(anh: list[Anh], so_fold: int | None = None, seed: int | None = None) -> dict[str, int]:
    """Gán mỗi image_id một số fold trong [0, so_fold).

    Cách làm: với từng loài, xáo danh sách ảnh bằng seed cố định rồi rải vòng
    tròn vào các fold. Điểm bắt đầu của mỗi loài lệch đi một bậc (`moc`) thay
    vì luôn bắt đầu từ fold 0 — nếu loài nào cũng bắt đầu từ 0 thì với các loài
    có số ảnh không chia hết cho 5, fold 0 sẽ luôn nhận phần dư và phình ra.
    """
    so_fold = so_fold or cauhinh.SO_FOLD
    seed = cauhinh.SEED if seed is None else seed
    if so_fold < 2:
        raise ValueError("so_fold phải >= 2")

    theo_loai: dict[str, list[str]] = {}
    for a in anh:
        theo_loai.setdefault(a.ma_loai, []).append(a.image_id)

    ra: dict[str, int] = {}
    moc = 0
    for ma in sorted(theo_loai):
        ids = sorted(theo_loai[ma])
        # Random riêng cho từng loài, gieo bằng seed + tên loài, để thêm hay
        # bớt một loài không làm xáo trộn phép chia của các loài còn lại.
        random.Random(f"{seed}:{ma}").shuffle(ids)
        for i, iid in enumerate(ids):
            ra[iid] = (moc + i) % so_fold
        moc = (moc + len(ids)) % so_fold
    return ra


def ghi_csv(path: Path, anh: list[Anh], fold: dict[str, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["image_id", "ma_loai", "fold", "duong_dan"])
        for a in sorted(anh):
            w.writerow([a.image_id, a.ma_loai, fold[a.image_id],
                        a.duong_dan.relative_to(cauhinh.GOC).as_posix()])


def doc_csv(path: Path | None = None) -> dict[str, int]:
    path = path or cauhinh.FOLDS_CSV
    with path.open(encoding="utf-8-sig", newline="") as f:
        return {d["image_id"]: int(d["fold"]) for d in csv.DictReader(f)}


def thong_ke(anh: list[Anh], fold: dict[str, int], so_fold: int | None = None) -> list[list[int]]:
    """Ma trận [loài][fold] đếm số ảnh — dùng để kiểm mắt và để in báo cáo."""
    so_fold = so_fold or cauhinh.SO_FOLD
    mas = sorted({a.ma_loai for a in anh})
    bang = [[0] * so_fold for _ in mas]
    chi_so = {m: i for i, m in enumerate(mas)}
    for a in anh:
        bang[chi_so[a.ma_loai]][fold[a.image_id]] += 1
    return bang


# ------------------------------------------------------------- self-test


def _gia_lap(dem: dict[str, int]) -> list[Anh]:
    return [Anh(f"{m}/a{i:04d}", m, Path(f"work/chuan/{m}/a{i:04d}.png"))
            for m, n in dem.items() for i in range(n)]


def _selftest() -> None:
    dem = {"AAA_AAA": 19, "BBB_BBB": 162, "CCC_CCC": 37, "DDD_DDD": 20, "EEE_EEE": 21}
    anh = _gia_lap(dem)
    f = chia(anh, so_fold=5, seed=1)

    # Phân hoạch đúng: mọi ảnh có đúng một fold, không ảnh nào sót.
    assert set(f) == {a.image_id for a in anh}
    assert all(0 <= v < 5 for v in f.values())

    # Mọi loài phải có mặt ở cả 5 fold.
    for ma, n in dem.items():
        co = {f[a.image_id] for a in anh if a.ma_loai == ma}
        assert co == set(range(5)), f"{ma} chỉ có mặt ở fold {sorted(co)}"
        # Số ảnh mỗi fold của một loài chênh nhau tối đa 1 — đó là ý nghĩa của phân tầng.
        dem_fold = [sum(1 for a in anh if a.ma_loai == ma and f[a.image_id] == k) for k in range(5)]
        assert max(dem_fold) - min(dem_fold) <= 1, (ma, dem_fold)
        assert sum(dem_fold) == n

    # Tổng mỗi fold cũng phải cân — đây là việc của `moc`.
    tong = [sum(1 for v in f.values() if v == k) for k in range(5)]
    assert max(tong) - min(tong) <= 2, tong

    # Tái lập: cùng seed cho cùng kết quả, khác seed cho kết quả khác.
    assert chia(anh, 5, 1) == f
    assert chia(anh, 5, 2) != f

    # Thêm một loài mới không được làm xáo trộn fold của các loài cũ.
    anh2 = anh + _gia_lap({"FFF_FFF": 30})
    f2 = chia(anh2, 5, 1)
    cu = [a for a in anh if a.ma_loai != "AAA_AAA"]  # moc dịch nên chỉ loài sau bị ảnh hưởng
    assert all(f2[a.image_id] == f[a.image_id] for a in anh if a.ma_loai == "AAA_AAA"), \
        "xáo trộn phép chia của loài cũ"
    assert len(cu) > 0

    # so_fold không hợp lệ phải báo lỗi.
    try:
        chia(anh, so_fold=1)
        raise AssertionError("so_fold=1 phải ném ValueError")
    except ValueError:
        pass

    # thong_ke: tổng toàn bảng bằng số ảnh.
    bang = thong_ke(anh, f, 5)
    assert sum(map(sum, bang)) == len(anh)
    assert len(bang) == len(dem)


def _selftest_du_lieu_that() -> None:
    from .danhmuc import liet_ke_anh, ma_loai_chot

    anh = liet_ke_anh()
    f = chia(anh)
    assert len(f) == 1085

    for ma in ma_loai_chot():
        co = {f[a.image_id] for a in anh if a.ma_loai == ma}
        assert co == set(range(cauhinh.SO_FOLD)), f"{ma} thiếu fold {sorted(set(range(5)) - co)}"

    tong = [sum(1 for v in f.values() if v == k) for k in range(cauhinh.SO_FOLD)]
    assert sum(tong) == 1085
    assert max(tong) - min(tong) <= 5, tong
