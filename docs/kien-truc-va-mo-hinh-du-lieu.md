# Kiến trúc và mô hình dữ liệu — bản để trả lời vấn đáp

> Viết ngày 14/10/2026. Bám theo khung của **Lecture 4 — MMDS Architecture** và
> **Lecture 5 — MM data model**, có đối chiếu **Lecture 7 — Vector database and Clustering**.
> Dùng để trả lời thầy; mọi thuật ngữ dưới đây lấy nguyên từ slide.

---

# Phần 1 — Kiến trúc (Lecture 4)

Bài giảng tách kiến trúc thành **hai chiều độc lập**, phải trả lời cả hai:

1. **Architectural style** — centralized / distributed / hybrid
2. **Storage principle** — separation / homogeneity / hybrid

## 1.1 Architectural style: **CENTRALIZED**

> Slide 5: *"Centralized: single DBMS site, shared storage + CPU; simple admin, single point of failure. Suited to small/medium archives, campus media library, **development prototypes**"*

Hệ của nhóm rơi đúng vào mô tả này: một site DBMS duy nhất, lưu trữ và CPU dùng chung.

### Năm lý do chọn centralized

| # | Lý do | Số liệu của hệ |
|---|---|---|
| 1 | **Quy mô nhỏ** — slide 5 xếp "small/medium archives" và "development prototypes" vào centralized | 1.085 ảnh · vector đặc trưng ≈ 4–5 MB · toàn bộ CSDL < 1 GB |
| 2 | **Không có người dùng phân tán theo địa lý** — slide 5 nêu distributed hợp với "geo-distributed users" | Một người dùng, demo tại chỗ |
| 3 | **Không có yêu cầu fault tolerance** — slide 5 nêu distributed hợp khi có "fault tolerance requirements" | Bài tập lớn, không có SLA |
| 4 | **Truy vấn k-NN là truy vấn toàn cục** | Phân tán buộc phải scatter–gather tới mọi node; tổng khối lượng tính **không giảm**, chỉ thêm độ trễ mạng |
| 5 | **Độ trễ mạng đắt hơn cả phép tính** | Brute-force 1.085 vector < 1 ms; một vòng round-trip LAN ~0,2–1 ms, Internet ~20–50 ms |

### Lý do số 4 giải thích kỹ — đây là lập luận mạnh nhất

Slide 5 nêu *"Performance bottleneck: disk I/O + network path between storage and clients"*. Với k-NN, nút thắt đó không giảm được bằng cách phân tán:

```
Truy vấn → fan-out tới TẤT CẢ N node → mỗi node trả top-5 cục bộ → merge → top-5 toàn cục
```

Tìm 5 ảnh gần nhất về nguyên tắc phải so với **toàn bộ** không gian vector. Chia ra N node thì mỗi node làm 1/N công việc nhưng **tổng công việc không đổi**, lại cộng thêm chi phí mạng và bước merge. Ở quy mô 1.085 vector, phân tán **làm hệ chậm đi**.

Thêm nữa: **chọn khóa phân mảnh cho k-NN là bài toán khó** — không có khóa tự nhiên nào bảo toàn tính lân cận trong không gian nhiều chiều; muốn shard đúng phải phân cụm (IVF) hoặc LSH, tức thêm cả một tầng thuật toán xấp xỉ cho một vấn đề chưa tồn tại.

### Vì sao không phải hybrid

> Slide 5: *"Hybrid deployments: metadata centralized, LOBs distributed near users"*

Hybrid theo định nghĩa của slide là **phân tán LOB tới gần người dùng** (kiểu CDN). Hệ của nhóm không có người dùng ở xa, nên phần "distributed near users" không có lý do tồn tại.

## 1.2 Storage principle: **HOMOGENEITY**

> Slide 12: *"Homogeneity Principle — Unified Storage Structure. All media types stored under one logical schema and access API... **Example: one PostgreSQL + object storage bucket for all BLOBs**"*

Thiết kế của nhóm khớp đúng ví dụ trong slide:

