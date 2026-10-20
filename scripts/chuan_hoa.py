"""Chuẩn hóa ảnh cá về 256×256 — bước sau `tai_anh.py`, trước khi trích đặc trưng.

    work/anh/<ma_loai>/*.jpg  →  work/chuan/<ma_loai>/<sha8>.png  (RGBA 256×256)

Thiết kế xuất phát từ câu hỏi: **resize ảnh hưởng thế nào tới từng nhóm đặc trưng?**

    Màu (①②③)         bất biến tỉ lệ — đều là thống kê chuẩn hóa theo số pixel
    Hình dáng (⑦⑧⑨⑩)   bất biến tỉ lệ theo công thức, nhưng mask răng cưa của
                        ảnh nhỏ làm lệch hệ số Fourier bậc cao
    Kết cấu (④⑤⑥)      KHÔNG bất biến. LBP và GLCM đo quan hệ giữa các pixel kề
                        nhau, Gabor đo tần số không gian — đổi tỉ lệ là đổi hẳn
                        giá trị đặc trưng

Nhóm kết cấu là ràng buộc, và nó dẫn tới bốn quyết định:

1.  **Chuẩn hóa CON CÁ, không phải khung ảnh.** Cắt theo hộp bao mask rồi đưa
    cạnh dài của cá về đúng `TARGET_FISH` px. Nhờ vậy mọi con cá đều ở cùng một
    độ phân giải, LBP và GLCM mới so sánh được với nhau.

2.  **Không bao giờ phóng to.** Cá nhỏ hơn `MIN_FISH` px thì loại. Phóng to tạo
    pixel nội suy trơn: LBP dồn vào bin "phẳng", GLCM contrast sụp. Ảnh mờ sẽ
    giống nhau *vì đều mờ* chứ không vì cùng loài — cùng loại lỗi với bẫy nền.

3.  **Chỉ lấy mẫu lại MỘT lần.** Xoay rồi mới resize là hai lần làm nhòe. Ở đây
    xoay + lật + thu nhỏ + căn giữa được gộp thành một phép affine duy nhất.

4.  **Ghi lại hệ số thu nhỏ của từng ảnh.** Ảnh gốc 1600px và ảnh gốc 300px tuy
    cùng về 256 nhưng ảnh thứ nhất bị lọc tần số cao nhiều hơn. Không khử được
    triệt để, nên ghi lại `he_so_scale` để ở bước đánh giá kiểm xem độ phân giải
    có tương quan với lỗi nhận dạng hay không, thay vì đoán.

Cách dùng:

    python scripts/chuan_hoa.py                      # mọi loài da_chot
    python scripts/chuan_hoa.py --loai CYP_CAR
    python scripts/chuan_hoa.py --loai CYP_CAR --xem-thu 6   # xuất ảnh đối chiếu

Phụ thuộc: rembg, Pillow, numpy. Lần chạy đầu rembg tải model ~170MB.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import deque
from pathlib import Path

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
SPECIES_CSV = ROOT / "data_meta" / "species.csv"
IN_DIR = ROOT / "work" / "anh"
OUT_DIR = ROOT / "work" / "chuan"
LOAI_DIR = ROOT / "work" / "loai"      # nơi `ap_dung_lat.py` cất ảnh bị loại

# Canvas 384 chốt ngày 03/10 dựa trên phân bố kích thước cá đo thật trên ba
# nguồn: giữ được 91% ảnh iNaturalist, 90% FishBase, 97% Archive — mất 7% ảnh
# để đổi lấy ~50% chi tiết kết cấu (6,3 → 9,4 px mỗi hàng vảy ước tính).
# Không lên 448 vì mất 16% ảnh mà chỉ thêm 1,6 px.
CANVAS = 384            # ảnh ra: CANVAS × CANVAS
TARGET_FISH = 348       # cạnh dài con cá trong ảnh ra, chừa lề 18px mỗi bên
MIN_FISH = 348          # cá nhỏ hơn mức này thì loại — tránh phóng to
MIN_MASK_PCT = 2.0      # mask nhỏ hơn % này so với ảnh thì coi như rembg hỏng
NGUONG_THON = 1.5       # dưới mức này thì trục chính không đáng tin → không xoay
MANH_CHINH_PCT = 70.0   # mảnh lớn nhất phải chiếm ít nhất % này của mask
NEN = (128, 128, 128)   # nền xám trung tính: không màu, ít tạo biên giả

LY_DO = {
    "mask_rong": "rembg không tìm thấy cá",
    "ca_qua_nho": f"cá ngắn hơn {MIN_FISH}px — resize sẽ là phóng to",
    "nhieu_manh": "mask vỡ thành nhiều mảnh — có thể nhiều con cá hoặc tách nền sai",
}


# ------------------------------------------------------------------ hình học


def do_net(rgb: Image.Image, alpha: Image.Image) -> float:
    """Phương sai Laplacian tính CHỈ bên trong thân cá, đã bỏ vùng biên.

    Ghi lại để bước đánh giá kiểm xem độ nét có tương quan với lỗi nhận dạng
    không — các nguồn ảnh có độ nét khác nhau (đo ngày 03/10: FishBase 3573,
    iNaturalist 2493, Archive 2110), và nếu hệ "nhận ra" loài qua độ nét thay vì
    hình thái thì đó là cùng loại lỗi với bẫy nền.

    Phải bỏ vùng biên: nền đã bị xóa nên ranh giới cá/nền là một cạnh cực sắc,
    tính cả vào thì chỉ số bị phồng lên vài lần và vô nghĩa.
    """
    m = np.asarray(alpha.filter(ImageFilter.MinFilter(15))) > 127
    if m.sum() < 500:
        return 0.0
    a = np.asarray(rgb.convert("L"), dtype=np.float64)
    k = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float64)
    lap = (sliding_window_view(a, (3, 3)) * k).sum(axis=(2, 3))
    return float(lap[m[1:-1, 1:-1]].var())


def do_thon(mask: np.ndarray) -> float:
    """Tỉ số hai trục chính = sqrt(λ1/λ2). Tròn = 1, thon dài = lớn.

    Dùng để biết **trục chính có đáng tin không**. Với bóng cá gần tròn, hướng
    của trục chính do nhiễu quyết định chứ không do hình dạng, nên xoay theo nó
    là xoay bừa. Đo ngày 10/10: cá dĩa 1,29 (gần tròn) nên 86% ảnh bị xoay hơn
    60° dù ảnh gốc đã nằm ngang đúng; cá xiêm 1,44 vì vây xòe rộng làm bóng cá
    tròn ra.
    """
    ys, xs = np.nonzero(mask)
    x = xs - xs.mean()
    y = ys - ys.mean()
    cov = np.array([[(x * x).mean(), (x * y).mean()],
                    [(x * y).mean(), (y * y).mean()]])
    w = np.linalg.eigvalsh(cov)
    return float(np.sqrt(max(w) / max(min(w), 1e-9)))


def moment_truc_chinh(mask: np.ndarray) -> tuple[float, float, float]:
    """Trả về (cx, cy, góc trục chính theo radian).

    Góc từ công thức 0.5·atan2(2μ11, μ20−μ02) luôn nằm trong (−90°, 90°], nên
    phép xoay tự động bị giới hạn ±90° — không bao giờ tự quay thêm 180° làm
    đảo đầu đuôi. Đó là ràng buộc đã ghi trong kế hoạch, ở đây có sẵn miễn phí.
    """
    ys, xs = np.nonzero(mask)
    cx, cy = xs.mean(), ys.mean()
    dx, dy = xs - cx, ys - cy
    mu20 = (dx * dx).mean()
    mu02 = (dy * dy).mean()
    mu11 = (dx * dy).mean()
    theta = 0.5 * math.atan2(2.0 * mu11, mu20 - mu02)
    return float(cx), float(cy), float(theta)


def xoay_diem(xs: np.ndarray, ys: np.ndarray, cx: float, cy: float, alpha: float):
    ca, sa = math.cos(alpha), math.sin(alpha)
    dx, dy = xs - cx, ys - cy
    return ca * dx - sa * dy, sa * dx + ca * dy


def manh_lon_nhat_pct(mask: np.ndarray) -> float:
    """% diện tích mask thuộc về mảnh liên thông lớn nhất.

    Thấp nghĩa là mask vỡ — thường do ảnh có nhiều con cá, hoặc rembg bắt nhầm
    thêm vật khác. Đây là cách tự động bắt lỗi "nhiều cá trong một ảnh" (R-anh),
    đỡ cho người duyệt. Chạy trên bản thu nhỏ để nhanh.
    """
    # Lưới 256 chứ không phải 128: thu nhỏ quá mạnh làm ĐỨT những phần mảnh như
    # cuống đuôi, rồi báo oan ảnh một con cá là "nhiều mảnh".
    small = np.array(
        Image.fromarray((mask * 255).astype(np.uint8)).resize((256, 256), Image.Resampling.NEAREST)
    ) > 127
    if not small.any():
        return 0.0

    seen = np.zeros_like(small, dtype=bool)
    tong = int(small.sum())
    lon_nhat = 0
    h, w = small.shape
    for sy in range(h):
        for sx in range(w):
            if not small[sy, sx] or seen[sy, sx]:
                continue
            dem = 0
            q = deque([(sy, sx)])
            seen[sy, sx] = True
            while q:
                y, x = q.popleft()
                dem += 1
                for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                    if 0 <= ny < h and 0 <= nx < w and small[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        q.append((ny, nx))
            lon_nhat = max(lon_nhat, dem)
    return 100.0 * lon_nhat / tong


def doan_huong(mask: np.ndarray, cx: float, cy: float, alpha: float) -> tuple[str, float]:
    """Đoán đầu cá quay về bên nào, dựa trên bề dày thân ở hai đầu.

    Phía đuôi thon hơn phía đầu. So bề dày trung bình ở 20% ngoài cùng mỗi bên.
    Trả về ('L' hoặc 'R', tỉ số tin cậy). Đây chỉ là phỏng đoán — khi có cột
    `huong` do người duyệt ghi thì luôn ưu tiên dùng cột đó.
    """
    ys, xs = np.nonzero(mask)
    rx, ry = xoay_diem(xs.astype(float), ys.astype(float), cx, cy, -alpha)
    lo, hi = rx.min(), rx.max()
    span = hi - lo
    if span <= 0:
        return "L", 1.0
    bien = 0.2 * span
    trai = ry[rx < lo + bien]
    phai = ry[rx > hi - bien]
    day_trai = (trai.max() - trai.min()) if trai.size else 0.0
    day_phai = (phai.max() - phai.min()) if phai.size else 0.0
    if day_trai <= 0 or day_phai <= 0:
        return "L", 1.0
    # Bên dày hơn là phía đầu.
    if day_trai >= day_phai:
        return "L", float(day_trai / day_phai)
    return "R", float(day_phai / day_trai)


def affine_mot_lan(cx, cy, alpha, scale, lat: bool):
    """Hệ số affine cho PIL: gộp xoay + thu nhỏ + căn giữa + lật thành một phép.

    PIL ánh xạ điểm RA (x, y) về điểm VÀO (a·x + b·y + c, d·x + e·y + f), nên
    phải dựng phép biến đổi NGƯỢC.

    Gộp làm một là có chủ đích: xoay rồi resize là hai lần nội suy, làm nhòe
    kết cấu gấp đôi — mà kết cấu chính là thứ LBP, GLCM và Gabor đo.
    """
    ca, sa = math.cos(alpha), math.sin(alpha)
    t = CANVAS / 2.0
    a = ca / scale
    b = sa / scale
    c = cx - (ca * t + sa * t) / scale
    d = -sa / scale
    e = ca / scale
    f = cy - (-sa * t + ca * t) / scale
    if lat:
        # Thay x bằng (CANVAS-1-x) rồi khai triển lại.
        a, c = -a, a * (CANVAS - 1) + c
        d, f = -d, d * (CANVAS - 1) + f
    return (a, b, c, d, e, f)


# ----------------------------------------------------------------- xử lý ảnh


def chuan_hoa_mot_anh(img: Image.Image, mask_img: Image.Image, huong: str | None,
                      khong_xoay: bool = False):
    """Trả về (ảnh RGBA 256×256, thông tin) hoặc (None, thông tin có 'ly_do')."""
    mask = np.array(mask_img) > 127
    tong_px = mask.size
    if mask.sum() < tong_px * MIN_MASK_PCT / 100.0:
        return None, {"ly_do": "mask_rong"}

    thon = do_thon(mask)
    cx, cy, theta = moment_truc_chinh(mask)

    # Ảnh nguồn Archive VỐN ĐÃ nằm ngang đúng chuẩn đề bài → không xoay, để
    # người duyệt tự chỉnh bằng A/W/D/S. Mọi nguồn khác thì xoay theo trục chính.
    #
    # Người duyệt chốt tư thế dựa trên ẢNH ĐÃ CHUẨN HÓA, nên đổi cách xoay là
    # làm sai lệch nhãn họ đã ghi. Chỉ đổi khi chấp nhận duyệt lại phần đó.
    #
    # Một ý tưởng từng thử rồi bỏ: bỏ qua xoay khi `do_thon < NGUONG_THON` vì
    # trục chính không đáng tin với cá gần tròn. Bỏ vì nó cũng tác động tới ảnh
    # FishBase và iNaturalist đã duyệt xong. Vẫn ghi `do_thon` vào metadata.
    xoay_bo_qua = khong_xoay
    alpha = 0.0 if xoay_bo_qua else -theta

    # Đo cá trong hệ đã xoay, không cần xoay ảnh thật.
    ys, xs = np.nonzero(mask)
    rx, ry = xoay_diem(xs.astype(float), ys.astype(float), cx, cy, alpha)
    dai = float(rx.max() - rx.min())
    cao = float(ry.max() - ry.min())
    ca_px = max(dai, cao)

    if ca_px < MIN_FISH:
        return None, {"ly_do": "ca_qua_nho", "ca_px": round(ca_px, 1)}

    # Đếm mảnh SAU phép kiểm kích thước: trên mask nhỏ, phần mảnh như cuống đuôi
    # dễ bị đứt và gây báo oan. Đặt sau nên chỉ chạy trên mask đủ lớn, đáng tin hơn.
    pct = manh_lon_nhat_pct(mask)
    if pct < MANH_CHINH_PCT:
        return None, {"ly_do": "nhieu_manh", "manh_chinh_pct": round(pct, 1)}

    scale = TARGET_FISH / ca_px

    # Căn giữa theo TÂM HỘP BAO, không theo trọng tâm. Thân cá nặng hơn đuôi nên
    # trọng tâm lệch về phía đầu; lấy trọng tâm làm tâm thì đuôi dài có thể lọt
    # ra ngoài canvas 256px và BỊ CẮT MẤT — hỏng luôn đặc trưng hình dáng.
    bx = (rx.min() + rx.max()) / 2.0
    by = (ry.min() + ry.max()) / 2.0
    ca_, sa_ = math.cos(-alpha), math.sin(-alpha)
    cx = cx + (ca_ * bx - sa_ * by)
    cy = cy + (sa_ * bx + ca_ * by)
    huong_doan, tin_cay = doan_huong(mask, cx, cy, alpha)
    huong_dung = huong or huong_doan
    lat = huong_dung.upper() == "R"  # quy ước: mọi con cá quay đầu sang TRÁI

    he_so = affine_mot_lan(cx, cy, alpha, scale, lat)

    nen = Image.new("RGB", img.size, NEN)
    nen.paste(img, (0, 0), mask_img)  # xóa nền trước khi biến đổi
    # fillcolor=NEN: vùng nằm ngoài ảnh gốc sau khi xoay phải cùng màu nền xám,
    # không để mặc định màu đen — nếu không sẽ tạo thêm một biên giả sắc nét,
    # đúng thứ làm hỏng LBP và GLCM nếu có đoạn nào quên dùng mask.
    rgb = nen.transform(
        (CANVAS, CANVAS), Image.Transform.AFFINE, he_so,
        resample=Image.Resampling.BICUBIC, fillcolor=NEN,
    )
    alpha_ch = mask_img.transform(
        (CANVAS, CANVAS), Image.Transform.AFFINE, he_so, resample=Image.Resampling.NEAREST
    )
    ra = rgb.convert("RGBA")
    ra.putalpha(alpha_ch)

    return ra, {
        "do_net": round(do_net(rgb, alpha_ch), 1),
        "do_thon": round(thon, 2),
        "xoay_bo_qua": xoay_bo_qua,
        "goc_xoay_do": round(math.degrees(alpha), 2),
        "ca_px_goc": round(ca_px, 1),
        "he_so_scale": round(scale, 4),
        "lat": lat,
        "huong": huong_dung.upper(),
        "huong_nguon": "review" if huong else "heuristic",
        "huong_tin_cay": round(tin_cay, 2),
        "manh_chinh_pct": round(pct, 1),
        "ty_le_dai_cao": round(dai / cao, 3) if cao else None,
    }


# ------------------------------------------------------------------ chạy lô


def doc_huong(ma_loai: str) -> dict[str, str]:
    """Đọc cột `huong` người duyệt đã ghi, nếu có."""
    p = ROOT / "data_meta" / "review" / f"{ma_loai}.r1.csv"
    if not p.exists():
        return {}
    out = {}
    with p.open(newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            h = (r.get("huong") or "").strip().upper()
            tf = (r.get("image_id") or r.get("ten_file") or "").strip()
            if h in ("L", "R") and tf:
                out[Path(tf).stem] = h
    return out


def load_species(only, gom_ung_vien: bool) -> list[dict]:
    with SPECIES_CSV.open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    rows = [
        r for r in rows
        if (r.get("ma_loai") or "").strip()
        and ((r.get("trang_thai") or "").strip() == "da_chot"
             or (gom_ung_vien and (r.get("trang_thai") or "").strip() == "ung_vien"))
    ]
    if only:
        want = {m.upper() for m in only}
        rows = [r for r in rows if r["ma_loai"].strip() in want]
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--in-dir", default=str(IN_DIR))
    ap.add_argument("--out", default=str(OUT_DIR))
    ap.add_argument("--loai", nargs="*")
    ap.add_argument("--ung-vien", action="store_true")
    ap.add_argument("--lam-lai", action="store_true", help="xử lý lại ảnh đã có")
    ap.add_argument("--xem-thu", type=int, default=0,
                    help="xuất N ảnh đối chiếu gốc|mask|kết quả vào _xem_thu/")
    args = ap.parse_args()

    try:
        from rembg import new_session, remove
    except ImportError:
        sys.exit("Chưa cài rembg. Chạy: pip install rembg")

    print("Nạp model rembg (lần đầu tải ~170MB)...")
    session = new_session("u2net")

    in_dir, out_dir = Path(args.in_dir), Path(args.out)
    species = load_species(args.loai, args.ung_vien)
    tong = {"ok": 0, "mask_rong": 0, "ca_qua_nho": 0, "nhieu_manh": 0, "bo_qua": 0}
    ca_px_tat_ca: list[float] = []

    for sp in species:
        ma_loai = sp["ma_loai"].strip()
        thu_muc_vao = in_dir / ma_loai
        if not thu_muc_vao.exists():
            continue
        thu_muc_ra = out_dir / ma_loai
        thu_muc_ra.mkdir(parents=True, exist_ok=True)
        meta_path = thu_muc_ra / "_meta.jsonl"
        huong_map = doc_huong(ma_loai)

        dem = {"ok": 0, "mask_rong": 0, "ca_qua_nho": 0, "nhieu_manh": 0, "bo_qua": 0}
        xem_thu_con = args.xem_thu

        for p in sorted(thu_muc_vao.glob("*.jpg")):
            ten_ra = p.stem + ".png"
            dich = thu_muc_ra / ten_ra
            # Phải kiểm CẢ work/loai: ảnh người duyệt đã loại được `ap_dung_lat`
            # chuyển sang đó, nên nếu chỉ kiểm work/chuan thì lần chạy sau sẽ
            # tưởng chúng chưa xử lý, sinh lại và đưa ngược vào bộ dữ liệu.
            da_bi_loai = (LOAI_DIR / ma_loai / ten_ra).exists()
            if (dich.exists() or da_bi_loai) and not args.lam_lai:
                dem["bo_qua"] += 1
                continue

            try:
                img = Image.open(p).convert("RGB")
                mask_img = remove(img, session=session, only_mask=True)
            except Exception as exc:
                print(f"    lỗi rembg {p.name}: {type(exc).__name__}")
                dem["mask_rong"] += 1
                continue

            # Xét theo TỪNG ẢNH chứ không theo loài: trong cùng một loài có thể
            # lẫn ảnh Archive và ảnh iNaturalist (CAR_AUR cá vàng là ví dụ).
            ra, info = chuan_hoa_mot_anh(img, mask_img, huong_map.get(p.stem),
                                         khong_xoay="__archive__" in p.name)
            if ra is None:
                dem[info["ly_do"]] += 1
                continue

            ra.save(dich, "PNG")
            dem["ok"] += 1
            ca_px_tat_ca.append(info["ca_px_goc"])
            info.update({"ten_file_goc": p.name, "ten_file_ra": ten_ra})
            with meta_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(info, ensure_ascii=False) + "\n")

            if xem_thu_con > 0:
                xem = Image.new("RGB", (CANVAS * 3, CANVAS), (255, 255, 255))
                xem.paste(img.copy().resize((CANVAS, CANVAS)), (0, 0))
                xem.paste(mask_img.convert("RGB").resize((CANVAS, CANVAS)), (CANVAS, 0))
                xem.paste(ra.convert("RGB"), (CANVAS * 2, 0))
                (out_dir / "_xem_thu").mkdir(parents=True, exist_ok=True)
                xem.save(out_dir / "_xem_thu" / f"{p.stem}.jpg", quality=92)
                xem_thu_con -= 1

        for k in tong:
            tong[k] += dem[k]
        print(f"  {ma_loai:<9} đạt {dem['ok']:>4} | mask hỏng {dem['mask_rong']:>3} | "
              f"cá nhỏ {dem['ca_qua_nho']:>3} | nhiều mảnh {dem['nhieu_manh']:>3} | "
              f"bỏ qua {dem['bo_qua']:>4}")

    print("\n" + "-" * 62)
    print(f"Đạt {tong['ok']} ảnh. Loại: mask hỏng {tong['mask_rong']}, "
          f"cá nhỏ {tong['ca_qua_nho']}, nhiều mảnh {tong['nhieu_manh']}.")
    if ca_px_tat_ca:
        arr = np.array(ca_px_tat_ca)
        print(f"Cạnh dài con cá trong ảnh gốc: nhỏ nhất {arr.min():.0f}px, "
              f"trung vị {np.median(arr):.0f}px, lớn nhất {arr.max():.0f}px")
        print(f"Hệ số thu nhỏ: {TARGET_FISH / arr.max():.2f}× đến {TARGET_FISH / arr.min():.2f}×")
    for k, v in LY_DO.items():
        if tong.get(k):
            print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
