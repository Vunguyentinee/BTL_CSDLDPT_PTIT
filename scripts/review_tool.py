"""Công cụ duyệt ảnh bằng phím tắt — bước người làm, không thay thế được bằng máy.

Hai việc mà `chuan_hoa.py` không làm nổi và đây là nơi giải quyết:

1.  **Loại ảnh sai chuẩn.** Tay người cầm cá thì mask dính liền một khối nên phép
    đếm mảnh không bắt được; ảnh chụp chính diện, nhiều con một ảnh, vật lạ lọt
    vào — đều phải mắt người nhìn.
2.  **Ghi hướng đầu cá.** Heuristic đoán theo bề dày thân sai quá nửa số ảnh (đo
    ngày 03/10: 21/39 ảnh có độ tin cậy dưới 1,2), vì đuôi nhiều loài còn xòe
    rộng hơn đầu.

Màn hình hiện **ảnh đã chuẩn hóa bên trái, ảnh gốc bên phải**. Ảnh gốc cần cho
việc nhận ra tay người hay con cá thứ hai mà `rembg` đã cắt mất.

Bước chuẩn hóa đã xoay trục dài con cá nằm ngang, nhưng **không xác định được
chiều**: 28% ảnh phải xoay hơn 45° (cá chụp dọc), và với chúng thì bụng có thể
lên trên. Lật ngang không sửa được bụng ngược. Nên cần bốn trạng thái:

    A   nhận — ĐÚNG RỒI: đầu bên trái, lưng ở trên
    D   nhận — đầu bên PHẢI, lưng ở trên      → lật ngang
    W   nhận — đầu bên TRÁI, lưng ở DƯỚI      → lật dọc
    S   nhận — đầu bên PHẢI, lưng ở DƯỚI      → xoay 180°
    1   loại — R-anh   (nhiều con · có người · không chụp ngang · vật lạ · mờ)
    2   loại — R-nhan  (không chắc đúng loài)
    3   loại — R-trung (trùng với ảnh đã duyệt)
    Z   quay lại ảnh trước, sửa quyết định
    ESC thoát (đã lưu tới đâu giữ tới đó)

Cách nhớ: cứ nhìn **đầu cá đang ở bên nào** rồi **lưng ở trên hay dưới**.

Kết quả ghi ngay từng dòng vào `data_meta/review/<ma_loai>.r1.csv`, nên thoát
giữa chừng không mất gì và mở lại thì duyệt tiếp từ chỗ dở.

Ảnh cần lật sẽ được `ap_dung_lat.py` lật sau — lật ngang ảnh PNG đã chuẩn hóa là
phép **không mất mát và không lấy mẫu lại**, nên không phải chạy lại `rembg`.

    python scripts/review_tool.py --loai CYP_CAR
    python scripts/review_tool.py --loai CYP_CAR --nguoi Minh
"""

from __future__ import annotations

import argparse
import csv
import sys
import tkinter as tk
from pathlib import Path

from PIL import Image, ImageTk

ROOT = Path(__file__).resolve().parent.parent
SPECIES_CSV = ROOT / "data_meta" / "species.csv"
CHUAN_DIR = ROOT / "work" / "chuan"
ANH_DIR = ROOT / "work" / "anh"
REVIEW_DIR = ROOT / "data_meta" / "review"
CO_ANH = 420
COT = ["image_id", "quyet_dinh", "ma_ly_do", "tu_the", "bien_doi", "nguoi_duyet"]

LY_DO = {
    "1": ("R-anh", "nhiều con / có người / không chụp ngang / vật lạ / mờ"),
    "2": ("R-nhan", "không chắc đúng loài"),
    "3": ("R-trung", "trùng ảnh đã duyệt"),
}