| Thành phần | Nơi lưu |
|---|---|
| Metadata (loài, họ, nguồn, split) | PostgreSQL |
| Vector đặc trưng (4 khối) | PostgreSQL, kiểu `vector(n)` |
| Ảnh nhị phân 384×384 | Hệ thống file, CSDL giữ đường dẫn + SHA-256 |

Một lược đồ logic duy nhất, một API truy cập duy nhất (SQL), bất kể là metadata hay tham chiếu tới ảnh.

### Vì sao KHÔNG phải separation hay hybrid

> Slide 10: *"Separation Principle — Each media type (text, image, audio, video) stored on dedicated server subsystem"*

Separation là tách **theo loại phương tiện**: video server riêng, image server riêng, audio server riêng. **Hệ của nhóm chỉ có một loại phương tiện là ảnh tĩnh**, nên nguyên tắc này không có gì để áp dụng.

Hybrid (slide 14) = catalog thống nhất + storage engine chuyên biệt theo từng loại phương tiện. Cũng không áp dụng được vì lý do trên.

> **Lưu ý khi trả lời:** việc nhóm tách *metadata trong CSDL* và *ảnh ngoài CSDL* **không phải** separation principle. Separation là tách theo loại phương tiện, còn đây là tách theo loại dữ liệu trong cùng một phương tiện. Slide 12 xếp chính xác mô hình này vào homogeneity.

### Vì sao ảnh để ngoài CSDL

| Lý do | |
|---|---|
| DBMS quan hệ xử lý BLOB lớn kém | Phình WAL, backup và dump chậm, khó cache |
| Pipeline xử lý ảnh đọc file trực tiếp tiện hơn | OpenCV, Pillow, rembg đều làm việc trên file |
| Slide 12 chấp nhận cách này | *"unified catalog + typed LOB columns **or object store backend**"* |

**Cái giá:** không có ACID giữa một hàng trong bảng và một file trên đĩa. Bốn biện pháp bù:

1. Ảnh **bất biến** — chỉ thêm, không sửa tại chỗ
2. Tên file = **SHA-256 của nội dung**, lưu hash trong CSDL
3. Script **`verify_integrity`** đối chiếu bảng ↔ thư mục (thiếu file, file mồ côi, hash sai)
4. Thứ tự ghi: **file trước, insert sau**, trong một giao dịch

## 1.3 Kiểu triển khai: **client–server 3 tầng**

```
Tầng trình bày   Trình duyệt ← Streamlit UI
       ↕ HTTP
Tầng ứng dụng    package fishcbir/ (preprocess → features → search → eval)
       ↕ SQL
Tầng dữ liệu     PostgreSQL 17 + pgvector  ← MỘT site duy nhất
```

> ### ⚠️ Bẫy vấn đáp: client–server KHÔNG phải distributed
>
> Việc ứng dụng và DBMS chạy ở hai tiến trình khác nhau **không** làm CSDL thành phân tán. Theo slide 5, distributed nghĩa là **"fragments/replicas across sites"** — dữ liệu nằm ở nhiều site và nhiều DBMS phối hợp. Ở đây chỉ có một DBMS, một bản dữ liệu, không phân mảnh, không nhân bản → **centralized**.

---

# Phần 2 — Mô hình dữ liệu (Lecture 5)

> Slide 3: *"Progression: Relational → Object-Oriented → Object-Relational → NoSQL → Graph → Vector. Each model addresses a different weakness of the previous one for multimedia data"*

## 2.1 Câu trả lời: **Object-Relational (ORDBMS) mở rộng bằng Vector**

Không phải một mô hình thuần túy, mà là **nền Object-Relational cộng kiểu dữ liệu Vector** — và đây chính là con đường mà bài giảng chỉ ra:

> Slide 42: *"Example: PostgreSQL for Multimedia Metadata... **Extensions (PostGIS, pgvector) push ORDBMS further toward multimedia & similarity**"*

> Slide 40: *"Object-Relational Databases (ORDBMS) — Goal: keep SQL/relational strengths while adding object features for multimedia... **Examples: PostgreSQL**, Oracle, IBM Db2, Informix"*

