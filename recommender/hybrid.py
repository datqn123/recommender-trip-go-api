"""
Hybrid Recommendation Module - Phase 2
Kết hợp Content-Based (Phase 1) và Collaborative Filtering (Phase 2)
"""
import math


def get_hybrid_recommendations(
    hotel_id, 
    user_id=None,
    content_weight=0.5,
    collab_weight=0.5,
    limit=10
):
    """
    Hybrid Recommendations kết hợp:
    - Content-Based: Từ global_data (views.py)
    - Collaborative Filtering: Từ cf_global_data (collaborative.py)
    
    Args:
        hotel_id: Hotel ID để tìm recommendations tương tự
        user_id: Optional user ID để personalize
        content_weight: Trọng số Content-Based (α)
        collab_weight: Trọng số Collaborative Filtering (β)
        limit: Số lượng kết quả
    
    Returns:
        List of hybrid recommendations với hybrid_score
    """
    from . import views
    from . import collaborative
    
    # 1. Lấy Content-Based recommendations (Phase 1)
    content_recs = {}
    
    if views.global_data:
        indices = views.global_data.get('indices', {})
        cosine_sim = views.global_data.get('sim')
        df = views.global_data.get('df')
        
        if hotel_id in indices.index and cosine_sim is not None:
            idx = indices[hotel_id]
            sim_scores = list(enumerate(cosine_sim[idx]))
            sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
            
            # Lấy top recommendations (bỏ chính nó)
            for i, score in sim_scores[1:limit*2]:  # Lấy nhiều hơn để merge
                rec_hotel_id = df.iloc[i]['id']
                content_recs[rec_hotel_id] = float(score)
    
    # 2. Lấy Collaborative Filtering recommendations
    collab_recs = {}
    
    if collaborative.cf_global_data:
        # Item-Based CF từ hotel_id
        item_recs = collaborative.get_item_based_recommendations(hotel_id, limit*2)
        for rec in item_recs:
            collab_recs[rec['hotel_id']] = rec['cf_score']
        
        # User-Based CF nếu có user_id
        if user_id:
            user_recs = collaborative.get_user_based_recommendations(user_id, limit*2)
            for rec in user_recs:
                hid = rec['hotel_id']
                # Merge: lấy max score nếu đã có
                if hid not in collab_recs or rec['cf_score'] > collab_recs[hid]:
                    collab_recs[hid] = rec['cf_score']
    
    # 3. Normalize scores (0-1)
    def normalize_scores(scores_dict):
        if not scores_dict:
            return {}
        max_score = max(scores_dict.values())
        min_score = min(scores_dict.values())
        range_score = max_score - min_score if max_score != min_score else 1
        return {k: (v - min_score) / range_score for k, v in scores_dict.items()}
    
    content_recs = normalize_scores(content_recs)
    collab_recs = normalize_scores(collab_recs)
    
    # 4. Kết hợp với weighted average
    all_hotel_ids = set(content_recs.keys()) | set(collab_recs.keys())
    all_hotel_ids.discard(hotel_id)  # Loại bỏ hotel gốc
    
    hybrid_scores = {}
    for hid in all_hotel_ids:
        content_score = content_recs.get(hid, 0)
        collab_score = collab_recs.get(hid, 0)
        
        # Weighted combination
        hybrid_score = (content_weight * content_score) + (collab_weight * collab_score)
        
        hybrid_scores[hid] = {
            'hotel_id': hid,
            'hybrid_score': round(hybrid_score, 4),
            'content_score': round(content_score, 4),
            'collab_score': round(collab_score, 4),
        }
    
    # 5. Sort và return top results
    sorted_results = sorted(
        hybrid_scores.values(), 
        key=lambda x: x['hybrid_score'], 
        reverse=True
    )[:limit * 2]  # Lấy nhiều hơn để diversity filter
    
    # 6. Apply diversity
    diverse_results = apply_diversity(sorted_results, limit)
    
    return diverse_results


