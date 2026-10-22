"""Xuất bản sửa hai mục 3.5 và 4.4 ra .docx theo đúng phong cách báo cáo giai đoạn 1.

    python scripts/xuat_docx_sua_muc.py

Phong cách đo trực tiếp từ Documents/Báo cáo giai đoạn 1.pdf:

    thân bài     Times New Roman 13pt, giãn dòng 1,5, căn đều,
                 thụt dòng đầu 25pt (0,88cm)
    lề           trái 3cm, phải 2cm, trên/dưới 2cm (A4)
    tiêu đề mục  TNR Bold 13pt, "3.5." tại lề rồi tab sang 23,2pt
    gạch đầu     ký tự − (U+2212) Arial 9pt tại lề, chữ thụt 20,9pt
    chú thích    TNR Italic 13pt, căn giữa, không thụt
    bảng         viền đơn 0,5pt màu 808080, KHÔNG tô nền ô,
                 hàng đầu in đậm, bảng căn giữa, trong ô giãn 1,5
    ký tự ①-⑩   font Cambria Math (bản gốc dùng font này)

Văn phong: chủ ngữ là "Nhóm", câu thuật không bình luận, và KHÔNG in đậm
giữa câu — bản gốc chỉ in đậm ở tiêu đề mục và hàng đầu bảng.

Số liệu lấy từ ket_qua/fisher_*.csv do scripts/gia_tri_thong_tin.py sinh ra.
"""

from __future__ import annotations

import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

ROOT = Path(__file__).resolve().parent.parent
RA = ROOT / "docs" / "bao-cao" / "Sua-muc-3.5-va-4.4.docx"

CHU = "Times New Roman"
CO = Pt(13)
VIEN = "808080"          # xám 50%, đo được từ các ô viền trong PDF
THUT_DAU = Pt(25)        # thụt dòng đầu đoạn
TREO_TIEU_DE = Pt(23.2)  # khoảng từ "3.5." sang chữ
TREO_GACH = Pt(20.9)     # khoảng từ dấu − sang chữ
VONG = "①②③④⑤⑥⑦⑧⑨⑩"


# ----------------------------------------------------------------- tiện ích

def dat_font(run, *, dam=False, nghieng=False, chu=CHU, co=CO) -> None:
    run.font.name = chu
    run.font.size = co
    run.bold = dam
    run.italic = nghieng
    # Word cần cả w:cs cho chữ Việt có dấu mới không nhảy sang font khác.
    rPr = run._element.get_or_add_rPr()
    rf = rPr.find(qn("w:rFonts"))
    if rf is None:
        rf = rPr.makeelement(qn("w:rFonts"), {})
        rPr.insert(0, rf)
    for a in ("w:ascii", "w:hAnsi", "w:cs"):
        rf.set(qn(a), chu)


def viet(p, text: str, *, dam=False, nghieng=False) -> None:
    """Ghi text vào đoạn p, tự đổi font Cambria Math cho ① đến ⑩."""
    dem = ""
    for ch in text:
        if ch in VONG:
            if dem:
                dat_font(p.add_run(dem), dam=dam, nghieng=nghieng)
                dem = ""
            dat_font(p.add_run(ch), dam=dam, nghieng=nghieng, chu="Cambria Math")
        else:
            dem += ch
    if dem:
        dat_font(p.add_run(dem), dam=dam, nghieng=nghieng)


def than(doc, text: str, *, thut=True) -> None:
    p = doc.add_paragraph()
    f = p.paragraph_format
    f.first_line_indent = THUT_DAU if thut else Pt(0)
    f.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    f.space_after = Pt(0)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    viet(p, text)


def tieu_de(doc, so: str, ten: str) -> None:
    p = doc.add_paragraph()
    f = p.paragraph_format
    f.left_indent = Pt(0)
    f.first_line_indent = Pt(0)
    f.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    f.space_before = Pt(6)
    f.space_after = Pt(0)
    f.tab_stops.add_tab_stop(TREO_TIEU_DE)
    viet(p, f"{so}\t{ten}", dam=True)