Hệ dùng **PostgreSQL 17 + pgvector**: PostgreSQL là ORDBMS theo đúng slide 40, pgvector thêm kiểu `vector(n)` cùng các toán tử khoảng cách.

### Slide 55 mô tả gần như nguyên văn hệ của nhóm

> *"Example: Image Retrieval with Vectors — Offline: for each flower image, compute embedding e_i ∈ R^512; insert (id, e_i, species). Online: embed query image q → e_q; search top-5 nearest under cosine similarity. SQL+pgvector sketch: `SELECT id FROM images ORDER BY embedding <=> :q LIMIT 5`. Evaluation: Precision@k / Recall@k. **This is the data-model layer behind CBIR systems in Lectures 10–12**"*

Đổi "flower" thành "fish" là ra đúng đề tài. Nhóm dùng thêm ba khối đặc trưng cổ điển bên cạnh embedding 512 chiều.

## 2.2 Vì sao KHÔNG chọn từng mô hình còn lại

Nguyên tắc chung: **mô hình dữ liệu phải khớp với đặc tính dữ liệu**. Slide 5 liệt kê 5 đặc tính khiến người ta cần các mô hình phức tạp — đối chiếu thì dữ liệu của nhóm **đơn giản ở đúng những chiều đó**:

| Đặc tính (slide 5) | Dữ liệu của nhóm |
|---|---|
| Heterogeneity — nhiều định dạng, schema, access pattern | ❌ **Một loại phương tiện duy nhất**: ảnh PNG 384×384 |
| Structural nesting — chương, cảnh, khung hình lồng nhau | ❌ **Phẳng**: mỗi ảnh là một đơn vị độc lập, không lồng nhau |
| Evolving schemas — định dạng và thuộc tính mới xuất hiện | ❌ **Lược đồ đã đóng băng** từ khi chốt dữ liệu |
| Cross-media relationships — hyperlink, đồng bộ, dẫn xuất | ❌ **Không có**: ảnh không trỏ tới nhau |
| Volume — BLOB lớn + quan hệ cấu trúc | ⚠️ Nhỏ: < 1 GB |

Chính vì dữ liệu đơn giản ở bốn chiều đầu nên các mô hình sinh ra để giải quyết chúng đều **thừa**.

---

### ❌ Relational thuần

> Slide 6–7: *"Data represented in flat table structures... Limitations: difficulty representing complex multimedia structures"*

**Vì sao không:** không có kiểu vector và **không có toán tử khoảng cách**. Muốn tìm top-5 phải kéo toàn bộ 1.085 vector ra khỏi CSDL rồi tính ở tầng ứng dụng — khi đó CSDL chỉ còn là kho chứa, không còn là "hệ CSDL quản trị các đặc trưng" như mục 3 của đề yêu cầu.

Slide 56 nói thẳng: *"Relational/OR: great for exact attributes; **poor native support for ANN at scale**"*.

**Trả lời phản biện này thế nào:** nhận xét đó đúng **ở quy mô lớn**. pgvector đã thêm ANN (HNSW/IVFFlat) vào nền quan hệ, và ở 1.085 vector thì ngay cả quét tuần tự chính xác cũng chỉ mất dưới 1 ms. Nhóm sẽ **đo và báo cáo cả thời gian lẫn recall** của hai cách, dùng số liệu thật để chứng minh lựa chọn.

---

### ❌ Object-Oriented (OODBMS)

> Slide 11: *"Objects map naturally to multimedia entities: Document, Image, VideoClip, Museum, Scene... Inheritance: share common attributes/methods... Encapsulation: data and behavior stored together"*

**Vì sao không:** OODBMS giải quyết **kế thừa, đóng gói hành vi, và OID để điều hướng đối tượng**. Hệ của nhóm:

- Chỉ có **một lớp thực thể ảnh**, không có phân cấp `Image`/`Video`/`Audio` để kế thừa
- Không cần **hành vi lưu trong CSDL** — mọi xử lý nằm ở package `fishcbir/`
- Không có **điều hướng theo OID** — truy vấn là k-NN trên vector, không phải đi theo tham chiếu đối tượng

