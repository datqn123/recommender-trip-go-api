"""
Collaborative Filtering Module - Phase 2 (Optimized)
Xây dựng User-Item Rating Matrix và tính toán recommendations
dựa trên hành vi của users tương tự.
"""
import pandas as pd
import numpy as np
from scipy.sparse import csr_matrix, coo_matrix
from sklearn.metrics.pairwise import cosine_similarity
from django.db.models import Avg, F
from django.utils import timezone
from typing import List, Dict, Any, Optional, Tuple
import datetime

# --- CONSTANTS ---
WEIGHT_VIEW_BASE = 2.0
WEIGHT_FAVORITE = 4.0
WEIGHT_BOOKING = 5.0
WEIGHT_REVIEW_DEFAULT = 3.0

BONUS_DURATION_60S = 0.5
BONUS_DURATION_180S = 1.0
BONUS_CLICK_BOOKING = 1.0
BONUS_CLICK_FAVORITE = 1.0

# Time Decay configuration
DECAY_RATE = 0.05  # Score giảm 5% mỗi ngày
MIN_DECAY_FACTOR = 0.1  # Score không bao giờ giảm dưới 10% giá trị gốc

# --- GLOBAL CACHE ---
cf_global_data: Dict[str, Any] = {}


def calculate_time_decay(interaction_time: datetime.datetime) -> float:
    """
    Tính hệ số time decay dựa trên thời gian tương tác.
    Formula: 1 / (1 + decay_rate * days_ago)
    """
    if not interaction_time:
        return 1.0
    
    now = timezone.now()
    delta = now - interaction_time
    days_ago = max(0, delta.days)
    
    decay_factor = 1 / (1 + DECAY_RATE * days_ago)
    return max(decay_factor, MIN_DECAY_FACTOR)


def build_user_item_matrix() -> Optional[pd.DataFrame]:
    """
    Xây dựng User-Item Rating Matrix trực tiếp (Memory Efficient).
    Sử dụng approach "List of Dicts" -> DataFrame để de-duplicate,
    sau đó chuyển sang Sparse Matrix.
    """
    from .models import ViewHistories, FavoriteHotels, Bookings, HotelReviews
    
    print("🔄 Đang xây dựng User-Item Matrix (Optimized with Time Decay)...")
    
    # Store tuples: (user_id, hotel_id, rating, source)
    ratings_data: List[Dict[str, Any]] = []
    
    # 1. ViewHistories - Engagement-based scoring with Time Decay
    # Optimize query: chỉ lấy fields cần thiết
    view_qs = ViewHistories.objects.all().values(
        'account_id', 'hotel_id', 
        'view_duration_seconds', 'clicked_booking', 'clicked_favorite',
        'viewed_at'
    )
    
    count_views = 0
    for view in view_qs:
        if not view['hotel_id'] or not view['account_id']:
            continue
            
        score = WEIGHT_VIEW_BASE
        
        # Engagement Bonuses
        duration = view['view_duration_seconds'] or 0
        if duration > 60:
            score += BONUS_DURATION_60S
        if duration > 180:
            score += BONUS_DURATION_180S
        if view['clicked_booking']:
            score += BONUS_CLICK_BOOKING
        if view['clicked_favorite']:
            score += BONUS_CLICK_FAVORITE
            
        score = min(score, 5.0)
        
        # Apply Time Decay
        decay = calculate_time_decay(view['viewed_at'])
        final_score = score * decay
        
        ratings_data.append({
            'user_id': view['account_id'],
            'hotel_id': view['hotel_id'],
            'rating': final_score,
            'source': 'view'
        })
        count_views += 1

    print(f"  📍 ViewHistories: {count_views} records")
    
    # 2. FavoriteHotels
    fav_qs = FavoriteHotels.objects.all().values('account_id', 'hotel_id', 'created_at')
    for fav in fav_qs:
        decay = calculate_time_decay(fav['created_at'])
        ratings_data.append({
            'user_id': fav['account_id'],
            'hotel_id': fav['hotel_id'],
            'rating': WEIGHT_FAVORITE * decay,
            'source': 'favorite'
        })
    print(f"  ❤️ FavoriteHotels: {len(fav_qs)} records")
    
    # 3. Bookings
    booking_qs = Bookings.objects.filter(
        room__isnull=False,
        status__in=['CONFIRMED', 'COMPLETED']
    ).select_related('room__hotel').values('user_id', 'room__hotel_id', 'created_at')
    
    for booking in booking_qs:
        if booking['room__hotel_id']:
            decay = calculate_time_decay(booking['created_at'])
            ratings_data.append({
                'user_id': booking['user_id'],
                'hotel_id': booking['room__hotel_id'],
                'rating': WEIGHT_BOOKING * decay,
                'source': 'booking'
            })
    print(f"  🏨 Bookings: {len(booking_qs)} records")
    
    # 4. Reviews
    review_qs = HotelReviews.objects.filter(
        average_rating__isnull=False
    ).values('user_id', 'hotel_id', 'average_rating', 'created_at')
    
    for review in review_qs:
        decay = calculate_time_decay(review['created_at'])
        ratings_data.append({
            'user_id': review['user_id'],
            'hotel_id': review['hotel_id'],
            'rating': float(review['average_rating']) * decay,
            'source': 'review'
        })
    print(f"  ⭐ HotelReviews: {len(review_qs)} records")
    
    if not ratings_data:
        print("⚠️ Không có dữ liệu user behavior!")
        return None
        
    # Convert to DataFrame to handle duplicates (User-Item collision)
    # Nếu 1 user vừa view vừa book hotel -> Lấy max score
    df = pd.DataFrame(ratings_data)
    df_agg = df.groupby(['user_id', 'hotel_id'])['rating'].max().reset_index()
    
    print(f"✅ Tổng cộng: {len(df_agg)} unique interactions. Sparse Matrix Size: {df_agg['user_id'].nunique()}x{df_agg['hotel_id'].nunique()}")
    return df_agg


