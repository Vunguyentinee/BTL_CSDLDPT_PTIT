"""Danh mục loài và danh sách ảnh đã chuẩn hóa.

Một chỗ duy nhất trả lời hai câu hỏi: hệ có những loài nào, và mỗi loài có
những ảnh nào. Mọi phần khác của hệ đọc qua đây chứ không tự quét thư mục,
để không ai vô tình nhặt nhầm hai loài đã loại (CLA_BAT, PAM_ARG) — ảnh của
chúng vẫn còn trên đĩa nhưng không thuộc bộ dữ liệu.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import NamedTuple

import numpy as np
from PIL import Image

from . import cauhinh


class Anh(NamedTuple):
    """Một ảnh đã chuẩn hóa.

    `image_id` gồm cả mã loài vì tên file chỉ duy nhất trong một thư mục loài,
    không duy nhất trên toàn bộ.
    """

    image_id: str
    ma_loai: str
    duong_dan: Path


def doc_loai(path: Path | None = None, trang_thai: str = "da_chot") -> list[dict[str, str]]:
    """Các dòng trong species.csv có trạng thái cho trước, giữ nguyên thứ tự file."""
    path = path or cauhinh.SPECIES_CSV
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [d for d in csv.DictReader(f) if d["trang_thai"] == trang_thai]


def ma_loai_chot(path: Path | None = None) -> list[str]:
    return [d["ma_loai"] for d in doc_loai(path)]


def ten_hien_thi(path: Path | None = None) -> dict[str, str]:
    return {d["ma_loai"]: d["ten_viet"] for d in doc_loai(path)}


def ho_cua_loai(path: Path | None = None) -> dict[str, str]:
    """Mã họ của từng loài — dùng cho P@5 theo họ và cho cặp loài cùng họ."""
    return {d["ma_loai"]: d["ma_ho"] for d in doc_loai(path)}


def liet_ke_anh(goc: Path | None = None, ma_loai: list[str] | None = None) -> list[Anh]:
    """Mọi ảnh .png của các loài đã chốt, sắp xếp ổn định.

    Sắp xếp theo (ma_loai, tên file) chứ không theo thứ tự hệ điều hành trả về,
    vì thứ tự đó khác nhau giữa các máy và sẽ làm phép chia fold không tái lập.
    """
    goc = goc or cauhinh.ANH_CHUAN
    ma_loai = ma_loai if ma_loai is not None else ma_loai_chot()
    ra: list[Anh] = []
    for ma in sorted(ma_loai):
        thu_muc = goc / ma
        if not thu_muc.is_dir():
            continue
        for p in sorted(thu_muc.glob("*.png"), key=lambda q: q.name):
            ra.append(Anh(f"{ma}/{p.stem}", ma, p))
    return ra


def dem_theo_loai(anh: list[Anh]) -> dict[str, int]:
    d: dict[str, int] = {}
    for a in anh:
        d[a.ma_loai] = d.get(a.ma_loai, 0) + 1
    return d


def nap_anh(duong_dan: Path, nguong_alpha: int = 128) -> tuple[np.ndarray, np.ndarray]:
    """Đọc PNG RGBA đã chuẩn hóa → (rgb uint8 HxWx3, mask bool HxW).

    Kênh alpha chính là mask thân cá do rembg sinh ra, đã được chuan_hoa.py
    giữ lại qua phép affine. Ngưỡng 128 để cắt phần biên bán trong suốt:
    điểm ảnh biên trộn lẫn màu nền xám nên không được tính vào đặc trưng màu.
    """
    with Image.open(duong_dan) as im:
        im = im.convert("RGBA")
        a = np.asarray(im)
    return np.ascontiguousarray(a[:, :, :3]), a[:, :, 3] >= nguong_alpha


def co_mask(mask: np.ndarray, px: int) -> np.ndarray:
    """Co mask vào trong `px` điểm ảnh bằng phép ăn mòn hình vuông.

    Đặc trưng kết cấu (LBP, GLCM, Gabor) lấy cửa sổ quanh mỗi điểm ảnh, nên ở
    sát biên cá chúng sẽ hút cả nền xám vào và sinh ra kết cấu giả. Co vào vài
    điểm ảnh là cách rẻ nhất để tránh. Đặc trưng màu không cần.
    """
    if px <= 0:
        return mask
    m = mask
    for _ in range(px):
        g = m.copy()
        g[1:, :] &= m[:-1, :]
        g[:-1, :] &= m[1:, :]
        g[:, 1:] &= m[:, :-1]
        g[:, :-1] &= m[:, 1:]
        m = g
    return m


# ------------------------------------------------------------- self-test


def _selftest() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        goc = Path(d)
        # liet_ke_anh chỉ nhặt loài được yêu cầu, bỏ qua thư mục lạ.
        for ma in ("AAA_AAA", "BBB_BBB", "ZZZ_LOAI"):
            (goc / ma).mkdir()
            for i in range(3):
                Image.new("RGBA", (8, 8), (10, 20, 30, 255)).save(goc / ma / f"anh{i}.png")
        anh = liet_ke_anh(goc, ["AAA_AAA", "BBB_BBB"])
        assert len(anh) == 6, len(anh)
        assert {a.ma_loai for a in anh} == {"AAA_AAA", "BBB_BBB"}
        # image_id phải duy nhất dù tên file trùng nhau giữa hai loài.
        assert len({a.image_id for a in anh}) == 6
        assert anh[0].image_id == "AAA_AAA/anh0"
        # Thứ tự phải ổn định và không phụ thuộc thứ tự hệ điều hành trả về.
        assert [a.image_id for a in anh] == sorted(a.image_id for a in anh)
        assert dem_theo_loai(anh) == {"AAA_AAA": 3, "BBB_BBB": 3}
        # Thư mục loài không tồn tại thì bỏ qua, không nổ.
        assert liet_ke_anh(goc, ["KHONG_CO"]) == []

        # nap_anh: alpha dưới ngưỡng thành False, từ ngưỡng trở lên thành True.
        p = goc / "thu.png"
        a = np.zeros((4, 4, 4), np.uint8)
        a[:, :, :3] = (200, 100, 50)
        a[0, 0, 3], a[1, 1, 3], a[2, 2, 3] = 0, 127, 128
        a[3, 3, 3] = 255
        Image.fromarray(a, "RGBA").save(p)
        rgb, mask = nap_anh(p)
        assert rgb.shape == (4, 4, 3) and mask.shape == (4, 4)
        assert tuple(rgb[0, 0]) == (200, 100, 50)
        assert not mask[0, 0] and not mask[1, 1]
        assert mask[2, 2] and mask[3, 3]

    # co_mask: một khối 5x5 đặc, co 1 px còn 3x3.
    m = np.zeros((9, 9), bool)
    m[2:7, 2:7] = True
    assert co_mask(m, 0).sum() == 25
    assert co_mask(m, 1).sum() == 9, co_mask(m, 1).sum()
    assert co_mask(m, 2).sum() == 1
    assert co_mask(m, 3).sum() == 0
    # Co mask không bao giờ làm mask to ra.
    assert (co_mask(m, 1) & ~m).sum() == 0


def _selftest_du_lieu_that() -> None:
    """Đối chiếu với đĩa. Chỉ chạy khi gọi kiem_tra.py --day-du."""
    ma = ma_loai_chot()
    assert len(ma) == 20, f"phải có 20 loài đã chốt, đang có {len(ma)}"
    assert "CLA_BAT" not in ma and "PAM_ARG" not in ma, "hai loài đã loại lọt vào danh mục"

    anh = liet_ke_anh()
    assert len(anh) == 1085, f"phải có 1.085 ảnh, đang có {len(anh)}"
    assert len({a.image_id for a in anh}) == 1085, "image_id bị trùng"

    dem = dem_theo_loai(anh)
    assert set(dem) == set(ma), "có loài không có ảnh nào"
    assert min(dem.values()) == 19, f"loài ít nhất phải có 19 ảnh, đang là {min(dem.values())}"
    assert max(dem.values()) == 162, f"loài nhiều nhất phải có 162 ảnh, đang là {max(dem.values())}"

    # Mọi ảnh phải đúng khổ 384x384 và có mask không rỗng.
    rgb, mask = nap_anh(anh[0].duong_dan)
    assert rgb.shape == (cauhinh.CANVAS, cauhinh.CANVAS, 3), rgb.shape
    assert mask.any(), "ảnh đầu tiên có mask rỗng"
