"""
Collaborative Filtering Module - Phase 2
Xây dựng User-Item Rating Matrix và tính toán recommendations
dựa trên hành vi của users tương tự.
"""
import pandas as pd
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.metrics.pairwise import cosine_similarity
from django.db.models import Avg

# --- GLOBAL CACHE ---
cf_global_data = {}


def build_user_item_matrix():
    """
    Xây dựng User-Item Rating Matrix từ nhiều nguồn dữ liệu:
    - ViewHistories: base 2.0 + bonus (duration/clickedBooking/clickedFavorite)
    - FavoriteHotels: 4.0
    - Bookings (hotel): 5.0  
    - HotelReviews: average_rating thực tế
    """
    from .models import ViewHistories, FavoriteHotels, Bookings, HotelReviews, Hotels
    
    print("🔄 Đang xây dựng User-Item Matrix...")
    
    ratings_list = []
    
    # 1. ViewHistories - Engagement-based scoring
    view_qs = ViewHistories.objects.all().values(
        'account_id', 'hotel_id', 
        'view_duration_seconds', 'clicked_booking', 'clicked_favorite'
    )
    
    for view in view_qs:
        score = 2.0  # Base score
        
        # Bonus từ engagement metrics
        duration = view.get('view_duration_seconds') or 0
        if duration > 60:
            score += 0.5  # Xem > 1 phút
        if duration > 180:
            score += 1  # Xem > 3 phút (rất quan tâm)
        if view.get('clicked_booking'):
            score += 1.0  # Click đặt phòng = rất quan tâm
        if view.get('clicked_favorite'):
            score += 1.0  # Thêm vào yêu thích
        
        score = min(score, 5.0)  # Cap at 5.0
        
        ratings_list.append({
            'user_id': view['account_id'],
            'hotel_id': view['hotel_id'],
            'rating': score,
            'source': 'view'
        })
    # in ra số lượng viewhistory
    print(f"  📍 ViewHistories: {len([r for r in ratings_list if r['source'] == 'view'])} records")
    
    # 2. FavoriteHotels - điểm sẽ là 4.0
    fav_qs = FavoriteHotels.objects.all().values('account_id', 'hotel_id')
    
    for fav in fav_qs:
        ratings_list.append({
            'user_id': fav['account_id'],
            'hotel_id': fav['hotel_id'],
            'rating': 4.0,
            'source': 'favorite'
        })
    
    print(f"  ❤️ FavoriteHotels: {len([r for r in ratings_list if r['source'] == 'favorite'])} records")
    
    # 3. Bookings (hotel type) - điểm sẽ là 5.0

    # Lấy userid-hotel_id từ bookings
    booking_qs = Bookings.objects.filter(
        room__isnull=False,
        status__in=['CONFIRMED', 'COMPLETED']
    ).select_related('room__hotel').values('user_id', 'room__hotel_id')
    
    for booking in booking_qs:
        if booking['room__hotel_id']:
            ratings_list.append({
                'user_id': booking['user_id'],
                'hotel_id': booking['room__hotel_id'],
                'rating': 5.0,
                'source': 'booking'
            })
    
    print(f"  🏨 Bookings: {len([r for r in ratings_list if r['source'] == 'booking'])} records")
    
    # 4. HotelReviews - Explicit rating
    review_qs = HotelReviews.objects.filter(
        average_rating__isnull=False
    ).values('user_id', 'hotel_id', 'average_rating')
    
    for review in review_qs:
        ratings_list.append({
            'user_id': review['user_id'],
            'hotel_id': review['hotel_id'],
            'rating': review['average_rating'],
            'source': 'review'
        })
    
    print(f"  ⭐ HotelReviews: {len([r for r in ratings_list if r['source'] == 'review'])} records")
    
    if not ratings_list:
        print("⚠️ Không có dữ liệu user behavior!")
        return None
    
    # Convert to DataFrame
    df = pd.DataFrame(ratings_list)
    
    # Aggregate ratings (lấy rating cao nhất nếu có nhiều sources)
    df_agg = df.groupby(['user_id', 'hotel_id'])['rating'].max().reset_index()
    
    print(f"✅ Tổng cộng: {len(df_agg)} user-hotel interactions từ {df['user_id'].nunique()} users và {df['hotel_id'].nunique()} hotels")
    
    return df_agg