def apply_diversity(recommendations, limit=10, max_per_location=3, max_per_type=4):
    """
    Đa dạng hóa kết quả recommendations:
    - Giới hạn số hotels cùng location
    - Mix các loại hotels khác nhau (HOTEL, RESORT, HOMESTAY, VILLA)
    
    Args:
        recommendations: List of recommendation dicts
        limit: Số kết quả cuối cùng
        max_per_location: Max hotels cùng location
        max_per_type: Max hotels cùng type
    """
    from .models import Hotels
    
    if not recommendations:
        return []
    
    # Lấy thông tin location và type của các hotels
    hotel_ids = [rec['hotel_id'] for rec in recommendations]
    hotels_info = Hotels.objects.filter(id__in=hotel_ids).select_related('location').values(
        'id', 'location__name', 'type'
    )
    hotel_meta = {h['id']: {'location': h['location__name'], 'type': h['type']} for h in hotels_info}
    
    # Apply diversity limits
    location_count = {}
    type_count = {}
    diverse_results = []
    
    for rec in recommendations:
        hid = rec['hotel_id']
        meta = hotel_meta.get(hid, {})
        loc = meta.get('location', 'Unknown')
        hotel_type = meta.get('type', 'HOTEL')
        
        # Check location limit
        if location_count.get(loc, 0) >= max_per_location:
            continue
        
        # Check type limit
        if type_count.get(hotel_type, 0) >= max_per_type:
            continue
        
        # Add to results
        diverse_results.append(rec)
        location_count[loc] = location_count.get(loc, 0) + 1
        type_count[hotel_type] = type_count.get(hotel_type, 0) + 1
        
        # Stop if we have enough
        if len(diverse_results) >= limit:
            break
    
    return diverse_results


def get_personalized_recommendations(user_id, limit=10):
    """
    Personalized Recommendations cho user cụ thể
    Dựa hoàn toàn vào Collaborative Filtering
    
    Args:
        user_id: User ID
        limit: Số lượng kết quả
    
    Returns:
        List of personalized recommendations
    """
    from . import collaborative
    from .models import Hotels, HotelImages, Rooms
    from django.db.models import Min
    
    # Lấy User-Based CF recommendations
    recs = collaborative.get_user_based_recommendations(user_id, limit)
    
    if not recs:
        return []
    
    # Enrich với hotel info
    hotel_ids = [rec['hotel_id'] for rec in recs]
    hotels = Hotels.objects.filter(id__in=hotel_ids).select_related('location').values(
        'id', 'name', 'address', 'star_rating', 'average_rating', 'location__name'
    )
    hotels_dict = {h['id']: h for h in hotels}
    
    # Lấy thumbnail cho mỗi hotel (caption='Thumbnail')
    hotel_thumbnails = {}
    images = HotelImages.objects.filter(
        hotel_id__in=hotel_ids, 
        caption='Thumbnail'
    ).values('hotel_id', 'image_url')
    for img in images:
        hotel_thumbnails[img['hotel_id']] = img['image_url']
    
    # Lấy giá phòng thấp nhất cho mỗi hotel
    min_prices = Rooms.objects.filter(
        hotel_id__in=hotel_ids,
        price__isnull=False
    ).values('hotel_id').annotate(
        min_price=Min('price')
    )
    hotel_min_prices = {item['hotel_id']: item['min_price'] for item in min_prices}
    
    results = []
    for rec in recs:
        hotel_info = hotels_dict.get(rec['hotel_id'], {})
        results.append({
            'hotel_id': rec['hotel_id'],
            'name': hotel_info.get('name'),
            'address': hotel_info.get('address'),
            'star_rating': hotel_info.get('star_rating'),
            'average_rating': hotel_info.get('average_rating'),
            'location': hotel_info.get('location__name'),
            'thumbnail': hotel_thumbnails.get(rec['hotel_id']),
            'min_room_price': hotel_min_prices.get(rec['hotel_id']),
            'cf_score': rec['cf_score'],
            'recommendation_type': 'personalized'
        })
    
    return results