# phím -> (tư thế đang thấy, phép biến đổi để về đầu-trái lưng-trên)
#
# Mọi phép đều chỉ ĐỔI CHỖ pixel, không nội suy — không làm nhòe thêm kết cấu
# và không phải chạy lại rembg.
#
# GIỮ NGUYÊN schema này: nhóm đã duyệt 2.499 ảnh theo đúng các cột
# `tu_the` + `bien_doi` trong hai ngày 09–10/10. Đổi cột là mất hết dữ liệu đó.
TU_THE = {
    "a": ("dau_trai_lung_tren", ""),
    "d": ("dau_phai_lung_tren", "ngang"),
    "w": ("dau_trai_lung_duoi", "doc"),
    "s": ("dau_phai_lung_duoi", "180"),
}


def doc_loai(ma_loai: str) -> dict:
    with SPECIES_CSV.open(newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            if (r.get("ma_loai") or "").strip().upper() == ma_loai:
                return r
    sys.exit(f"Không có mã loài {ma_loai} trong species.csv")


class BangDuyet:
    def __init__(self, ma_loai: str, nguoi: str):
        self.ma_loai = ma_loai
        self.nguoi = nguoi
        self.loai = doc_loai(ma_loai)

        REVIEW_DIR.mkdir(parents=True, exist_ok=True)
        self.csv_path = REVIEW_DIR / f"{ma_loai}.r1.csv"
        self.da_duyet = self._doc_da_duyet()

        tat_ca = sorted((CHUAN_DIR / ma_loai).glob("*.png"))
        if not tat_ca:
            sys.exit(f"Không có ảnh đã chuẩn hóa ở {CHUAN_DIR / ma_loai}")
        self.ds = [p for p in tat_ca if p.stem not in self.da_duyet]
        self.tong = len(tat_ca)
        self.i = 0
        self.lich_su: list[str] = []

        self.root = tk.Tk()
        self.root.title(f"Duyệt ảnh — {ma_loai}")
        self.lbl_anh = tk.Label(self.root, bg="#222")
        self.lbl_anh.pack()
        self.lbl_tt = tk.Label(self.root, font=("Segoe UI", 11), justify="left", anchor="w")
        self.lbl_tt.pack(fill="x", padx=8, pady=4)
        tk.Label(
            self.root, justify="left", anchor="w", fg="#333", font=("Consolas", 10),
            text="NHẬN — nhìn đầu cá ở bên nào, lưng ở trên hay dưới:\n"
                 "   A  đầu TRÁI · lưng TRÊN  (đúng rồi)      D  đầu PHẢI · lưng TRÊN  → lật ngang\n"
                 "   W  đầu TRÁI · lưng DƯỚI  → lật dọc       S  đầu PHẢI · lưng DƯỚI  → xoay 180°\n"
                 "LOẠI — 1 sai chuẩn ảnh · 2 sai loài · 3 trùng      Z quay lại sửa · ESC thoát",
        ).pack(fill="x", padx=8, pady=(0, 8))

        for phim in ("a", "A", "d", "D", "w", "W", "s", "S", "1", "2", "3", "z", "Z"):
            self.root.bind(phim, self.phim)
        self.root.bind("<Escape>", lambda e: self.root.destroy())
        self.hien()

    # ------------------------------------------------------------ dữ liệu

    def _doc_da_duyet(self) -> dict[str, dict]:
        if not self.csv_path.exists():
            return {}
        with self.csv_path.open(newline="", encoding="utf-8-sig") as fh:
            return {r["image_id"]: r for r in csv.DictReader(fh)}

    def _ghi_het(self) -> None:
        """Ghi lại cả file. Dữ liệu nhỏ (vài trăm dòng) nên ghi lại toàn bộ là an
        toàn hơn ghi bổ sung, vì phím Z cần sửa được dòng đã ghi."""
        with self.csv_path.open("w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, fieldnames=COT, lineterminator="\n")
            w.writeheader()
            w.writerows(self.da_duyet.values())

    # ------------------------------------------------------------ giao diện

    def hien(self) -> None:
        if self.i >= len(self.ds):
            self.xong()
            return
        p = self.ds[self.i]

        trai = Image.open(p).convert("RGB")
        trai.thumbnail((CO_ANH, CO_ANH))

        goc = next(iter(ANH_DIR.glob(f"{self.ma_loai}/{p.stem}.jpg")), None)
        phai = Image.open(goc).convert("RGB") if goc else Image.new("RGB", (10, 10), "#333")
        phai.thumbnail((CO_ANH, CO_ANH))

        khung = Image.new("RGB", (CO_ANH * 2 + 12, CO_ANH), (34, 34, 34))
        khung.paste(trai, ((CO_ANH - trai.width) // 2, (CO_ANH - trai.height) // 2))
        khung.paste(phai, (CO_ANH + 12 + (CO_ANH - phai.width) // 2, (CO_ANH - phai.height) // 2))

        self._img = ImageTk.PhotoImage(khung)
        self.lbl_anh.config(image=self._img)

        xong = len(self.da_duyet)
        nhan = sum(1 for r in self.da_duyet.values() if r["quyet_dinh"] == "nhan")
        self.lbl_tt.config(
            text=f"{self.loai['ten_viet']}  ({self.loai['ten_khoa_hoc']})\n"
                 f"Đã duyệt {xong}/{self.tong}   ·   nhận {nhan}   ·   còn {len(self.ds) - self.i}\n"
                 f"TRÁI = đã chuẩn hóa   |   PHẢI = ảnh gốc   ·   {p.stem}"
        )

    def phim(self, e) -> None:
        k = e.keysym.lower()
        if k == "z":
            self.lui()
            return
        if self.i >= len(self.ds):
            return
        p = self.ds[self.i]

        if k in TU_THE:
            tu_the, bien_doi = TU_THE[k]
            row = dict(image_id=p.stem, quyet_dinh="nhan", ma_ly_do="",
                       tu_the=tu_the, bien_doi=bien_doi, nguoi_duyet=self.nguoi)
        elif k in LY_DO:
            row = dict(image_id=p.stem, quyet_dinh="loai", ma_ly_do=LY_DO[k][0],
                       tu_the="", bien_doi="", nguoi_duyet=self.nguoi)
        else:
            return

        self.da_duyet[p.stem] = row
        self.lich_su.append(p.stem)
        self._ghi_het()
        self.i += 1
        self.hien()

    def lui(self) -> None:
        if not self.lich_su:
            return
        stem = self.lich_su.pop()
        self.da_duyet.pop(stem, None)
        self._ghi_het()
        self.i = max(0, self.i - 1)
        self.hien()

    def xong(self) -> None:
        nhan = sum(1 for r in self.da_duyet.values() if r["quyet_dinh"] == "nhan")
        bd = sum(1 for r in self.da_duyet.values() if r.get("bien_doi"))
        self.lbl_anh.config(image="")
        self.lbl_tt.config(
            text=f"XONG {self.ma_loai}\n"
                 f"Nhận {nhan}/{self.tong} ảnh   ·   {bd} ảnh cần xoay/lật\n"
                 f"Kết quả: {self.csv_path}\n"
                 f"Chạy tiếp: python scripts/ap_dung_lat.py --loai {self.ma_loai}"
        )

    def chay(self) -> None:
        self.root.mainloop()


class ManHinhChon:
    """Bảng chọn loài, hiện khi chạy không truyền tham số.

    Cần có vì bấm nút Run trong VS Code sẽ chạy file mà không kèm `--loai`, và
    cả ba thành viên đều sẽ bấm Run chứ không gõ lệnh.
    """

    def __init__(self):
        self.chon: tuple[str, str] | None = None
        self.root = tk.Tk()
        self.root.title("Chọn loài để duyệt")

        tk.Label(self.root, text="Tên người duyệt:", anchor="w",
                 font=("Segoe UI", 10)).pack(fill="x", padx=12, pady=(12, 2))
        self.o_ten = tk.Entry(self.root, font=("Segoe UI", 11))
        self.o_ten.insert(0, self._ten_cu())
        self.o_ten.pack(fill="x", padx=12)

        tk.Label(self.root, text="Bấm vào loài muốn duyệt:", anchor="w",
                 font=("Segoe UI", 10)).pack(fill="x", padx=12, pady=(12, 4))

        khung = tk.Frame(self.root)
        khung.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        canvas = tk.Canvas(khung, height=420, highlightthickness=0)
        thanh = tk.Scrollbar(khung, orient="vertical", command=canvas.yview)
        trong = tk.Frame(canvas)
        trong.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=trong, anchor="nw")
        canvas.configure(yscrollcommand=thanh.set)
        canvas.pack(side="left", fill="both", expand=True)
        thanh.pack(side="right", fill="y")

        for ma, ten, co, nhan, con in self._danh_sach():
            if con == 0:
                mau, trang_thai = "#1a7f37", f"ĐÃ XONG · nhận {nhan}"
            elif con < co:
                mau, trang_thai = "#9a6700", f"còn {con} chưa duyệt"
            else:
                mau, trang_thai = "#24292f", f"chưa duyệt ({con} ảnh)"
            nhan_nut = f"{ma:<9} {ten:<20} {co:>4} ảnh   {trang_thai}"
            tk.Button(trong, text=nhan_nut, font=("Consolas", 10), anchor="w", fg=mau,
                      width=58, relief="groove",
                      command=lambda m=ma: self._chon(m)).pack(fill="x", pady=1)

        self.root.bind("<Escape>", lambda e: self.root.destroy())

    def _ten_cu(self) -> str:
        f = REVIEW_DIR / ".nguoi_duyet.txt"
        return f.read_text(encoding="utf-8").strip() if f.exists() else ""

    def _danh_sach(self) -> list[tuple[str, str, int, int, int]]:
        """Trả về (mã, tên Việt, số ảnh đang có, số đã duyệt, số CÒN phải duyệt).

        Số còn lại phải tính bằng **hiệu của hai tập tên ảnh**, không lấy hiệu
        của hai con số. Sau khi `ap_dung_lat` chạy, ảnh bị loại đã chuyển sang
        work/loai nên số file trong work/chuan nhỏ hơn số dòng đã duyệt — trừ
        hai con số sẽ ra số âm và loài nào cũng hiện là chưa xong.
        """
        out = []
        with SPECIES_CSV.open(newline="", encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                if (r.get("trang_thai") or "").strip() != "da_chot":
                    continue
                ma = r["ma_loai"].strip()
                d = CHUAN_DIR / ma
                co = {p.stem for p in d.glob("*.png")} if d.exists() else set()
                if not co:
                    continue
                f = REVIEW_DIR / f"{ma}.r1.csv"
                da = set()
                nhan = 0
                if f.exists():
                    with f.open(newline="", encoding="utf-8-sig") as fh2:
                        for row in csv.DictReader(fh2):
                            da.add(row["image_id"])
                            if row.get("quyet_dinh") == "nhan":
                                nhan += 1
                out.append((ma, r.get("ten_viet", ""), len(co), nhan, len(co - da)))
        return out

    def _chon(self, ma: str) -> None:
        ten = self.o_ten.get().strip()
        REVIEW_DIR.mkdir(parents=True, exist_ok=True)
        (REVIEW_DIR / ".nguoi_duyet.txt").write_text(ten, encoding="utf-8")
        self.chon = (ma, ten)
        self.root.destroy()

    def chay(self) -> tuple[str, str] | None:
        self.root.mainloop()
        return self.chon


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--loai", help="mã loài, ví dụ CYP_CAR. Bỏ trống thì hiện bảng chọn")
    ap.add_argument("--nguoi", default="", help="tên người duyệt")
    args = ap.parse_args()

    if args.loai:
        ma, nguoi = args.loai.strip().upper(), args.nguoi
    else:
        kq = ManHinhChon().chay()
        if not kq:
            return 0
        ma, nguoi = kq
    BangDuyet(ma, nguoi).chay()
    return 0


if __name__ == "__main__":
    sys.exit(main())
