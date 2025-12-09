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
    )[:limit]
    
    return sorted_results


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
    from .models import Hotels
    
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
            'cf_score': rec['cf_score'],
            'recommendation_type': 'personalized'
        })
    
    return results