Thêm nữa, slide 43 nhận xét OODBMS *"weaker SQL interoperability historically"* — mất hệ sinh thái SQL mà không đổi lại được gì cho bài toán này.

---

### ❌ NoSQL (document / key-value / wide-column)

> Slide 44: *"Why MM apps use them: schema evolution, large catalogs, CDN-like object refs... Trade-off: **weaker multi-document ACID** vs easier horizontal scale"*

**Vì sao không:** ba động lực chính của NoSQL đều không có ở đây.

| Động lực NoSQL | Tình trạng của nhóm |
|---|---|
| Schema evolution | Lược đồ đã đóng băng |
| Large catalogs, horizontal scale | 1.085 bản ghi, một máy thừa sức |
| Nested arrays tránh join explosion | Dữ liệu phẳng, chỉ 2 bảng chính |

Và cái giá thì có thật: **nhất quán yếu hơn**. Phần đánh giá của nhóm cần một snapshot cố định để tính Precision@5 và mAP — nhất quán cuối sẽ khiến cùng một truy vấn cho kết quả khác nhau giữa hai lần đo.

Slide 47 cũng nêu wide-column *"Not ideal for ad-hoc multi-attribute similarity search alone"* — đúng thứ hệ này làm.

---

### ❌ Graph

> Slide 49: *"Multimedia systems are rich in relationships: cites, similar-to, appears-in, derived-from"* · Slide 52: *"**Weaker alone for bulk storage of BLOBs or pure k-NN on high-dim vectors**"*

**Vì sao không:** graph mạnh ở **điều hướng nhiều bước** (multi-hop). Dữ liệu của nhóm **không có quan hệ nào giữa các ảnh** — không có `APPEARS_IN`, `DERIVED_FROM`, `CITES`. Quan hệ duy nhất là `ảnh → thuộc về → loài`, một khóa ngoại đơn giản.

Slide 52 nói thẳng graph **yếu với k-NN trên vector nhiều chiều** — chính là phép truy vấn duy nhất của hệ này.

Một lưu ý: cạnh `SIMILAR_TO` trong slide 50 nghe có vẻ hợp, nhưng nó đòi **tính sẵn và lưu cố định** độ tương đồng giữa các cặp. Hệ của nhóm tính độ tương đồng **lúc truy vấn** với ảnh mới chưa có trong CSDL — không dựng trước cạnh được.

---

### ⚠️ Vector DB thuần (Milvus, Qdrant, Pinecone)

> Slide 56: *"**Vector DB: specialized for similarity; still needs metadata store for rich filters**"* · *"Production MM systems are often polyglot: object store + catalog + vector index"*

**Đây là lựa chọn gần đúng nhất, và là phản biện đáng gờm nhất.** Lý do không chọn:

| | |
|---|---|
| **Vẫn phải có kho metadata riêng** | Chính slide 56 nói vậy. Chọn Milvus nghĩa là phải quản **hai hệ**: Milvus cho vector + một CSDL quan hệ cho loài/họ/split |
| **Mất ACID giữa vector và metadata** | Hai hệ riêng thì không có giao dịch chung |
| **Thừa ở quy mô này** | Milvus, Qdrant sinh ra cho hàng triệu tới hàng tỉ vector. Nhóm có 1.085 |
| **pgvector đã đủ** | Có `<->` (L2), `<=>` (cosine), `<#>` (inner product) và index HNSW/IVFFlat — đúng các chỉ mục slide 54 liệt kê |

**Nói gọn khi vấn đáp:** PostgreSQL + pgvector cho nhóm **cả hai thứ trong một hệ, một giao dịch** — metadata quan hệ và tìm kiếm tương đồng. Vector DB chuyên dụng chỉ cho một nửa, nửa còn lại vẫn phải dựng thêm.

## 2.3 Vị trí trên dãy tiến hóa của bài giảng

```
Relational → Object-Oriented → Object-Relational → NoSQL → Graph → Vector
                                      ▲                              ▲
                                      └──────── HỆ CỦA NHÓM ─────────┘
                                   nền ORDBMS          +  kiểu Vector
                                  (PostgreSQL)            (pgvector)
```