def gach(doc, text: str) -> None:
    """Một dòng gạch đầu dòng: − Arial 9pt tại lề, chữ treo vào trong."""
    p = doc.add_paragraph()
    f = p.paragraph_format
    f.left_indent = TREO_GACH
    f.first_line_indent = -TREO_GACH
    f.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    f.space_after = Pt(0)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    f.tab_stops.add_tab_stop(TREO_GACH)
    dat_font(p.add_run("−"), chu="Arial", co=Pt(9))
    dat_font(p.add_run("\t"))
    viet(p, text)


def chu_thich(doc, text: str) -> None:
    p = doc.add_paragraph()
    f = p.paragraph_format
    f.first_line_indent = Pt(0)
    f.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    f.space_before = Pt(6)
    f.space_after = Pt(0)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    viet(p, text, nghieng=True)


def ke_vien(bang) -> None:
    """Viền đơn 0,5pt màu 808080 cho mọi đường, kể cả đường trong."""
    tblPr = bang._tbl.tblPr
    b = tblPr.makeelement(qn("w:tblBorders"), {})
    for canh in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = b.makeelement(qn(f"w:{canh}"), {})
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), "4")        # 4/8 pt = 0,5pt
        e.set(qn("w:space"), "0")
        e.set(qn("w:color"), VIEN)
        b.append(e)
    tblPr.append(b)


def lam_bang(doc, dau: list[str], hang: list[list[str]],
             rong: list[float] | None = None,
             can_giua: list[int] | None = None) -> None:
    t = doc.add_table(rows=1, cols=len(dau))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = rong is None
    ke_vien(t)
    can_giua = can_giua or []

    def o(cell, text, dam):
        # Ô mới đã có đúng một đoạn rỗng không run nào; dùng luôn để khỏi
        # sinh ra một run rỗng thừa như cách gán cell.text = "".
        p = cell.paragraphs[0]
        f = p.paragraph_format
        f.first_line_indent = Pt(0)
        f.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        f.space_after = Pt(0)
        viet(p, text, dam=dam)

    for j, c in enumerate(t.rows[0].cells):
        o(c, dau[j], True)
        c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    for h in hang:
        cells = t.add_row().cells
        for j, c in enumerate(cells):
            o(c, h[j], False)
            if j in can_giua:
                c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    if rong:
        for r in t.rows:
            for j, c in enumerate(r.cells):
                c.width = Cm(rong[j])


# ----------------------------------------------------------------- nội dung

