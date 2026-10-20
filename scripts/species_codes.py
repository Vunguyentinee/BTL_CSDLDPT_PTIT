"""Bước 3 — Sinh mã loài (`ma_loai`) và mã họ (`ma_ho`) theo quy ước của nhóm.

Quy ước (xem `docs/plan/quy-trinh-cong-viec.md`, Phụ lục B):

    ma_loai = <3 chữ đầu của chi>_<3 chữ đầu của tính ngữ loài>, in hoa
    ma_ho   = <4 chữ đầu của tên họ>, in hoa

Xử lý trùng mã: nới phần sau lên 4 chữ cho **tất cả** thành viên của nhóm bị
trùng (không chỉ một loài), còn trùng thì lên 5, tối đa 8 chữ. Nhờ nới cho cả
nhóm mà mã vẫn suy ra được từ tên khoa học, không cần tra bảng ngoại lệ.

Module này thuần tính toán, không đọc/ghi file và không gọi mạng, nên chạy
`python scripts/species_codes.py` sẽ tự kiểm tra bằng vài ví dụ.
"""

from __future__ import annotations

import re
import unicodedata

GENUS_LEN = 3
EPITHET_LEN = 3
FAMILY_LEN = 4
MAX_PART_LEN = 8

RE_SPECIES_CODE = re.compile(r"^[A-Z]{1,8}_[A-Z]{1,8}$")
RE_FAMILY_CODE = re.compile(r"^[A-Z]{2,8}$")


def to_letters(text: str) -> str:
    """Bỏ dấu, bỏ mọi ký tự không phải chữ cái Latin, trả về chữ in hoa.

    'Cá chép' -> 'CACHEP', 'sp-nov.' -> 'SPNOV'
    """
    decomposed = unicodedata.normalize("NFKD", text or "")
    ascii_only = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"[^A-Za-z]", "", ascii_only).upper()


def split_scientific_name(name: str) -> tuple[str, str]:
    """'Cyprinus carpio' -> ('Cyprinus', 'carpio').

    Bỏ qua mọi thành phần từ thứ ba trở đi (phân loài, tên tác giả, năm).
    """
    tokens = [t for t in re.split(r"\s+", (name or "").strip()) if t]
    if len(tokens) < 2:
        raise ValueError(
            f"Tên khoa học phải gồm ít nhất chi + tính ngữ loài: {name!r}"
        )
    return tokens[0], tokens[1]


def _species_code(genus: str, epithet: str, epithet_len: int) -> str:
    g = to_letters(genus)[:GENUS_LEN]
    e = to_letters(epithet)[:epithet_len]
    if not g or not e:
        raise ValueError(f"Không sinh được mã từ {genus!r} {epithet!r}")
    return f"{g}_{e}"


def _resolve(make_code, count: int, start_len: int) -> tuple[list[str], list[str]]:
    """Sinh mã cho `count` phần tử rồi nới dần cho tới khi không còn trùng.

    `make_code(i, length)` trả về mã của phần tử i với độ dài phần sau là `length`.
    Trả về (danh sách mã, danh sách cảnh báo).
    """
    lengths = [start_len] * count
    warnings: list[str] = []

    while True:
        codes = [make_code(i, lengths[i]) for i in range(count)]

        groups: dict[str, list[int]] = {}
        for i, code in enumerate(codes):
            groups.setdefault(code, []).append(i)
        clashes = {code: idx for code, idx in groups.items() if len(idx) > 1}
        if not clashes:
            return codes, warnings

        # Nới cho toàn bộ thành viên của mỗi nhóm bị trùng.
        grew = False
        for code, idx in clashes.items():
            for i in idx:
                if lengths[i] < MAX_PART_LEN:
                    lengths[i] += 1
                    grew = True

        if not grew:
            for code, idx in clashes.items():
                warnings.append(
                    f"không tách được mã trùng {code!r} (các dòng {idx}) "
                    f"dù đã nới tới {MAX_PART_LEN} chữ — phải đặt mã tay"
                )
            return codes, warnings


def _assign_over_unique(
    keys: list, make, start_len: int
) -> tuple[list[str], list[str]]:
    """Sinh mã theo danh sách khóa, chỉ giải trùng giữa các khóa KHÁC NHAU.

    Hai dòng có cùng khóa (cùng một họ, hoặc cùng một tên khoa học) phải nhận
    **cùng một mã** — đó không phải trùng mã. Nếu không tách hai trường hợp này
    ra thì mọi loài cùng họ sẽ bị coi là xung đột và mã họ bị nới vô nghĩa.
    """
    uniq = list(dict.fromkeys(keys))

    def make_index(i: int, length: int) -> str:
        return make(uniq[i], length)

    codes, warnings = _resolve(make_index, len(uniq), start_len)
    table = dict(zip(uniq, codes))
    return [table[k] for k in keys], warnings