def train_collaborative_model() -> bool:
    """
    Train collaborative filtering model efficiently using Sparse Matrices.
    Tránh sử dụng pivot_table() vì nó tạo Dense Matrix gây tốn RAM.
    """
    print("\n🔄 Đang huấn luyện Collaborative Filtering Model (Optimized)...")
    
    df = build_user_item_matrix()
    
    if df is None or df.empty:
        print("⚠️ Không thể train CF model - không có dữ liệu!")
        return False
    
    # Map UserIDs và HotelIDs sang indices liên tục (0, 1, 2, ...)
    user_ids = sorted(df['user_id'].unique())
    hotel_ids = sorted(df['hotel_id'].unique())
    
    user_map = {uid: i for i, uid in enumerate(user_ids)}
    hotel_map = {hid: i for i, hid in enumerate(hotel_ids)}
    
    # Tạo coordinates cho Sparse Matrix
    row_indices = df['user_id'].map(user_map).values
    col_indices = df['hotel_id'].map(hotel_map).values
    data = df['rating'].values
    
    # Tạo CSR Matrix trực tiếp
    n_users = len(user_ids)
    n_hotels = len(hotel_ids)
    sparse_matrix = csr_matrix((data, (row_indices, col_indices)), shape=(n_users, n_hotels))
    
    # Tính Similarities
    # User Similarity: Cosine similarity giữa các hàng (users)
    user_similarity = cosine_similarity(sparse_matrix, dense_output=False)
    
    # Item Similarity: Cosine similarity giữa các cột (hotels)
    # Transpose matrix để rows là items
    item_matrix = sparse_matrix.T
    item_similarity = cosine_similarity(item_matrix, dense_output=False)
    
    # Lưu vào global cache
    # Lưu ý: user_similarity va item_similarity giờ là Sparse Matrices
    cf_global_data['user_item_matrix_sparse'] = sparse_matrix
    cf_global_data['user_similarity_sparse'] = user_similarity
    cf_global_data['item_similarity_sparse'] = item_similarity
    
    # Lưu mappings để lookup ngược lại
    cf_global_data['user_ids'] = user_ids
    cf_global_data['hotel_ids'] = hotel_ids
    
    # Để tương thích ngược với code cũ (nếu cần lookup nhanh score 1 user-item)
    # Chúng ta lưu thêm dict hoặc dùng sparse indexing
    # Ở đây ta sẽ dùng sparse indexing trong hàm get_recs để tiết kiệm RAM
    
    print(f"✅ CF Model đã sẵn sàng!")
    print(f"   - Users: {n_users}")
    print(f"   - Hotels: {n_hotels}")
    
    return True


