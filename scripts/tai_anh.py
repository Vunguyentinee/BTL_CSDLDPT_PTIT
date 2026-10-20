"""Tải ảnh cá về và lọc sơ bộ — thay cho `craw_data.py`.

Bốn chế độ:

    inat      Tải từ iNaturalist theo **taxon_id**. Đây là NGUỒN CHÍNH: lọc theo
              mã loài nên không bao giờ trả nhầm loài, kèm `quality_grade=research`
              (loài đã được cộng đồng xác nhận) và lọc giấy phép ngay trong truy vấn.
    crawl     Tìm theo tên khoa học trên Bing. ⚠️ KHÔNG ĐÁNG TIN — Bing bỏ qua
              tên Latin ít phổ biến và trả về nội dung thương mại theo vị trí địa
              lý. Lần chạy 03/10 cho ra ~2000 ảnh tai nghe, mỹ phẩm, sách; đã phải
              xóa sạch. Chỉ dùng khi đã xem tận mắt bảng ảnh mẫu và thấy đúng.
    fishbase  Tải ảnh mẫu vật từ FishBase. Ảnh chụp nghiêng ngang, nền sạch,
              nhãn loài đáng tin — tỉ lệ đạt chuẩn cao nhất trong các nguồn,
              nhưng mỗi loài chỉ có vài chục ảnh nên dùng để bù, không đủ một mình.
    url       Tải từ danh sách URL thành viên nộp qua Google Sheet.

Cả hai chế độ đều chạy cùng một dây lọc:

    tải về → kiểm đọc được → áp hướng EXIF rồi xóa EXIF → chuyển RGB
    → loại ảnh nhỏ → loại trùng tuyệt đối (SHA-256) → loại trùng gần (dHash)
    → resize cạnh dài ≤ 1600px → lưu JPEG q90, tên `<ma_loai>__<nguon>__<sha8>.jpg`

Cách dùng:

    python scripts/tai_anh.py crawl                          # mọi loài da_chot
    python scripts/tai_anh.py crawl --loai CYP_CAR --limit 50
    python scripts/tai_anh.py url --csv work/urls.csv
    python scripts/tai_anh.py bao-cao

Chạy lại được nhiều lần: ảnh đã có sẽ bị nhận ra là trùng và bỏ qua, nên cứ
chạy thêm để bù cho loài còn thiếu.

Ảnh ra ở `work/anh/<ma_loai>/`. Xem báo cáo thấy đủ thì copy thư mục đó lên
Drive để cả nhóm duyệt.

Phụ thuộc: requests, Pillow.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import io
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
SPECIES_CSV = ROOT / "data_meta" / "species.csv"
OUT_DIR = ROOT / "work" / "anh"

# --- Tham số lọc (đã thống nhất trong docs/plan/ke-hoach.md) ---------------
# Ngưỡng này CHỈ là phép kiểm thô để bỏ icon và ảnh thu nhỏ. Nó đo cả ảnh,
# trong khi thứ thật sự quan trọng là **con cá dài bao nhiêu pixel** — mà điều
# đó chỉ biết được sau khi `rembg` tách được mask. Phép kiểm thật nằm ở
# `chuan_hoa.py`: cạnh dài của hộp bao mask phải ≥ 256px, nếu không thì bước
# resize về 256×256 sẽ là PHÓNG TO, làm nhòe vảy và sọc — đúng những thứ mà
# LBP, GLCM và Gabor đo. Ảnh mờ sẽ giống nhau vì đều mờ chứ không vì cùng loài.
#
# Đặt 320 thay vì 600 để không loại oan: ảnh FishBase bị giới hạn 640px và
# nhiều ảnh web nằm trong khoảng 400–600px, nhưng cá chiếm gần hết khung nên
# vẫn dùng được. Trong 342 ảnh đã tải, ngưỡng 600 sẽ loại oan 27 ảnh tốt.
MIN_EDGE = 320
MAX_EDGE = 1600         # resize cạnh dài về tối đa mức này
JPEG_QUALITY = 90
DHASH_THRESHOLD = 5     # khoảng cách Hamming coi là trùng gần (trên 64 bit)
MAX_BYTES = 25 * 1024 * 1024
MAX_RETRIES = 4         # số lần thử lại khi lỗi mạng thoáng qua
TARGET_PER_SPECIES = 70

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
# URL của ảnh thu nhỏ do Google/Bing phục vụ — không phải ảnh gốc, loại ngay.
THUMBNAIL_HOSTS = ("gstatic.com", "googleusercontent.com", "bing.net", "bing.com")

# ---------------------------------------------------------------- lọc trùng


def dhash(img: Image.Image, size: int = 8) -> int:
    """Mã băm tri giác 64 bit: so sánh từng pixel với pixel bên phải nó.

    Tự cài thay vì dùng gói `imagehash` để không phải thêm scipy và pywavelets
    vào danh sách phụ thuộc chỉ cho một hàm.
    """
    small = img.convert("L").resize((size + 1, size), Image.Resampling.LANCZOS)
    # Pillow 12 đổi `getdata()` thành `get_flattened_data()`; dùng được cả hai bản.
    lay_pixel = getattr(small, "get_flattened_data", None) or small.getdata
    px = list(lay_pixel())
    bits = 0
    for row in range(size):
        line = px[row * (size + 1) : (row + 1) * (size + 1)]
        for col in range(size):
            bits = (bits << 1) | (1 if line[col] > line[col + 1] else 0)
    return bits


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


class KhoAnh:
    """Quản lý thư mục ảnh của một loài: nạp chỉ mục cũ, thêm ảnh mới.

    Chỉ mục dùng **JSON Lines và ghi bổ sung từng dòng ngay khi lưu ảnh**, thay
    vì ghi lại toàn bộ file ở cuối lượt chạy. Ba lý do:

    * Ngắt giữa lượt chạy không mất gì — ảnh nào đã lưu là đã được ghi nhận.
    * Không bao giờ phải ghi lại cả file nên không có nguy cơ ghi dở làm hỏng.
    * Excel không tự giữ file `.jsonl`. Bản trước dùng `_index.csv` và đã gặp
      `PermissionError` vì Excel mở file đó, làm cả lượt tải chết giữa đường.

    Vẫn đọc được `_index.csv` cũ để không mất dữ liệu của các lượt chạy trước.
    """

    def __init__(self, ma_loai: str, out_dir: Path):
        self.ma_loai = ma_loai
        self.dir = out_dir / ma_loai
        self.dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.dir / "_index.jsonl"
        self.legacy_csv = self.dir / "_index.csv"
        self.url_log = self.dir / "_urls_da_thu.txt"
        self.shas: set[str] = set()
        self.hashes: list[int] = []
        self.rows: list[dict] = []
        self.urls_da_thu: set[str] = set()
        self.loi_ghi_index = False
        self._load()

    def da_thu_url(self, url: str) -> bool:
        """URL đã tải thử ở lượt trước thì bỏ qua.

        Chống trùng dựa trên nội dung ảnh nên vẫn phải tải về mới biết là trùng.
        Ghi nhớ URL đã thử giúp lượt chạy lại không tải lại những thứ đã biết —
        quan trọng vì crawl hay bị ngắt giữa chừng rồi chạy tiếp.
        """
        return url in self.urls_da_thu

    def ghi_nho_url(self, url: str) -> None:
        self.urls_da_thu.add(url)
        try:
            with self.url_log.open("a", encoding="utf-8") as fh:
                fh.write(url + "\n")
        except OSError:
            pass

    def _nhan(self, row: dict) -> None:
        # Chỉ tin dòng mà file ảnh còn thật trên đĩa.
        if not row.get("ten_file") or not (self.dir / row["ten_file"]).exists():
            return
        self.rows.append(row)
        self.shas.add(row.get("sha256", ""))
        try:
            self.hashes.append(int(row["dhash"]))
        except (ValueError, KeyError, TypeError):
            pass

    def _load(self) -> None:
        if self.index_path.exists():
            for line in self.index_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    try:
                        self._nhan(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        elif self.legacy_csv.exists():
            try:
                with self.legacy_csv.open(newline="", encoding="utf-8-sig") as fh:
                    for row in csv.DictReader(fh):
                        self._nhan(row)
            except OSError:
                pass

        if self.url_log.exists():
            self.urls_da_thu = {
                u.strip() for u in self.url_log.read_text(encoding="utf-8").splitlines() if u.strip()
            }
        # URL của ảnh đã lưu cũng coi như đã thử.
        self.urls_da_thu.update(r.get("url", "") for r in self.rows)

    def __len__(self) -> int:
        return len(self.rows)

    def co_sha(self, sha: str) -> bool:
        return sha in self.shas

    def trung_gan(self, h: int) -> bool:
        return any(hamming(h, old) <= DHASH_THRESHOLD for old in self.hashes)

    def them(self, ten_file: str, sha: str, h: int, nguon: str, url: str,
             extra: dict | None = None) -> None:
        row = {
            "ten_file": ten_file,
            "sha256": sha,
            "dhash": str(h),
            "nguon": nguon,
            "url": url,
        }
        if extra:
            row.update(extra)
        self.rows.append(row)
        self.shas.add(sha)
        self.hashes.append(h)
        try:
            with self.index_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        except OSError as exc:
            # Không để lỗi ghi chỉ mục làm chết cả lượt tải: ảnh vẫn nằm trên đĩa.
            if not self.loi_ghi_index:
                print(f"    !! không ghi được {self.index_path.name}: {exc.strerror}. "
                      f"Đóng file đó trong Excel rồi chạy lại để chỉ mục khớp.")
                self.loi_ghi_index = True


# ------------------------------------------------------------------ xử lý ảnh

THONG_KE_KEYS = [
    "link",
    "tai_loi",
    "khong_phai_anh",
    "anh_nho",
    "trung_tuyet_doi",
    "trung_gan",
    "luu_moi",
]


def nguon_tu_url(url: str) -> str:
    """Suy tên nguồn từ tên miền. Không ai phải gõ cột nguồn bằng tay."""
    host = (urlparse(url).netloc or "").lower()
    if "inaturalist" in host:
        return "inat"
    if "wikimedia" in host or "wikipedia" in host:
        return "wikimedia"
    if "fishbase" in host:
        return "fishbase"
    parts = [p for p in host.split(".") if p not in ("www", "com", "org", "net")]
    name = re.sub(r"[^a-z0-9]", "", parts[0] if parts else "web")
    return (name or "web")[:12]


def tai_mot_url(session: requests.Session, url: str) -> tuple[bytes | None, str]:
    """Tải một URL. Trả về (dữ liệu, lý do lỗi nếu có)."""
    if any(h in url for h in THUMBNAIL_HOSTS):
        return None, "la_anh_thu_nho (URL của Google/Bing, không phải ảnh gốc)"
    try:
        parsed = urlparse(url)
        headers = {
            "User-Agent": UA,
            # Nhiều trang chặn tải trực tiếp; gửi Referer cùng tên miền thì đỡ bị 403.
            "Referer": f"{parsed.scheme}://{parsed.netloc}/",
            "Accept": "image/avif,image/webp,image/*,*/*;q=0.8",
        }
        resp = session.get(url, headers=headers, timeout=30, stream=True)
        if resp.status_code == 403:
            # Một số trang chặn khi thấy Referer; thử lại một lần không gửi Referer.
            headers.pop("Referer", None)
            resp = session.get(url, headers=headers, timeout=30, stream=True)
        if resp.status_code != 200:
            return None, f"HTTP {resp.status_code}"
        ctype = resp.headers.get("Content-Type", "")
        if ctype and not ctype.startswith("image/"):
            return None, f"khong_phai_anh (Content-Type: {ctype[:40]})"
        data = b""
        for chunk in resp.iter_content(65536):
            data += chunk
            if len(data) > MAX_BYTES:
                return None, "qua_lon"
        return data, ""
    except requests.RequestException as exc:
        return None, f"{type(exc).__name__}"


def xu_ly_va_luu(data: bytes, url: str, kho: KhoAnh, nguon: str,
                 extra: dict | None = None) -> str:
    """Lọc rồi lưu một ảnh. Trả về khóa thống kê tương ứng."""
    sha = hashlib.sha256(data).hexdigest()
    if kho.co_sha(sha):
        return "trung_tuyet_doi"

    try:
        Image.open(io.BytesIO(data)).verify()
        img = Image.open(io.BytesIO(data))
        # Phải áp hướng EXIF TRƯỚC khi xóa EXIF, nếu không nhiều ảnh điện thoại
        # sẽ bị nằm ngang và người duyệt loại oan.
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
    except Exception:
        return "khong_phai_anh"

    if max(img.size) < MIN_EDGE:
        return "anh_nho"

    h = dhash(img)
    if kho.trung_gan(h):
        return "trung_gan"

    img.thumbnail((MAX_EDGE, MAX_EDGE), Image.Resampling.LANCZOS)
    ten_file = f"{kho.ma_loai}__{nguon}__{sha[:8]}.jpg"
    img.save(kho.dir / ten_file, "JPEG", quality=JPEG_QUALITY, optimize=True)
    kho.them(ten_file, sha, h, nguon, url, extra)
    return "luu_moi"


# ------------------------------------------------------------------ tìm Bing


def bing_image_urls(session: requests.Session, query: str, want: int, bo_qua=None) -> list[str]:
    """Lấy danh sách URL ảnh gốc từ Bing.

    Gọi thẳng endpoint `images/async` với User-Agent hiện đại. Đây chính là chỗ
    `bing_image_downloader` hỏng: nó gửi UA Chrome 23 (2012) nên Bing trả về
    trang rỗng 972 byte và bắt được 0 link.
    """
    urls: list[str] = []
    seen: set[str] = set()
    first = 0

    while len(urls) < want and first < 1000:
        try:
            resp = session.get(
                "https://www.bing.com/images/async",
                params={"q": query, "first": first, "count": 35, "adlt": "off", "qft": ""},
                headers={"User-Agent": UA},
                timeout=30,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"    lỗi khi tìm Bing: {type(exc).__name__}")
            break

        links = re.findall(r"murl&quot;:&quot;(.*?)&quot;", resp.text)
        if not links:
            break

        for raw in links:
            u = html.unescape(raw)
            if u in seen or not u.startswith("http"):
                continue
            seen.add(u)
            # Lọc URL đã thử NGAY TRONG LÚC PHÂN TRANG, không lọc sau. Nếu lọc
            # sau thì lượt chạy lại chỉ lấy đúng `want` link rồi loại gần hết,
            # còn lại quá ít link mới để bù cho loài đang thiếu.
            if bo_qua and bo_qua(u):
                continue
            urls.append(u)

        first += 35
        time.sleep(1.0)  # giữ nhịp, tránh bị chặn

    return urls[:want]


# ------------------------------------------------- nhập từ thư mục có sẵn


def che_do_nhap(args: argparse.Namespace) -> int:
    """Nhập ảnh từ một thư mục trên đĩa (ví dụ bộ dữ liệu tải sẵn).

    Chạy đúng dây lọc như ảnh tải về từ mạng — áp hướng EXIF, chuyển RGB, loại
    ảnh nhỏ, loại trùng tuyệt đối và trùng gần, resize, đặt tên chuẩn — nên ảnh
    nhập vào không được ưu ái hơn ảnh crawl, và vẫn chống trùng chung một chỉ mục.
    """
    nguon_dir = Path(args.tu)
    if not nguon_dir.is_dir():
        sys.exit(f"Không thấy thư mục {nguon_dir}")
    ma_loai = args.loai_dich.strip().upper()
    hop_le = {r["ma_loai"].strip() for r in load_species(None, True)}
    if ma_loai not in hop_le:
        sys.exit(f"Mã loài {ma_loai} không có trong species.csv")

    kho = KhoAnh(ma_loai, Path(args.out))
    tk = {k: 0 for k in THONG_KE_KEYS}
    files = sorted(
        p for p in nguon_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
    )
    tk["link"] = len(files)
    print(f"Nhập {len(files)} file từ {nguon_dir.name} → {ma_loai}")

    for p in files:
        try:
            data = p.read_bytes()
        except OSError:
            tk["tai_loi"] += 1
            continue
        tk[xu_ly_va_luu(data, f"file://{p}", kho, "archive")] += 1

    in_thong_ke(ma_loai, nguon_dir.name, tk, len(kho))
    return 0


# ------------------------------------------------------------- iNaturalist

INAT_API = "https://api.inaturalist.org/v1"
# Bỏ giấy phép -nd (NoDerivatives): pipeline có crop và tách nền, tức là tạo ra
# tác phẩm phái sinh.
INAT_LICENSES = "cc0,cc-by,cc-by-nc,cc-by-sa,cc-by-nc-sa"
INAT_KICH_THUOC = "large"   # ~1024px, đủ to mà không nặng như `original` (2MB+)
INAT_MIN_GOC = 400          # bỏ ảnh mà bản gốc còn nhỏ hơn mức này


def inat_photo_urls(session: requests.Session, taxon_id: int, want: int,
                    bo_qua=None, chat_luong: str = "research") -> list[tuple[str, str]]:
    """Lấy URL ảnh của một loài từ iNaturalist. Trả về [(url, license_code)].

    Khác hẳn crawl theo từ khóa: ở đây lọc theo **taxon_id**, nên không bao giờ
    trả nhầm loài. Thêm `quality_grade=research` nghĩa là loài đã được cộng đồng
    xác nhận, và lọc giấy phép ngay trong truy vấn.

    **Chỉ lấy ảnh ĐẦU TIÊN của mỗi quan sát.** Một quan sát thường có nhiều ảnh
    của *cùng một con cá* ở các góc khác nhau; lấy hết sẽ làm phương sai nội lớp
    giả tạo thấp đi, và những ảnh đó quá giống nhau để tính là hai mẫu độc lập.
    """
    ket_qua: list[tuple[str, str]] = []
    page = 1

    while len(ket_qua) < want and page <= 50:
        # Thử lại khi lỗi mạng thoáng qua. Thiếu bước này thì một SSLError duy
        # nhất làm hỏng cả loài: lượt chạy 03/10 mất trắng 5 loài vì lý do đó.
        data = None
        for lan in range(1, MAX_RETRIES + 1):
            try:
                # `research` = loài đã được cộng đồng xác nhận.
                # `casual` = chưa xác nhận, GỒM CẢ cá nuôi và cá cảnh — iNaturalist
                # xếp mọi quan sát vật nuôi vào đây. Với cá tra, cá tai tượng thì
                # casual còn nhiều gấp 2–3 lần research. Đổi lại nhãn loài kém
                # tin cậy hơn, nên người duyệt phải kiểm loài kỹ hơn.
                tham_so = {
                    "taxon_id": taxon_id,
                    "photos": "true",
                    "photo_license": INAT_LICENSES,
                    "order_by": "votes",   # ưu tiên ảnh được cộng đồng đánh giá cao
                    "per_page": 200,
                    "page": page,
                }
                if chat_luong != "tat-ca":
                    tham_so["quality_grade"] = chat_luong

                resp = session.get(
                    f"{INAT_API}/observations",
                    params=tham_so,
                    headers={"User-Agent": USER_AGENT_INAT},
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                break
            except (requests.RequestException, ValueError) as exc:
                if lan == MAX_RETRIES:
                    print(f"    bỏ cuộc sau {MAX_RETRIES} lần: {type(exc).__name__}")
                else:
                    cho = 2 ** lan
                    print(f"    {type(exc).__name__} — chờ {cho}s rồi thử lại ({lan}/{MAX_RETRIES})")
                    time.sleep(cho)
        if data is None:
            break

        obs = data.get("results", [])
        if not obs:
            break

        for o in obs:
            anh = (o.get("photos") or [])
            if not anh:
                continue
            ph = anh[0]
            dim = ph.get("original_dimensions") or {}
            if max(dim.get("width", 0), dim.get("height", 0)) < INAT_MIN_GOC:
                continue
            url = (ph.get("url") or "").replace("square.", f"{INAT_KICH_THUOC}.")
            if not url.startswith("http"):
                continue
            if bo_qua and bo_qua(url):
                continue
            ket_qua.append((url, ph.get("license_code") or ""))
            if len(ket_qua) >= want:
                break

        page += 1
        time.sleep(1.0)  # iNaturalist đề nghị giữ dưới ~60 lần gọi API mỗi phút

    return ket_qua


USER_AGENT_INAT = "BTL-CSDLDPT-fish-cbir/0.1 (bai tap lon CSDL Da phuong tien)"


def che_do_inat(args: argparse.Namespace) -> int:
    species = load_species(args.loai, args.ung_vien)
    if not species:
        sys.exit("Không có loài nào để tải.")

    session = requests.Session()
    out_dir = Path(args.out)
    print(f"Tải từ iNaturalist cho {len(species)} loài, tối đa {args.limit} ảnh/loài\n")

    for sp in species:
        ma_loai = sp["ma_loai"].strip()
        taxon = (sp.get("inat_taxon_id") or "").strip()
        if not taxon.isdigit():
            print(f"  {ma_loai:<9} thiếu `inat_taxon_id` — chạy build_species.py trước")
            continue

        kho = KhoAnh(ma_loai, out_dir)
        if len(kho) >= args.muc_tieu:
            print(f"  {ma_loai:<9} đã có {len(kho)} ảnh (mục tiêu {args.muc_tieu}) — bỏ qua")
            continue

        tk = {k: 0 for k in THONG_KE_KEYS}
        can = args.limit - len(kho) if args.bu_cho_du else args.limit
        items = inat_photo_urls(session, int(taxon), max(can, 0),
                                bo_qua=kho.da_thu_url, chat_luong=args.chat_luong)
        tk["link"] = len(items)

        for url, lic in items:
            kho.ghi_nho_url(url)
            data, loi = tai_mot_url(session, url)
            if data is None:
                tk["khong_phai_anh" if "khong_phai_anh" in loi else "tai_loi"] += 1
            else:
                tk[xu_ly_va_luu(data, url, kho, "inat", {"license": lic})] += 1
            time.sleep(0.2)

        in_thong_ke(ma_loai, sp.get("ten_viet") or ma_loai, tk, len(kho))

    return 0


# ---------------------------------------------------------------- FishBase

FISHBASE_MIRRORS = ("https://www.fishbase.se", "https://www.fishbase.de")


def fishbase_speccode(session: requests.Session, ten_khoa_hoc: str) -> tuple[int | None, str]:
    """Tra SpecCode của FishBase từ tên khoa học.

    Trang `summary/<Chi>-<loài>.html` tra được trực tiếp bằng tên, không cần
    biết SpecCode trước. Nhờ vậy cột `fishbase_id` trong species.csv không phải
    điền tay — script tự lấy rồi ghi lại vào file.
    """
    parts = ten_khoa_hoc.strip().split()
    if len(parts) < 2:
        return None, "tên khoa học không hợp lệ"
    slug = f"{parts[0].capitalize()}-{parts[1].lower()}"

    for base in FISHBASE_MIRRORS:
        try:
            resp = session.get(
                f"{base}/summary/{slug}.html", headers={"User-Agent": UA}, timeout=30
            )
            if resp.status_code != 200:
                continue
            m = re.search(r"ThumbnailsSummary\.php\?ID=(\d+)", resp.text)
            if not m:
                m = re.search(r"[Ss]pec[Cc]ode[\"'=:>\s]+(\d+)", resp.text)
            if m:
                return int(m.group(1)), base
            return None, f"không thấy SpecCode trên trang {slug}"
        except requests.RequestException:
            continue
    return None, "không truy cập được FishBase"


def fishbase_image_urls(session: requests.Session, speccode: int, base: str) -> list[str]:
    """Lấy URL ảnh đầy đủ từ thư viện ảnh của một loài trên FishBase.

    Trang thư viện chứa cả ảnh thu nhỏ (`images/thumbnails/...`) và ảnh đầy đủ
    (`images/species/...`) — chỉ lấy loại thứ hai.

    Bỏ file `.gif`: trên FishBase đó thường là **hình vẽ** chứ không phải ảnh
    chụp, mà hình vẽ thuộc diện phải loại theo checklist. Lọc ngay ở đây đỡ cho
    người duyệt. Với cá chép: 36 ảnh jpg và 14 hình vẽ gif.
    """
    try:
        resp = session.get(
            f"{base}/photos/ThumbnailsSummary.php?ID={speccode}",
            headers={"User-Agent": UA},
            timeout=30,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"    lỗi mở thư viện ảnh: {type(exc).__name__}")
        return []

    duong_dan = re.findall(r"src=[\"'](?:\.\./)?(images/species/[^\"']+)[\"']", resp.text)
    ket_qua: list[str] = []
    for p in dict.fromkeys(duong_dan):
        if p.lower().endswith((".jpg", ".jpeg", ".png")):
            ket_qua.append(f"{base}/{p}")
    return ket_qua


def ghi_speccode(ma_loai_den_speccode: dict[str, int]) -> int:
    """Ghi SpecCode vừa tra được vào cột `fishbase_id` của species.csv.

    Chỉ điền vào ô đang trống, và giữ nguyên đúng thứ tự cột của file hiện có
    để không làm mất những chỉnh sửa tay khác.
    """
    if not ma_loai_den_speccode:
        return 0
    with SPECIES_CSV.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        cot = list(reader.fieldnames or [])
        rows = list(reader)
    if "fishbase_id" not in cot:
        return 0

    da_ghi = 0
    for r in rows:
        ma = (r.get("ma_loai") or "").strip()
        if ma in ma_loai_den_speccode and not (r.get("fishbase_id") or "").strip():
            r["fishbase_id"] = str(ma_loai_den_speccode[ma])
            da_ghi += 1
    if da_ghi:
        tmp = SPECIES_CSV.with_suffix(".csv.tmp")
        with tmp.open("w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, fieldnames=cot, lineterminator="\n", extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        tmp.replace(SPECIES_CSV)
    return da_ghi


def che_do_fishbase(args: argparse.Namespace) -> int:
    species = load_species(args.loai, args.ung_vien)
    if not species:
        sys.exit("Không có loài nào để tải.")

    session = requests.Session()
    out_dir = Path(args.out)
    speccode_moi: dict[str, int] = {}
    print(f"Tải từ FishBase cho {len(species)} loài, tối đa {args.limit} ảnh/loài\n")

    for sp in species:
        ma_loai = sp["ma_loai"].strip()
        ten_kh = (sp.get("ten_khoa_hoc") or "").strip()

        code = (sp.get("fishbase_id") or "").strip()
        if code.isdigit():
            speccode, base = int(code), FISHBASE_MIRRORS[0]
        else:
            speccode, base = fishbase_speccode(session, ten_kh)
            if speccode:
                speccode_moi[ma_loai] = speccode
            time.sleep(1.0)  # FishBase là trang học thuật phi lợi nhuận — gọi chậm
        if not speccode:
            print(f"  {ma_loai:<9} không tra được SpecCode: {base}")
            continue

        kho = KhoAnh(ma_loai, out_dir)
        tk = {k: 0 for k in THONG_KE_KEYS}
        urls = fishbase_image_urls(session, speccode, base)[: args.limit]
        tk["link"] = len(urls)

        for url in urls:
            data, loi = tai_mot_url(session, url)
            if data is None:
                tk["khong_phai_anh" if "khong_phai_anh" in loi else "tai_loi"] += 1
            else:
                tk[xu_ly_va_luu(data, url, kho, "fishbase")] += 1
            time.sleep(0.5)

        in_thong_ke(ma_loai, f"{sp.get('ten_viet') or ten_kh} (SpecCode {speccode})", tk, len(kho))

    n = ghi_speccode(speccode_moi)
    if n:
        print(f"\nĐã ghi {n} SpecCode vào cột `fishbase_id` của species.csv — "
              f"không cần tra tay nữa.")
    return 0


# -------------------------------------------------------------------- loài


def load_species(only: list[str] | None, gom_ung_vien: bool) -> list[dict]:
    if not SPECIES_CSV.exists():
        sys.exit(f"Không thấy {SPECIES_CSV}")
    with SPECIES_CSV.open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))

    def nhan(r: dict) -> bool:
        tt = (r.get("trang_thai") or "").strip()
        return tt == "da_chot" or (gom_ung_vien and tt == "ung_vien")

    rows = [r for r in rows if (r.get("ma_loai") or "").strip() and nhan(r)]
    if only:
        want = {m.strip().upper() for m in only}
        found = {(r.get("ma_loai") or "").strip() for r in rows}
        for m in want - found:
            print(f"  cảnh báo: không có loài {m} (hoặc không ở trạng thái da_chot)")
        rows = [r for r in rows if (r.get("ma_loai") or "").strip() in want]
    return rows


def in_thong_ke(ma_loai: str, ten: str, tk: dict, tong: int) -> None:
    thieu = max(0, TARGET_PER_SPECIES - tong)
    print(
        f"  {ma_loai:<9} {ten[:26]:<27} "
        f"link {tk['link']:>4} | lưu mới {tk['luu_moi']:>4} | "
        f"trùng {tk['trung_tuyet_doi'] + tk['trung_gan']:>4} | "
        f"nhỏ {tk['anh_nho']:>3} | lỗi {tk['tai_loi'] + tk['khong_phai_anh']:>3} | "
        f"tổng có {tong:>4}" + (f" | còn thiếu {thieu}" if thieu else " | ĐỦ")
    )


# ------------------------------------------------------------- chế độ crawl


def che_do_crawl(args: argparse.Namespace) -> int:
    species = load_species(args.loai, args.ung_vien)
    if not species:
        sys.exit("Không có loài nào để tải.")

    session = requests.Session()
    out_dir = Path(args.out)
    print(f"Crawl Bing cho {len(species)} loài, mỗi loài tối đa {args.limit} link\n")

    for sp in species:
        ma_loai = sp["ma_loai"].strip()
        truy_van = (sp.get("ten_khoa_hoc") or "").strip()
        if args.them_tu_khoa:
            truy_van = f"{truy_van} {args.them_tu_khoa}"

        kho = KhoAnh(ma_loai, out_dir)
        if len(kho) >= args.muc_tieu:
            print(f"  {ma_loai:<9} đã có {len(kho)} ảnh (mục tiêu {args.muc_tieu}) — bỏ qua")
            continue

        tk = {k: 0 for k in THONG_KE_KEYS}
        urls = bing_image_urls(session, truy_van, args.limit, bo_qua=kho.da_thu_url)
        tk["link"] = len(urls)

        for url in urls:
            kho.ghi_nho_url(url)
            data, loi = tai_mot_url(session, url)
            if data is None:
                tk["khong_phai_anh" if "khong_phai_anh" in loi else "tai_loi"] += 1
            else:
                tk[xu_ly_va_luu(data, url, kho, "bing")] += 1
            time.sleep(0.2)


        in_thong_ke(ma_loai, sp.get("ten_viet") or truy_van, tk, len(kho))

    return 0


# ---------------------------------------------------------------- chế độ url


def che_do_url(args: argparse.Namespace) -> int:
    csv_path = Path(args.csv)
    if not csv_path.exists():
        sys.exit(f"Không thấy {csv_path}. Tải Sheet về: File → Download → CSV")

    hop_le = {r["ma_loai"].strip() for r in load_species(None, True)}
    with csv_path.open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    if not rows or "url" not in rows[0] or "ma_loai" not in rows[0]:
        sys.exit("File CSV phải có ít nhất hai cột: ma_loai, url")

    # Gom theo loài, bỏ URL trùng (hai người nộp cùng một link).
    theo_loai: dict[str, list[dict]] = {}
    loi_rows: list[dict] = []
    da_thay: dict[str, str] = {}  # url -> ma_loai đã nhận url đó

    for r in rows:
        ma_loai = (r.get("ma_loai") or "").strip().upper()
        url = (r.get("url") or "").strip()
        nguoi = (r.get("nguoi_nop") or "").strip()
        if not url:
            continue
        if ma_loai not in hop_le:
            loi_rows.append({**r, "ly_do": f"ma_loai '{ma_loai}' không có trong species.csv"})
            continue
        if url in da_thay:
            # Cùng URL cho hai loài khác nhau là xung đột nhãn, không phải trùng
            # lặp bình thường — một trong hai người đã gán sai loài.
            if da_thay[url] != ma_loai:
                loi_rows.append({**r, "ly_do": f"XUNG DOT NHAN: URL này cũng được nộp cho {da_thay[url]}"})
            else:
                loi_rows.append({**r, "ly_do": "URL trùng với dòng khác"})
            continue
        da_thay[url] = ma_loai
        theo_loai.setdefault(ma_loai, []).append({"url": url, "nguoi_nop": nguoi})

    session = requests.Session()
    out_dir = Path(args.out)
    print(f"Tải từ {csv_path.name}: {len(da_thay)} URL hợp lệ, {len(theo_loai)} loài\n")

    for ma_loai, items in sorted(theo_loai.items()):
        kho = KhoAnh(ma_loai, out_dir)
        tk = {k: 0 for k in THONG_KE_KEYS}
        tk["link"] = len(items)

        for it in items:
            url = it["url"]
            data, loi = tai_mot_url(session, url)
            if data is None:
                tk["khong_phai_anh" if "khong_phai_anh" in loi else "tai_loi"] += 1
                loi_rows.append({"ma_loai": ma_loai, "url": url,
                                 "nguoi_nop": it["nguoi_nop"], "ly_do": loi})
            else:
                kq = xu_ly_va_luu(data, url, kho, nguon_tu_url(url))
                tk[kq] += 1
                if kq in ("anh_nho", "khong_phai_anh"):
                    loi_rows.append({"ma_loai": ma_loai, "url": url,
                                     "nguoi_nop": it["nguoi_nop"], "ly_do": kq})
            time.sleep(0.2)

        in_thong_ke(ma_loai, "", tk, len(kho))

    if loi_rows:
        loi_path = csv_path.parent / "urls_loi.csv"
        with loi_path.open("w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.DictWriter(
                fh, fieldnames=["ma_loai", "url", "nguoi_nop", "ly_do"],
                extrasaction="ignore", lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(loi_rows)
        print(f"\n{len(loi_rows)} URL có vấn đề → {loi_path}")
        print("Dán file này vào tab `loi` của Sheet để người nộp tự bù.")

    return 0


# ------------------------------------------------------------- chế độ báo cáo


def che_do_bao_cao(args: argparse.Namespace) -> int:
    species = load_species(args.loai, args.ung_vien)
    out_dir = Path(args.out)
    tong_cong = 0
    thieu_loai = []

    print(f"{'ma_loai':<9} {'tên Việt':<24} {'có':>5} {'mục tiêu':>9} {'thiếu':>6}")
    print("-" * 58)
    for sp in species:
        ma_loai = sp["ma_loai"].strip()
        n = len(KhoAnh(ma_loai, out_dir))
        thieu = max(0, TARGET_PER_SPECIES - n)
        tong_cong += n
        if thieu:
            thieu_loai.append(ma_loai)
        print(f"{ma_loai:<9} {(sp.get('ten_viet') or '')[:23]:<24} {n:>5} "
              f"{TARGET_PER_SPECIES:>9} {thieu if thieu else '-':>6}")

    print("-" * 58)
    print(f"Tổng: {tong_cong} ảnh / {len(species)} loài")
    if thieu_loai:
        print(f"Còn thiếu ở {len(thieu_loai)} loài: {' '.join(thieu_loai)}")
    else:
        print("Mọi loài đã đủ. Copy work/anh/ lên Drive để cả nhóm duyệt.")
    return 0


# --------------------------------------------------------------------- main


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    # Cờ dùng chung cho mọi chế độ. Khai báo qua parser cha `parents=[...]` để
    # gõ được SAU tên chế độ (`crawl --loai CYP_CAR`), đúng thứ tự tự nhiên.
    chung = argparse.ArgumentParser(add_help=False)
    chung.add_argument("--out", default=str(OUT_DIR), help="thư mục ảnh ra")
    chung.add_argument("--loai", nargs="*", help="chỉ làm các mã loài này")
    chung.add_argument("--ung-vien", action="store_true", help="gồm cả loài ung_vien")

    sub = ap.add_subparsers(dest="che_do", required=True)

    c = sub.add_parser("crawl", parents=[chung], help="tìm và tải từ Bing theo tên khoa học")
    c.add_argument("--limit", type=int, default=250, help="số link mỗi loài (mặc định 250)")
    c.add_argument("--them-tu-khoa", default="", help="thêm từ khóa, ví dụ 'whole fish'")
    # Mục tiêu tính trên ảnh THÔ. Sau chuẩn hóa và duyệt sẽ rụng đi khá nhiều,
    # nên đặt cao hơn 70 để còn đủ. `--bo-qua-du` cũ là cờ store_true mặc định
    # True nên không bao giờ tắt được — thay bằng ngưỡng số cho rõ ràng.
    c.add_argument("--muc-tieu", type=int, default=TARGET_PER_SPECIES,
                   help=f"có đủ bấy nhiêu ảnh thô thì bỏ qua loài (mặc định {TARGET_PER_SPECIES})")

    i = sub.add_parser("inat", parents=[chung], help="tải từ iNaturalist theo taxon_id")
    i.add_argument("--limit", type=int, default=150, help="số ảnh mỗi loài (mặc định 150)")
    i.add_argument("--muc-tieu", type=int, default=TARGET_PER_SPECIES,
                   help=f"có đủ bấy nhiêu ảnh thô thì bỏ qua loài (mặc định {TARGET_PER_SPECIES})")
    i.add_argument("--bu-cho-du", action="store_true",
                   help="chỉ tải thêm cho đủ --limit, tính cả ảnh đã có")
    i.add_argument("--chat-luong", choices=["research", "casual", "tat-ca"],
                   default="research",
                   help="research = loài đã được cộng đồng xác nhận (mặc định); "
                        "casual = chưa xác nhận, GỒM cá nuôi và cá cảnh; tat-ca = cả hai")

    f = sub.add_parser("fishbase", parents=[chung], help="tải ảnh mẫu vật từ FishBase")
    f.add_argument("--limit", type=int, default=40, help="số ảnh mỗi loài (mặc định 40)")

    u = sub.add_parser("url", parents=[chung], help="tải từ danh sách URL (CSV xuất từ Google Sheet)")
    u.add_argument("--csv", default=str(ROOT / "work" / "urls.csv"))

    n = sub.add_parser("nhap", parents=[chung], help="nhập ảnh từ một thư mục có sẵn trên đĩa")
    n.add_argument("--tu", required=True, help="thư mục nguồn")
    n.add_argument("--loai-dich", required=True, help="mã loài đích, ví dụ BET_SPL")

    sub.add_parser("bao-cao", parents=[chung], help="đếm ảnh hiện có theo loài")

    args = ap.parse_args()
    if args.che_do == "crawl":
        return che_do_crawl(args)
    if args.che_do == "nhap":
        return che_do_nhap(args)
    if args.che_do == "inat":
        return che_do_inat(args)
    if args.che_do == "fishbase":
        return che_do_fishbase(args)
    if args.che_do == "url":
        return che_do_url(args)
    return che_do_bao_cao(args)


if __name__ == "__main__":
    sys.exit(main())