Nhóm **không nhảy cóc** tới cuối dãy, mà dừng ở **Object-Relational rồi mở rộng bằng kiểu Vector** — đúng con đường slide 42 mô tả: *"Extensions (PostGIS, pgvector) push ORDBMS further toward multimedia & similarity"*.

Lý do: dãy tiến hóa trong slide 3 là **mỗi mô hình giải một điểm yếu của mô hình trước** cho dữ liệu đa phương tiện. Dữ liệu của nhóm không mắc những điểm yếu mà OO, NoSQL, Graph sinh ra để giải — nó chỉ mắc đúng **một** điểm yếu của Relational thuần: **không tìm kiếm tương đồng được**. Và pgvector vá đúng chỗ đó.

---

# Phần 3 — Vận dụng mô hình Vector (Lecture 7)

> Slide 2 (L7): *"Each record (document, image, audio clip) → N-dimensional feature vector... Features: TF-IDF weights (text), **color histogram bins (image)**, MFCC stats (audio)"*

Hệ của nhóm hiện thực đúng mô hình không gian vector này, với **bốn khối đặc trưng lưu thành bốn cột vector riêng**:

| Khối | Chiều | Nội dung |
|---|---|---|
| `color` | 285 | Color moments Lab · histogram HSV 4 dải · màu trội k-means |
| `texture` | 118 | LBP đa tỉ lệ · GLCM 4 hướng · Gabor |
| `shape` | 98 | Tỉ số hình học · Hu moments · Fourier descriptors · contour signature |
| `deep` | 512 | ResNet18 sau global average pooling |

### Vì sao tách bốn cột thay vì một vector 1.013 chiều

Slide 54 nêu *"Record: id + dense vector (dim d) + optional payload metadata"* — tức mô hình chuẩn là **một** vector. Nhóm tách làm bốn, có chủ đích:

1. **Chạy được ablation** — đo riêng đóng góp của từng khối, trả lời mục 2 của đề về "giá trị thông tin của đặc trưng", mà không phải trích lại đặc trưng
2. **Mỗi khối một độ đo phù hợp** — slide 54: *"Distance metrics: cosine, Euclidean (L2), inner product — **choose to match training**"*. Histogram dùng Chi-square/Bhattacharyya, vector deep dùng cosine, tỉ số hình học dùng L2. Gộp một vector thì buộc phải dùng chung một độ đo
3. **Bảng phân rã khoảng cách** cho mục 4b — hiện `d_màu`, `d_kết_cấu`, `d_hình_dáng`, `d_deep` riêng cho từng ảnh trong top-5

### Chuẩn hóa — slide 2 và 6 của Lecture 7

Slide 2 (L7) nêu *"vectors must be comparable (same feature definition)... **normalization required**"*, slide 6 đưa công thức similarity chuẩn hóa theo độ dài vector.

Nhóm áp dụng ở hai mức:
- **Trong khối**: z-score từng chiều, tham số `mean`/`std` tính **chỉ trên phần gallery của từng fold** để tránh rò rỉ dữ liệu
- **Giữa các khối**: đưa mỗi khoảng cách về `[0,1]` rồi hợp nhất `d_total = Σ wᵢ·dᵢ`

Không chuẩn hóa thì 285 chiều màu sẽ nhấn chìm 7 chiều Hu moments.

### Chỉ mục — slide 54

> *"Exact k-NN is O(N·d); ANN indexes trade a little recall for large speedups. Common indexes: HNSW, IVF, PQ, LSH"*

Nhóm sẽ **đo cả hai**: quét tuần tự chính xác và index HNSW của pgvector, báo cáo **cả thời gian lẫn recall**.

Giả thuyết cần kiểm chứng, chưa khẳng định trước: ở 1.085 vector, HNSW có thể **không nhanh hơn** quét tuần tự mà còn giảm recall, vì nó là tìm kiếm xấp xỉ và chi phí duyệt đồ thị không được đền bù. Nếu đo ra đúng vậy thì đó là **bằng chứng thực nghiệm cho lựa chọn kiến trúc tập trung**, không phải thất bại.

