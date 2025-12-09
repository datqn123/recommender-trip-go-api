# Phase 2 API Testing Guide

## Base URL
```
http://localhost:8001/api/
```

---

## 1. Content-Based Recommendations (Phase 1)

### URL
```
GET /api/recommend/{hotel_id}/
```

### Example
```bash
curl http://localhost:8001/api/recommend/1/
curl http://localhost:8001/api/recommend/100/?limit=5
```

### Response JSON
```json
{
    "source_hotel_id": 1,
    "source_hotel_name": "Vinpearl Resort Nha Trang",
    "recommendations": [
        {
            "id": 45,
            "name": "Vinpearl Resort Đà Nẵng",
            "address": "Đà Nẵng",
            "star_rating": 5,
            "location__name": "Đà Nẵng",
            "similarity_score": 0.8923,
            "similarity_reasons": ["Cùng 5 sao", "Cùng loại: RESORT"]
        }
    ]
}
```

---

## 2. Personalized Recommendations (Phase 2 - CF)

### URL
```
GET /api/recommend/user/{user_id}/
```

### Example
```bash
curl http://localhost:8001/api/recommend/user/1/
curl http://localhost:8001/api/recommend/user/5/?limit=5
```

### Response JSON
```json
{
    "user_id": 1,
    "recommendation_type": "personalized",
    "recommendations": [
        {
            "hotel_id": 123,
            "name": "Mường Thanh Grand Đà Nẵng",
            "address": "Đà Nẵng",
            "star_rating": 4,
            "average_rating": 8.5,
            "location": "Đà Nẵng",
            "cf_score": 4.5123
        }
    ]
}
```

### Nếu user chưa có dữ liệu
```json
{
    "user_id": 999,
    "message": "Không đủ dữ liệu để gợi ý. Hãy xem và đánh giá thêm hotels!",
    "recommendations": []
}
```

---

## 3. Hybrid Recommendations (Phase 2)

### URL
```
GET /api/recommend/hybrid/{hotel_id}/?user_id={user_id}
```

### Query Parameters
| Param | Default | Description |
|-------|---------|-------------|
| user_id | null | Optional - để personalize |
| content_weight | 0.5 | Trọng số Content-Based (0-1) |
| collab_weight | 0.5 | Trọng số Collaborative (0-1) |
| limit | 10 | Số kết quả |

### Examples
```bash
# Không có user - chỉ dùng Content-Based + Item-Based CF
curl http://localhost:8001/api/recommend/hybrid/1/

# Có user - thêm User-Based CF
curl "http://localhost:8001/api/recommend/hybrid/1/?user_id=5"

# Điều chỉnh trọng số (70% Content, 30% CF)
curl "http://localhost:8001/api/recommend/hybrid/1/?user_id=5&content_weight=0.7&collab_weight=0.3"
```

### Response JSON
```json
{
    "source_hotel_id": 1,
    "source_hotel_name": "Vinpearl Resort Nha Trang",
    "user_id": 5,
    "weights": {
        "content_based": 0.5,
        "collaborative": 0.5
    },
    "recommendations": [
        {
            "hotel_id": 78,
            "hybrid_score": 0.8234,
            "content_score": 0.7500,
            "collab_score": 0.8968,
            "name": "Fusion Resort Đà Nẵng",
            "address": "Đà Nẵng",
            "star_rating": 5,
            "average_rating": 9.1,
            "location": "Đà Nẵng"
        }
    ]
}
```

---

## 4. Retrain Model

### URL
```
POST /api/model/retrain/
```

### Example
```bash
curl -X POST http://localhost:8001/api/model/retrain/
```

### Response JSON
```json
{
    "message": "Tất cả models đã được train lại!",
    "content_based": "✅ Success",
    "collaborative": "✅ Success"
}
```

---

## 5. Popular Hotels

### URL
```
GET /api/hotels/popular/
```

### Example
```bash
curl http://localhost:8001/api/hotels/popular/?limit=5
```

### Response JSON
```json
{
    "popular_hotels": [
        {
            "id": 1,
            "name": "Vinpearl Resort Nha Trang",
            "address": "Nha Trang",
            "star_rating": 5,
            "average_rating": 9.2,
            "total_reviews": 1523,
            "location": "Nha Trang"
        }
    ]
}
```

---

## Quick Test Script (PowerShell)

```powershell
# 1. Start server
python manage.py runserver 8001

# 2. Test endpoints (run in another terminal)
Invoke-RestMethod http://localhost:8001/api/recommend/1/ | ConvertTo-Json -Depth 5
Invoke-RestMethod http://localhost:8001/api/recommend/user/1/ | ConvertTo-Json -Depth 5
Invoke-RestMethod "http://localhost:8001/api/recommend/hybrid/1/?user_id=1" | ConvertTo-Json -Depth 5
```