def get_user_based_recommendations(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """
    User-Based Collaborative Filtering (Optimized for Sparse Matrix)
    """
    if not cf_global_data:
        return []
    
    user_ids = cf_global_data.get('user_ids', [])
    hotel_ids = cf_global_data.get('hotel_ids', [])
    sparse_matrix = cf_global_data.get('user_item_matrix_sparse')
    user_similarity = cf_global_data.get('user_similarity_sparse')
    
    if user_id not in user_ids:
        return []
    
    # Lấy index của target user
    u_idx = user_ids.index(user_id)
    
    # Lấy vector similarity của user này với tất cả users khác
    # user_similarity là sparse matrix (N x N)
    # Ta lấy row tương ứng -> result là sparse matrix (1 x N)
    sim_scores_sparse = user_similarity[u_idx]
    
    # Convert sang dense array chỉ cho row này để sort (N is usually manageable, N^2 is not)
    sim_scores = sim_scores_sparse.toarray().flatten()
    
    # Lấy indices của top similar users (bỏ chính nó - index u_idx)
    # argsort returns indices that would sort the array
    top_indices = np.argsort(sim_scores)[::-1]
    
    # Filter out self and 0 similarity
    similar_user_indices = [i for i in top_indices if i != u_idx and sim_scores[i] > 0][:20]  # Top 20 similar users
    
    if not similar_user_indices:
        return []

    # Dự đoán rating
    # Prediction formula: P(u, i) = sum(sim(u, v) * r(v, i)) / sum(|sim(u, v)|)
    # Vectorized implementation:
    # 1. Construct matrix of similar users' ratings (M users x K items)
    # 2. Construct vector of similarities (M users x 1)
    # 3. Weighted sum
    
    # Lấy ratings của similar users -> Sub-matrix (K x Items)
    similar_users_ratings = sparse_matrix[similar_user_indices]  # Returns CSR matrix
    
    # Weights (similarities)
    weights = sim_scores[similar_user_indices].reshape(-1, 1)  # K x 1
    
    # Weighted Sum: weights.T * ratings -> (1 x Items)
    # scikit-learn cosine_similarity returns values usually 0-1
    
    # Create diagonal matrix of weights for multiplication if needed, or simply multiply arrays
    # sparse matrix multiplication: (1xK) * (KxItems) = (1xItems)
    # We need to construct a sparse matrix for weights? No, simple multiplication is better
    
    # Manual weighted sum for transparency and sparse handle:
    # weighted_ratings = sum(sim * ratings)
    # Since weights is numpy array and ratings is CSR, we can do:
    # user_ratings_weighted = matrix product of weights and ratings
    
    # weights is (K, 1), similar_users_ratings is (K, Items)
    # We want (1, Items) -> (1, K) * (K, Items)
    weights_csr = csr_matrix(weights.T)
    prediction_scores = weights_csr.dot(similar_users_ratings).toarray().flatten()
    
    # Normalize by sum of weights (optional but good for accurate rating prediction)
    sum_weights = np.sum(weights)
    if sum_weights > 0:
        prediction_scores /= sum_weights
        
    # Filter out items user already rated
    user_rated_items_indices = sparse_matrix[u_idx].nonzero()[1]
    prediction_scores[user_rated_items_indices] = 0
    
    # Get top item indices
    top_item_indices = np.argsort(prediction_scores)[::-1][:limit]
    
    recommendations = []
    for idx in top_item_indices:
        score = prediction_scores[idx]
        if score > 0:
            recommendations.append({
                'hotel_id': hotel_ids[idx],
                'cf_score': round(float(score), 4)
            })
            
    return recommendations


def get_item_based_recommendations(hotel_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Item-Based Collaborative Filtering (Optimized)
    """
    if not cf_global_data:
        return []
    
    hotel_ids = cf_global_data.get('hotel_ids', [])
    item_similarity = cf_global_data.get('item_similarity_sparse')
    
    if hotel_id not in hotel_ids:
        return []
    
    h_idx = hotel_ids.index(hotel_id)
    
    # Lấy similarity row cho hotel này
    sim_scores = item_similarity[h_idx].toarray().flatten()
    
    # Sort
    top_indices = np.argsort(sim_scores)[::-1]
    
    recommendations = []
    # Skip self (index 0 implies max score usually)
    for idx in top_indices:
        if idx == h_idx:
            continue
            
        score = sim_scores[idx]
        if score > 0:
            recommendations.append({
                'hotel_id': hotel_ids[idx],
                'cf_score': round(float(score), 4)
            })
            if len(recommendations) >= limit:
                break
                
    return recommendations


def get_cf_recommendations(user_id=None, hotel_id=None, limit=10):
    """
    Main entry point cho CF recommendations
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
    
    # Merge and Dedup
    if user_id and hotel_id:
        seen = {}
        for rec in results:
            hid = rec['hotel_id']
            if hid not in seen:
                seen[hid] = rec
            else:
                if rec['cf_score'] > seen[hid]['cf_score']:
                    seen[hid] = rec
        results = sorted(seen.values(), key=lambda x: x['cf_score'], reverse=True)[:limit]
    
    return results


# Auto-train khi import (nếu có dữ liệu)
try:
    train_collaborative_model()
except Exception as e:
    print(f"⚠️ Chưa thể train CF model: {e}")