---

# Phần 4 — Bảng tóm tắt để trả lời nhanh

| Câu hỏi | Trả lời một câu | Slide neo |
|---|---|---|
| Architectural style? | **Centralized** — một site DBMS, quy mô nhỏ, không có người dùng phân tán | L4 tr.5 |
| Storage principle? | **Homogeneity** — một lược đồ, một API; chỉ có một loại phương tiện nên separation không áp dụng | L4 tr.12 |
| Kiểu triển khai? | **Client–server 3 tầng** — nhưng đây không phải distributed | L4 tr.5 |
| Mô hình dữ liệu? | **Object-Relational + Vector** — PostgreSQL 17 + pgvector | L5 tr.40, 42 |
| Sao không Relational thuần? | Không có kiểu vector, không có toán tử khoảng cách | L5 tr.56 |
| Sao không OO? | Không có phân cấp kế thừa, không cần hành vi trong CSDL, không điều hướng OID | L5 tr.11, 43 |
| Sao không NoSQL? | Lược đồ cố định, 1.085 bản ghi, và cần ACID cho phần đánh giá | L5 tr.44 |
| Sao không Graph? | Không có quan hệ giữa các ảnh; graph yếu với k-NN nhiều chiều | L5 tr.49, 52 |
| Sao không Vector DB thuần? | Vẫn phải dựng thêm kho metadata; pgvector cho cả hai trong một giao dịch | L5 tr.56 |
| Khi nào mới cần phân tán? | Từ ~10⁷ vector hoặc tải truy vấn cao. Hiện 1.085 | — |
| Client–server có phải phân tán? | **Không.** Distributed = fragments/replicas across sites | L4 tr.5 |

---

# Phần 5 — Ba phản biện khó nhất và cách trả lời

### "Sao không dùng vector database cho đúng bài?"

Slide 56 nói *"Vector DB: specialized for similarity; **still needs metadata store** for rich filters"*. Chọn Milvus là phải quản hai hệ và mất ACID giữa vector với metadata. PostgreSQL + pgvector cho cả hai trong một giao dịch. Ở 1.085 vector, lợi thế quy mô của vector DB chuyên dụng không phát huy.

### "Relational không hợp cho đa phương tiện, sao vẫn dùng?"

Đúng với **Relational thuần** — và nhóm không dùng cái đó. Nhóm dùng **Object-Relational**, mà slide 40 định nghĩa là *"keep SQL/relational strengths while adding object features for multimedia"*, với PostgreSQL là ví dụ đầu tiên. Slide 42 chỉ rõ pgvector là phần mở rộng đưa ORDBMS tới similarity search.

### "Ảnh không nằm trong CSDL thì có còn gọi là CSDL đa phương tiện không?"

Có. Slide 12 nêu rõ homogeneity có thể hiện thực bằng *"unified catalog + typed LOB columns **or object store backend**"* — để BLOB ở kho ngoài là một trong hai cách chuẩn. CSDL vẫn quản trị toàn bộ metadata và đặc trưng, vẫn là nơi thực hiện truy vấn tương đồng. Và nhóm có `verify_integrity` để đảm bảo toàn vẹn giữa bảng và thư mục ảnh — chính là phần ACID bị thiếu được bù lại bằng quy trình.

---

# Tham chiếu slide

| Nội dung | Bài giảng | Trang |
|---|---|---|
| Centralized vs Distributed vs Hybrid | L4 MMDS Architecture | 5 |
| Separation / Homogeneity / Hybrid principle | L4 | 8–14 |
| Dãy tiến hóa mô hình dữ liệu | L5 MM data model | 3 |
| Đặc tính dữ liệu đa phương tiện | L5 | 5 |
| Hạn chế của Relational | L5 | 6–8 |
| OODBMS | L5 | 10–12 |
| ORDBMS, PostgreSQL, pgvector | L5 | 40–43 |
| NoSQL | L5 | 44–48 |
| Graph | L5 | 49–52 |
| Vector data model | L5 | 53–56 |
| Mô hình không gian vector, chuẩn hóa | L7 Vector database | 2–6 |