def main() -> int:
    doc = Document()
    s = doc.sections[0]
    s.left_margin, s.right_margin = Cm(3), Cm(2)
    s.top_margin, s.bottom_margin = Cm(2), Cm(2)

    n = doc.styles["Normal"]
    n.font.name, n.font.size = CHU, CO
    n.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    n.paragraph_format.space_after = Pt(0)
    n.element.rPr.rFonts.set(qn("w:eastAsia"), CHU)

    # ---- đầu trang ghi rõ đây là bản sửa, không phải báo cáo mới ----
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(0)
    viet(p, "BẢN SỬA HAI MỤC CỦA BÁO CÁO GIAI ĐOẠN 1", dam=True)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(12)
    viet(p, "Thay thế nguyên mục 3.5 và mục 4.4 trong bản hiện tại", nghieng=True)

    than(doc, "Hai mục này được viết khi nhóm chưa đo được giá trị thông tin của "
              "Bộ A và Bộ B, nên mục 3.5 chỉ trình bày thuộc tính ngữ nghĩa và mục 4.4 "
              "chỉ đối chiếu hai phương pháp. Bảng Fisher nay đã có, vì vậy nội dung "
              "và tiêu đề của cả hai mục được thay bằng phần dưới đây.")

    # ================================================================ 3.5
    tieu_de(doc, "3.5.", "Giá trị thông tin của các bộ đặc trưng")

    than(doc, "Ba bộ đặc trưng chứa ba loại dữ liệu khác nhau nên nhóm dùng hai dụng cụ "
              "đo khác nhau: entropy cho Bộ C vì đó là thuộc tính định danh, và phân rã "
              "phương sai Fisher cho Bộ A và Bộ B vì đó là số thực. Mọi phép tính trong "
              "mục này chạy trên mẫu cân bằng 19 ảnh mỗi loài, tức 380 ảnh, bằng cỡ lớp "
              "nhỏ nhất là cá lóc. Nếu để nguyên 162 ảnh cá dĩa cạnh 19 ảnh cá lóc thì "
              "phương sai liên lớp phản ánh kích thước lớp nhiều hơn phản ánh khác biệt "
              "giữa các loài.")

    than(doc, "Với Bộ C, 20 loài cho 190 cặp loài và entropy tối đa lý thuyết là "
              "log₂20 = 4,32 bit. Kết quả đo trên bảng thuộc tính:")

    chu_thich(doc, "Bảng 3. Entropy và khả năng tách cặp của 10 thuộc tính ngữ nghĩa")
    lam_bang(doc,
             ["Thuộc tính", "Entropy (bit)", "Cặp tách được", "Tỉ lệ"],
             [["mau_nen", "2,65", "162/190", "85%"],
              ["dang_duoi", "2,18", "152/190", "80%"],
              ["kich_thuoc", "2,06", "147/190", "77%"],
              ["ti_le_dai_cao", "2,06", "143/190", "75%"],
              ["dang_than", "2,04", "145/190", "76%"],
              ["vay_lung", "1,74", "131/190", "69%"],
              ["soc", "1,73", "134/190", "71%"],
              ["tuong_phan_lung_bung", "1,35", "111/190", "58%"],
              ["moi_truong", "1,30", "108/190", "57%"],
              ["cham", "1,02", "69/190", "36%"]],
             rong=[6.0, 3.2, 3.4, 2.0], can_giua=[1, 2, 3])

    gach(doc, "Không thuộc tính nào đạt 4,32 bit, cao nhất là 2,65, nên không đặc trưng "
              "đơn lẻ nào phân loại nổi 20 loài. Đây là lập luận định lượng cho kiến "
              "trúc nhiều bộ đặc trưng.")
    gach(doc, "Entropy thấp không đồng nghĩa vô dụng: cham chỉ 1,02 bit vì 14/20 loài "
              "không có chấm, nhưng giá trị dom_mat chỉ có ở AST_OCE và day chỉ có ở "
              "ONC_MYK, POE_RET.")
    gach(doc, "Có những phân biệt thị giác mà thuộc tính ngữ nghĩa không biểu diễn được, "
              "như số khoang trắng của cá hề. Khoảng trống này là lý do tồn tại của "
              "Bộ A và Bộ B.")

    than(doc, "Với Bộ A và Bộ B, nhóm phân rã phương sai của mỗi chiều thành hai phần: "
              "phương sai nội lớp đo mức lệch giữa các ảnh cùng loài, phương sai liên lớp "
              "đo mức lệch giữa các loài. Tỉ số liên lớp chia nội lớp là Fisher score; "
              "tỉ số từ 1 trở lên nghĩa là chiều đó tách loài mạnh hơn nhiễu trong loài.")

    than(doc, "Để so sánh được giữa hai khối có số chiều khác nhau, nhóm dùng thêm đại "
              "lượng η² bằng phương sai liên lớp chia tổng hai phương sai. Đại lượng này "
              "nằm trong khoảng [0; 1] và bất biến thang đo. Tính bất biến thang đo là "
              "điều kiện bắt buộc ở đây vì Bộ A① trộn kênh L trong khoảng [0; 100] với "
              "hai kênh a và b trong khoảng [−128; 127].")

    chu_thich(doc, "Bảng 4. Bộ A① color moments — phân rã phương sai đủ cả 9 chiều, "
                   "sắp theo Fisher score giảm dần")
    lam_bang(doc,
             ["Chiều", "Phương sai nội lớp", "Phương sai liên lớp",
              "Fisher score", "η²"],
             [["lech_b", "25,33", "58,76", "2,32", "0,699"],
              ["lech_a", "18,62", "37,01", "1,99", "0,665"],
              ["tb_b", "213,05", "288,89", "1,36", "0,576"],
              ["xien_b", "124,93", "81,89", "0,66", "0,396"],
              ["tb_a", "129,44", "72,74", "0,56", "0,360"],
              ["tb_L", "154,52", "52,25", "0,34", "0,253"],
              ["lech_L", "25,68", "8,49", "0,33", "0,248"],
              ["xien_L", "176,40", "44,22", "0,25", "0,200"],
              ["xien_a", "80,74", "18,70", "0,23", "0,188"]],
             rong=[2.6, 3.6, 3.6, 2.6, 2.0], can_giua=[1, 2, 3, 4])

    gach(doc, "Hai chiều dẫn đầu là lech_b với 2,32 và lech_a với 1,99, đều là độ lệch "
              "chuẩn, trong khi chiều màu trung bình mạnh nhất là tb_b chỉ đạt 1,36. "
              "Mức đồng đều của màu tách loài tốt hơn giá trị màu trung bình.")
    gach(doc, "Cả ba chiều của kênh độ sáng L đều xếp gần cuối: tb_L 0,34, lech_L 0,33 "
              "và xien_L 0,25. Ảnh được chụp ở những điều kiện sáng khác nhau nên L "
              "biến động trong cùng một loài nhiều hơn là giữa các loài. Đây là bằng "
              "chứng định lượng cho việc chọn hệ màu Lab và tách độ sáng khỏi màu.")
    gach(doc, "Chỉ 3 trong 9 chiều đạt Fisher score từ 1 trở lên, phù hợp với vai trò "
              "đối chứng cơ sở của khối này.")

    chu_thich(doc, "Bảng 5. So sánh giá trị thông tin giữa các khối "
                   "(mẫu cân bằng 380 ảnh)")
    lam_bang(doc,
             ["Khối", "Số chiều", "η² trung bình", "η² top-9",
              "Fisher cao nhất", "Chiều mạnh"],
             [["Bộ A① color moments", "9", "0,398", "0,398", "2,32", "3/9"],
              ["Bộ B ResNet18", "512", "0,366", "0,681", "3,52", "82/512"],
              ["Bộ C ngữ nghĩa", "35", "0,971", "1,000", "—", "0/35"]],
             rong=[4.6, 1.9, 2.8, 2.2, 2.6, 2.3], can_giua=[1, 2, 3, 4, 5])

    gach(doc, "Cột dùng để so sánh giữa các khối là η² top-9, không phải η² trung bình. "
              "Lấy trung bình trên toàn bộ 512 chiều làm loãng Bộ B vì phần lớn chiều "
              "của nó không liên quan tới cặp loài đang xét: η² trung bình cho 0,366, "
              "thấp hơn 0,398 của Bộ A①, trái ngược với kết quả P@5 là 72,2% so với "
              "32,2%. So trên cùng 9 chiều mạnh nhất thì Bộ B đạt 0,681 và khớp với P@5. "
              "Nhóm phát hiện sai lệch này nhờ đối chiếu với P@5 trước khi đưa bảng vào "
              "báo cáo.")
    gach(doc, "Giá trị η² bằng 1,000 của Bộ C là hệ quả của cách gán vector, không phải "
              "thành tích. Vector Bộ C gán theo loài nên mọi ảnh cùng loài có vector như "
              "nhau, phương sai nội lớp bằng 0 và η² bằng 1 theo định nghĩa, bất kể bảng "
              "thuộc tính tốt hay dở. Giá trị thông tin của Bộ C phải đọc ở bảng entropy.")
    gach(doc, "Bộ B có 82 trong 512 chiều đạt Fisher score từ 1 trở lên và không có "
              "chiều nào vô dụng; phân vị tỉ số Fisher là 0,38 ở mức 25%, 0,55 ở mức "
              "50%, 0,82 ở mức 75% và 1,40 ở mức 95%. Vì vậy giảm chiều bằng PCA xuống "
              "128 sẽ làm mất thông tin thật chứ không chỉ cắt phần thừa; đánh đổi giữa "
              "kích thước chỉ mục và recall sẽ được đo ở giai đoạn 2.")

    chu_thich(doc, "Bảng 6. Mười hai cặp loài cùng họ — η² top-9 của từng khối, "
                   "giá trị cao nghĩa là tách được")
    lam_bang(doc,
             ["Họ", "Cặp loài", "Bộ A①", "Bộ B", "Chênh"],
             [["Acanthuridae", "PAR_HEP / ZEB_FLA", "0,489", "0,762", "+0,273"],
              ["Cichlidae", "AST_OCE / ORE_MOS", "0,281", "0,522", "+0,241"],
              ["Cichlidae", "AST_OCE / ORE_NIL", "0,243", "0,561", "+0,318"],
              ["Cichlidae", "AST_OCE / SYM_SPP", "0,046", "0,524", "+0,479"],
              ["Cichlidae", "ORE_MOS / ORE_NIL", "0,069", "0,182", "+0,112"],
              ["Cichlidae", "ORE_MOS / SYM_SPP", "0,295", "0,701", "+0,406"],
              ["Cichlidae", "ORE_NIL / SYM_SPP", "0,231", "0,691", "+0,460"],
              ["Cyprinidae", "CAR_AUR / CYP_CAR", "0,197", "0,567", "+0,370"],
              ["Osphronemidae", "BET_SPL / OSP_GOR", "0,218", "0,671", "+0,453"],
              ["Pomacentridae", "AMP_FRE / AMP_OCE", "0,103", "0,665", "+0,561"],
              ["Salmonidae", "ONC_MYK / SAL_SAL", "0,115", "0,386", "+0,271"],
              ["Scombridae", "KAT_PEL / SCO_COM", "0,087", "0,510", "+0,423"]],
             rong=[3.5, 5.0, 2.2, 2.0, 2.2], can_giua=[2, 3, 4])

    gach(doc, "Bộ B tách tốt hơn Bộ A① ở cả 12 cặp, không cặp nào ngoại lệ.")
    gach(doc, "Cặp khó nhất với Bộ A① là AST_OCE và SYM_SPP với 0,046. Cá hoàng bảo yến "
              "và cá dĩa cùng dáng dẹt cao và đều nhiều màu, đúng vai trò cặp dễ nhầm "
              "đã định khi chọn loài ở mục 2.2. Bộ B tách được cặp này với 0,524 nên nó "
              "không phải điểm khó của cả hệ.")
    gach(doc, "Cặp khó với cả hai khối là ORE_MOS và ORE_NIL, đạt 0,069 ở Bộ A① và "
              "0,182 ở Bộ B, trong khi cặp thấp thứ hai của Bộ B đạt 0,386, gấp 2,1 lần. "
              "Đây là cặp cùng chi Oreochromis và cũng là cặp nhầm nhiều nhất trong "
              "phân tích lỗi top-1 ở mục 4.5.")
    gach(doc, "Cặp được Bộ B cải thiện nhiều nhất là AMP_FRE và AMP_OCE với mức chênh "
              "0,561. Hai loài cá hề này cũng là hai loài có P@5 tăng mạnh nhất trong "
              "Bảng 2, tăng 77 và 67 điểm. Hai phép đo độc lập cho cùng một thứ hạng.")

    # ================================================================ 4.4
    tieu_de(doc, "4.4.", "Đối chiếu ba phương pháp đo giá trị thông tin")

    than(doc, "Ba phương pháp dưới đây dùng ba nguồn dữ liệu không chia sẻ với nhau: "
              "entropy tính trên bảng thuộc tính do người gán, Fisher score tính trên "
              "vector đặc trưng, và P@5 đo trên truy vấn ảnh thật. Việc chúng cùng chỉ "
              "ra một kết luận là bằng chứng mạnh hơn từng phương pháp riêng lẻ.")

    than(doc, "Đặt bốn loài yếu nhất và bốn loài mạnh nhất của Bộ A① cạnh giá trị "
              "mau_nen trong bảng ngữ nghĩa:")

    lam_bang(doc,
             ["Loài yếu nhất", "P@5", "mau_nen", "Loài mạnh nhất", "P@5", "mau_nen"],
             [["Cá lóc", "7%", "nau", "Cá đuôi gai xanh", "79%", "xanh_lam*"],
              ["Cá hồi vân", "10%", "bac", "Cá bảy màu", "74%", "da_mau"],
              ["Cá tra", "11%", "bac", "Cá dĩa", "70%", "da_mau"],
              ["Cá rô phi đen", "11%", "den", "Cá đuôi gai vàng", "69%", "vang*"]],
             rong=[3.4, 1.6, 2.3, 3.8, 1.6, 2.3], can_giua=[1, 2, 4, 5])
    than(doc, "* Màu duy nhất trong 20 loài.", thut=False)

    than(doc, "Bốn loài kém nhất đều có màu nâu, bạc hoặc đen, tức mau_nen không mang "
              "thông tin phân biệt; bốn loài tốt nhất đều có màu rực hoặc màu riêng. "
              "Entropy tính trên bảng do người gán và P@5 đo trên ảnh thật là hai "
              "phương pháp độc lập nhưng cho cùng một kết luận.")

    than(doc, "Cặp cùng chi Oreochromis được cả bốn phép đo chỉ ra là điểm khó nhất "
              "của hệ:")

    chu_thich(doc, "Bảng 7. Cặp ORE_MOS và ORE_NIL qua bốn phép đo độc lập")
    lam_bang(doc,
             ["Phép đo", "Kết quả", "Vị trí"],
             [["Số thuộc tính ngữ nghĩa khác nhau", "4/10",
               "một trong ba cặp giống nhất"],
              ["η² top-9 trên Bộ A①", "0,069", "thấp thứ hai trong 12 cặp"],
              ["η² top-9 trên Bộ B", "0,182", "thấp nhất trong 12 cặp"],
              ["P@5 của Bộ B", "32% và 41%", "hai loài thấp nhất trong 20"],
              ["Nhầm lẫn top-1", "13 ca và 7 ca", "cặp nhầm nhiều nhất"]],
             rong=[6.6, 3.2, 5.2], can_giua=[1])

    than(doc, "Bốn phép đo này không dùng chung dữ liệu đầu vào: một phép đọc bảng "
              "thuộc tính do người gán, hai phép đọc vector đặc trưng, một phép đọc "
              "nhãn dự đoán trên truy vấn thật. Hoa văn vạch đứng của cá rô phi vằn là "
              "kết cấu chứ không phải màu, nên GLCM (⑤) và Gabor (⑥) là hai đặc trưng "
              "được kỳ vọng xử lý cặp này ở giai đoạn 2. Đây là giả thuyết sẽ được kiểm "
              "bằng số, chưa phải kết quả đã đo.")

    than(doc, "Chênh lệch giữa Bộ B và Bộ A① lớn nhất ở những cặp mà đặc điểm phân biệt "
              "không nằm ở màu. Cặp cá hề minh họa rõ nhất: Bộ C chỉ tách được bằng 1 "
              "trong 10 thuộc tính, η² top-9 của Bộ A① là 0,103 còn của Bộ B là 0,665 "
              "nên mức chênh 0,561 là lớn nhất trong 12 cặp; P@5 tăng từ 19% và 25% lên "
              "96% và 91%, tức tăng 77 và 67 điểm, cũng là mức tăng lớn nhất trong 20 "
              "loài. Mạng sâu nhận ra đặc điểm phân biệt là số khoang trắng, thứ mà cả "
              "từ vựng ngữ nghĩa lẫn đặc trưng màu đều bỏ sót.")

    than(doc, "Ba phương pháp cho ba kết luận trùng khớp:")
    gach(doc, "Loài có màu nâu, bạc hoặc đen là loài khó; loài có màu rực hoặc màu "
              "riêng là loài dễ (entropy và P@5).")
    gach(doc, "Cặp Oreochromis cùng chi là điểm khó nhất, và khó với cả đặc trưng màu "
              "lẫn đặc trưng sâu (Fisher, P@5 và nhầm lẫn top-1).")
    gach(doc, "Bộ B hơn Bộ A① nhiều nhất ở những cặp mà đặc điểm phân biệt là hoa văn "
              "chứ không phải màu (Fisher và P@5).")

    # ---------------------------------------------------- hai chỗ sửa thêm
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(18)
    p.paragraph_format.space_after = Pt(0)
    viet(p, "Hai chỗ nhỏ cần sửa tay ngoài hai mục trên", dam=True)

    gach(doc, "Mục 1 Tóm tắt: câu “kiem_tra.py --day-du (10/10 bộ kiểm thử đạt)” không "
              "còn đúng vì nhóm đã thêm bộ kiểm thử fisher. Số đúng hiện tại là 8/8 bộ "
              "cơ bản và 11/11 khi chạy kèm --day-du.")
    gach(doc, "Mục 3.4: câu “Bảng ba cột (nội lớp, liên lớp, tỉ số) trên mẫu cân bằng "
              "19 ảnh mỗi loài sẽ được trình bày ở báo cáo tiến độ 2” cần thay bằng "
              "“Bảng ba cột được trình bày ở mục 3.5”, vì bảng đó đã có.")

    RA.parent.mkdir(parents=True, exist_ok=True)
    doc.save(RA)
    print(f"Da ghi {RA.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