def assign_species_codes(scientific_names: list[str]) -> tuple[list[str], list[str]]:
    """Sinh `ma_loai` cho một danh sách tên khoa học, giữ nguyên thứ tự.

    Hai dòng cùng tên khoa học sẽ nhận cùng mã và bị báo là dòng trùng lặp.
    """
    parts = [split_scientific_name(n) for n in scientific_names]
    keys = [(to_letters(g), to_letters(e)) for g, e in parts]

    def make(key: tuple[str, str], length: int) -> str:
        return _species_code(key[0], key[1], length)

    codes, warnings = _assign_over_unique(keys, make, EPITHET_LEN)

    seen: dict[tuple[str, str], int] = {}
    for i, key in enumerate(keys):
        if key in seen:
            warnings.append(
                f"tên khoa học {scientific_names[i]!r} xuất hiện ở cả dòng "
                f"{seen[key]} và {i} — hai dòng trùng loài"
            )
        else:
            seen[key] = i

    return codes, warnings


def assign_family_codes(family_names: list[str]) -> tuple[list[str], list[str]]:
    """Sinh `ma_ho` cho một danh sách tên họ, giữ nguyên thứ tự.

    Mọi loài cùng họ nhận cùng mã. Hai họ **khác tên** mà trùng 4 chữ đầu
    (Cyprinidae và Cyprinodontidae) thì được nới cho tới khi tách được.
    """
    cleaned = [to_letters(f) for f in family_names]
    for i, name in enumerate(cleaned):
        if not name:
            raise ValueError(f"Tên họ rỗng ở dòng {i}")

    def make(key: str, length: int) -> str:
        return key[:length]

    return _assign_over_unique(cleaned, make, FAMILY_LEN)


def genus_of(scientific_name: str) -> str:
    """Trả về phần chi của tên khoa học, giữ nguyên cách viết hoa gốc."""
    return split_scientific_name(scientific_name)[0]


def _selftest() -> None:
    codes, warns = assign_species_codes(
        [
            "Cyprinus carpio",
            "Carassius auratus",
            "Amphiprion ocellaris",
            "Amphiprion frenatus",
            "Zebrasoma flavescens",
        ]
    )
    assert codes == ["CYP_CAR", "CAR_AUR", "AMP_OCE", "AMP_FRE", "ZEB_FLA"], codes
    assert not warns

    # Hai loài cùng chi và trùng 3 chữ đầu tính ngữ -> nới cho CẢ HAI lên 4 chữ.
    # Tên dưới đây là tên giả, chỉ để kiểm tra luật nới.
    codes, warns = assign_species_codes(
        ["Aaa marmoratus", "Aaa marginatus", "Bbb striata"]
    )
    assert codes == ["AAA_MARM", "AAA_MARG", "BBB_STR"], codes
    assert not warns

    # Trùng sâu: 'argentimaculatus' và 'argentiventris' giống nhau tới 7 chữ
    # ('argenti'), nên phải nới tới 8 mới tách được. Mã dài ra là đúng quy ước.
    codes, warns = assign_species_codes(
        ["Lutjanus argentimaculatus", "Lutjanus argentiventris"]
    )
    assert codes == ["LUT_ARGENTIM", "LUT_ARGENTIV"], codes
    assert not warns

    fams, warns = assign_family_codes(["Cyprinidae", "Cichlidae", "Channidae", "Clariidae"])
    assert fams == ["CYPR", "CICH", "CHAN", "CLAR"], fams
    assert not warns

    # Nhiều loài cùng họ phải nhận CÙNG mã, không được coi là trùng mã.
    fams, warns = assign_family_codes(["Cyprinidae", "Cyprinidae", "Scombridae"])
    assert fams == ["CYPR", "CYPR", "SCOM"], fams
    assert not warns

    # Cyprinidae và Cyprinodontidae giống nhau tới 6 chữ ('Cyprin') nên mã họ
    # phải nới tới 7 chữ cho cả hai.
    fams, warns = assign_family_codes(["Cyprinidae", "Cyprinodontidae"])
    assert fams == ["CYPRINI", "CYPRINO"], fams
    assert not warns

    assert to_letters("Cá chép") == "CACHEP"
    assert genus_of("Pangasianodon hypophthalmus") == "Pangasianodon"
    assert RE_SPECIES_CODE.match("CYP_CAR")
    assert not RE_SPECIES_CODE.match("cyp_car")
    print("species_codes.py — tất cả phép tự kiểm đã qua.")


if __name__ == "__main__":
    _selftest()
