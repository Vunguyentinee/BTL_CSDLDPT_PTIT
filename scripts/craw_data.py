import time
from bing_image_downloader import downloader

# Danh sách tên khoa học các loài cá cần tải
fish_species = [
    "Betta splendens",        # Cá xiêm / betta
    "Cyprinus carpio",        # Cá chép
    "Oreochromis niloticus",  # Cá rô phi
    "Salmo salar"             # Cá hồi Đại Tây Dương
]

for species in fish_species:
    print(f"Đang tải ảnh cho: {species}...")
    downloader.download(
        query=species,
        limit=50,                   # Số lượng ảnh cho mỗi loài
        output_dir="dataset_ca",    # Thư mục lưu
        adult_filter_off=True,
        force_replace=False,
        timeout=60,
        verbose=False
    )
    time.sleep(2)  # Nghỉ 2 giây giữa các loài để tránh bị chặn IP