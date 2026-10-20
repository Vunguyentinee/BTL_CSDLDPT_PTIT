"""Đường dẫn và hằng số dùng chung cho cả hệ.

Gom vào một chỗ để không rải `Path(__file__).parent.parent` khắp nơi, và để
đổi vị trí dữ liệu bằng biến môi trường mà không phải sửa code.
"""

from __future__ import annotations

import os
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent


def _doc_env(path: Path) -> dict[str, str]:
    """Đọc file .env dạng KEY=VALUE. Không cần thư viện ngoài.

    Bỏ qua dòng trống và dòng bắt đầu bằng #. Không xử lý dấu nháy lồng nhau
    hay nối dòng — file cấu hình của dự án này chỉ có vài đường dẫn.
    """
    if not path.exists():
        return {}
    ra: dict[str, str] = {}
    for dong in path.read_text(encoding="utf-8").splitlines():
        dong = dong.strip()
        if not dong or dong.startswith("#") or "=" not in dong:
            continue
        k, _, v = dong.partition("=")
        ra[k.strip()] = v.strip().strip('"').strip("'")
    return ra


_ENV = {**_doc_env(GOC / ".env"), **os.environ}


def _duong_dan(khoa: str, mac_dinh: str) -> Path:
    gt = _ENV.get(khoa)
    return Path(gt) if gt else GOC / mac_dinh


# --- thư mục ---
ANH_CHUAN = _duong_dan("FISHCBIR_ANH_CHUAN", "work/chuan")
DATA_META = _duong_dan("FISHCBIR_DATA_META", "data_meta")
SPECIES_CSV = DATA_META / "species.csv"
THUOC_TINH_CSV = DATA_META / "thuoc_tinh_ngu_nghia.csv"
SPLITS = DATA_META / "splits"
FOLDS_CSV = SPLITS / "folds.csv"
KET_QUA = _duong_dan("FISHCBIR_KET_QUA", "ket_qua")

# --- hằng số ---
# Phải khớp với scripts/chuan_hoa.py. Nếu đổi ở đó thì phải đổi ở đây.
CANVAS = 384
SO_FOLD = 5
# Seed cố định để chia fold tái lập được. Đổi seed là đổi toàn bộ số liệu
# đánh giá, nên chỉ đổi khi có lý do và phải ghi vào báo cáo.
SEED = 20261020


def _selftest() -> None:
    assert GOC.is_dir()
    assert SPECIES_CSV.name == "species.csv"
    assert FOLDS_CSV.parent == SPLITS
    assert SO_FOLD >= 2
    assert CANVAS == 384

    # _doc_env: bỏ qua dòng trống, chú thích, dòng không có dấu =; bóc nháy.
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / ".env"
        p.write_text(
            '# chu thich\n\nA=1\nB = "hai"\nC=\'ba\'\nkhong_co_dau_bang\nD=co=dau=bang\n',
            encoding="utf-8",
        )
        e = _doc_env(p)
        assert e == {"A": "1", "B": "hai", "C": "ba", "D": "co=dau=bang"}, e
        assert _doc_env(Path(d) / "khong_ton_tai.env") == {}