def train_collaborative_model():
    """Train collaborative filtering model"""
    print("\n🔄 Đang huấn luyện Collaborative Filtering Model...")
    
    df = build_user_item_matrix()
    
    if df is None or df.empty:
        print("⚠️ Không thể train CF model - không có dữ liệu!")
        return False
    
    # Create user-item pivot table
    user_item_matrix = df.pivot_table(
        index='user_id', 
        columns='hotel_id', 
        values='rating',
        fill_value=0
    )
    
    # Đưa ma trận thưa thành ma trận vuông
    # Convert to sparse matrix for efficiency
    sparse_matrix = csr_matrix(user_item_matrix.values)
    
    # Tính User Similarity (User-Based CF)
    user_similarity = cosine_similarity(sparse_matrix)
    
    # Tính Item Similarity (Item-Based CF)
    item_similarity = cosine_similarity(sparse_matrix.T)
    
    # Lưu vào global cache
    cf_global_data['user_item_matrix'] = user_item_matrix
    cf_global_data['user_similarity'] = user_similarity
    cf_global_data['item_similarity'] = item_similarity
    cf_global_data['user_ids'] = user_item_matrix.index.tolist()
    cf_global_data['hotel_ids'] = user_item_matrix.columns.tolist()
    
    print(f"✅ CF Model đã sẵn sàng!")
    print(f"   - Users: {len(cf_global_data['user_ids'])}")
    print(f"   - Hotels: {len(cf_global_data['hotel_ids'])}")
    
    return True


def get_user_based_recommendations(user_id, limit=10):
    """
    User-Based Collaborative Filtering
    Gợi ý hotels mà các users tương tự đã thích
    """
    if not cf_global_data:
        return []
    
    user_ids = cf_global_data['user_ids']
    hotel_ids = cf_global_data['hotel_ids']
    user_item_matrix = cf_global_data['user_item_matrix']
    user_similarity = cf_global_data['user_similarity']
    
    if user_id not in user_ids:
        return []
    
    user_idx = user_ids.index(user_id)
    
    # Tìm top similar users
    sim_scores = list(enumerate(user_similarity[user_idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    
    # Bỏ chính user đó, lấy top 10 similar users
    similar_users = [i[0] for i in sim_scores[1:11]]
    
    # Tính predicted ratings cho mỗi hotel
    user_ratings = user_item_matrix.iloc[user_idx].values
    predictions = {}
    
    for hotel_idx, hotel_id in enumerate(hotel_ids):
        # Bỏ qua hotels đã interact
        if user_ratings[hotel_idx] > 0:
            continue
        
        # Weighted average từ similar users
        numerator = 0
        denominator = 0
        
        for sim_user_idx in similar_users:
            sim_score = user_similarity[user_idx][sim_user_idx]
            rating = user_item_matrix.iloc[sim_user_idx, hotel_idx]
            
            if rating > 0:
                numerator += sim_score * rating
                denominator += abs(sim_score)
        
        if denominator > 0:
            predictions[hotel_id] = numerator / denominator
    
    # Sort và lấy top recommendations
    sorted_predictions = sorted(predictions.items(), key=lambda x: x[1], reverse=True)
    recommendations = [
        {'hotel_id': hotel_id, 'cf_score': round(score, 4)}
        for hotel_id, score in sorted_predictions[:limit]
    ]
    
    return recommendations


def get_item_based_recommendations(hotel_id, limit=10):
    """
    Item-Based Collaborative Filtering
    Gợi ý hotels tương tự dựa trên interaction patterns
    """
    if not cf_global_data:
        return []
    
    hotel_ids = cf_global_data['hotel_ids']
    item_similarity = cf_global_data['item_similarity']
    
    if hotel_id not in hotel_ids:
        return []
    
    hotel_idx = hotel_ids.index(hotel_id)
    
    # Tìm similar hotels
    sim_scores = list(enumerate(item_similarity[hotel_idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    
    # Bỏ chính hotel đó, lấy top recommendations
    recommendations = []
    for idx, score in sim_scores[1:limit+1]:
        recommendations.append({
            'hotel_id': hotel_ids[idx],
            'cf_score': round(float(score), 4)
        })
    
    return recommendations


def get_cf_recommendations(user_id=None, hotel_id=None, limit=10):
    """
    Main entry point cho CF recommendations
    - Nếu có user_id: User-Based CF
    - Nếu có hotel_id: Item-Based CF
    - Nếu có cả 2: Kết hợp cả 2
    """
    results = []
    
    if user_id:
        user_recs = get_user_based_recommendations(user_id, limit)
        for rec in user_recs:
            rec['cf_type'] = 'user_based'
        results.extend(user_recs)
    
    if hotel_id:
        item_recs = get_item_based_recommendations(hotel_id, limit)
        for rec in item_recs:
            rec['cf_type'] = 'item_based'
        results.extend(item_recs)
    
    # Nếu có cả 2, merge và dedup
    if user_id and hotel_id:
        seen = {}
        merged = []
        for rec in results:
            hid = rec['hotel_id']
            if hid not in seen:
                seen[hid] = rec
            else:
                # Lấy score cao hơn
                if rec['cf_score'] > seen[hid]['cf_score']:
                    seen[hid] = rec
        results = sorted(seen.values(), key=lambda x: x['cf_score'], reverse=True)[:limit]
    
    return results


# Auto-train khi import (nếu có dữ liệu)
try:
    train_collaborative_model()
except Exception as e:
    print(f"⚠️ Chưa thể train CF model: {e}")
