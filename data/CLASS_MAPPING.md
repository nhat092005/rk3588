# Class Mapping — sfchd_shel5k

Gộp `sfchd` + `shel5k` thành 1 dataset 5 class, dùng bởi `scripts/data/prepare_sfchd_shel5k.py`
để tạo `data/sfchd_shel5k/processed/`. Quyết định đầy đủ + bằng chứng nguồn:
`docs/PPE_RK3588S_Research_Master_Guide.md`, mục 0.2.1–0.2.2.

Đây là tài liệu tham khảo — `prepare_sfchd_shel5k.py` không parse file này, có dict Python
riêng mã hóa đúng bảng dưới đây.

`scripts/data/prepare_sfchd_5class.py` (tạo `data/sfchd_5class/processed/`, Lựa chọn 1: SFCHD
đơn lẻ 5 class) dùng lại đúng dict đó, chỉ lấy phần `sfchd` — nên thứ tự index 5 class của
`sfchd_5class` và `sfchd_shel5k` giống hệt nhau.

## Index cố định (5 class cuối)

| Index | Class |
|---|---|
| 0 | `person` |
| 1 | `helmet` |
| 2 | `head` |
| 3 | `safety_clothes` |
| 4 | `self_clothes` |

## Nguồn từng class

| Class cuối | Từ `sfchd` | Từ `shel5k` |
|---|---|---|
| `person` | `person` | `person_with_helmet` + `person_no_helmet` (gộp bỏ trạng thái) |
| `helmet` | `helmet` | `helmet` |
| `head` | `head` | `head` |
| `safety_clothes` | `safety_clothes` | (không có) |
| `self_clothes` | `self_clothes` | (không có) |

## Bị loại (xóa object khỏi label khi gộp, không map vào class nào)

| Dataset | Class bị loại | Lý do |
|---|---|---|
| `sfchd` | `blur_head`, `blur_clothes` | Ảnh nhiễu/mờ do camera, không phải object class thật |
| `shel5k` | `head_with_helmet` | Box lồng gần trùng với `helmet`, gây nhiễu NMS/loss nếu tách riêng |
| `shel5k` | `face` | Không liên quan PPE compliance |

## Bảng remap theo index gốc (dùng trực tiếp trong code)

`sfchd` (`data/sfchd/processed/classes.txt` thứ tự: person, helmet, self_clothes, safety_clothes, head, blur_head, blur_clothes):

| Index gốc | Class gốc | Index mới |
|---:|---|---:|
| 0 | person | 0 |
| 1 | helmet | 1 |
| 2 | self_clothes | 4 |
| 3 | safety_clothes | 3 |
| 4 | head | 2 |
| 5 | blur_head | bỏ |
| 6 | blur_clothes | bỏ |

`shel5k` (`data/shel5k/processed/classes.txt` thứ tự: helmet, head, head_with_helmet, person_with_helmet, person_no_helmet, face):

| Index gốc | Class gốc | Index mới |
|---:|---|---:|
| 0 | helmet | 1 |
| 1 | head | 2 |
| 2 | head_with_helmet | bỏ |
| 3 | person_with_helmet | 0 |
| 4 | person_no_helmet | 0 |
| 5 | face | bỏ |

## Dedup ảnh

Đã verify bằng perceptual hash (dHash 64-bit, toàn bộ 5.000×12.372 ảnh, threshold hamming ≤5):
**0 cặp trùng** giữa `sfchd` và `shel5k`. Không cần dedup khi gộp.
