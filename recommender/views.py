from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Hotels, HotelsAmenities, Amenities, Locations, HotelViews, ViewHistories, FavoriteHotels, Bookings, HotelReviews, SearchHistory, HotelImages, Rooms
from collections import Counter
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
from django.db.models import Min

# --- BIẾN TOÀN CỤC ĐỂ LƯU MODEL (CACHE) ---
global_data = {}


def get_min_room_prices(hotel_ids):
    """
    Helper: Lấy giá phòng thấp nhất cho mỗi hotel
    
    Args:
        hotel_ids: List of hotel IDs
    
    Returns:
        Dict {hotel_id: min_price}
    """
    if not hotel_ids:
        return {}
    
    # Query lấy giá phòng thấp nhất cho mỗi hotel
    min_prices = Rooms.objects.filter(
        hotel_id__in=hotel_ids,
        price__isnull=False
    ).values('hotel_id').annotate(
        min_price=Min('price')
    )
    
    return {item['hotel_id']: item['min_price'] for item in min_prices}


def get_hotel_amenities():
    # Lấy amenity của từng hotel nối thành 1 chuỗi có danh key(hotel_id):value(string)
    amenties_qs = HotelsAmenities.objects.select_related('amenity').all().values(
        'hotel_id', 'amenity__name'
    )
    hotel_amenities = {}
    for ha in amenties_qs:
        hotel_id = ha['hotel_id']
        amenity_name = ha['amenity__name']
        if hotel_id not in hotel_amenities:
            hotel_amenities[hotel_id] = []
        hotel_amenities[hotel_id].append(amenity_name)
    # Trả về 1 cặp key:value
    return {k: ' '.join(v) for k, v in hotel_amenities.items()}

def get_hotel_views():
    """Lấy view_type của từng hotel"""
    view_qs = HotelViews.objects.all().values('hotel_id', 'view_type')
    hotel_views = {}
    for hv in view_qs:
        hotel_id = hv['hotel_id']
        view_type = hv['view_type'] or ''
        if hotel_id not in hotel_views:
            hotel_views[hotel_id] = []
        hotel_views[hotel_id].append(view_type)
    return {k: ' '.join(v) for k, v in hotel_views.items()}

def train_model():
    
    print("🔄 Đang huấn luyện AI...")
    
    # 1. Lấy dữ liệu Hotels kèm Location
    hotels_qs = Hotels.objects.select_related('location').all().values(
        'id', 'name', 'description', 'address', 
        'price_range', 'design_style', 'type', 'star_rating',
        'location__name', 'location__parent__name'
    )
    df_hotels = pd.DataFrame(list(hotels_qs))
    
    if df_hotels.empty:
        print("⚠️ Không có hotels trong database!")
        return
    
    # 2. Lấy amenities
    hotel_amenities = get_hotel_amenities()
    df_hotels['amenities'] = df_hotels['id'].map(hotel_amenities).fillna('')
    hotel_views = get_hotel_views()
    df_hotels['views'] = df_hotels['id'].map(hotel_views).fillna('')

    # Tăng trọng số của những từ quan trọng hơn để có đc weight cao
    location_weights = (df_hotels['location__name'].fillna('')+ " ")
    price_weights = (df_hotels['price_range'].fillna('')+ " ") * 2
    type_weights = (df_hotels['type'].fillna('')+ " ") * 2
    

    
    # 3. Tạo "Soup" (Gộp tất cả thông tin)
    df_hotels['soup'] = (
        df_hotels['name'].fillna('') + " " + 
        df_hotels['description'].fillna('') + " " + 
        df_hotels['address'].fillna('') + " " +
        location_weights + " " +
        price_weights + " " +
        type_weights + " " +
        df_hotels['design_style'].fillna('') + " " +
        df_hotels['star_rating'].astype(str).fillna('') + " sao " +
        (df_hotels['location__parent__name'].fillna('') + " ")*2 +
        df_hotels['amenities'] + " " +
        df_hotels['views']
    )
    
    # 4. Tính TF-IDF và Cosine Similarity
    VIETNAMESE_STOP_WORDS = [
    'là', 'và', 'của', 'những', 'cái', 'việc', 'tại', 'trong', 'các', 'cho', 'được', 'với', 
    'khách sạn', 'hotel', 'phòng', 'nơi' # Những từ này khách sạn nào cũng có -> nên bỏ
    ]
    tfidf = TfidfVectorizer(min_df=1, ngram_range=(1, 2), stop_words=VIETNAMESE_STOP_WORDS)
    tfidf_matrix = tfidf.fit_transform(df_hotels['soup'])
    cosine_sim = linear_kernel(tfidf_matrix, tfidf_matrix)
    
    # 5. Lưu vào cache
    global_data['df'] = df_hotels
    global_data['sim'] = cosine_sim
    global_data['indices'] = pd.Series(df_hotels.index, index=df_hotels['id']).drop_duplicates()
    
    print(f"✅ AI đã sẵn sàng! Đã load {len(df_hotels)} hotels.")

# Gọi train khi server khởi động
try:
    train_model()
except Exception as e:
    print(f"⚠️ Chưa thể train model: {e}")


# --- API ENDPOINTS ---

@api_view(['GET'])
def get_recommendations(request, hotel_id):
    """API gợi ý hotels tương tự"""
    try:
        hotel_id = int(hotel_id)
        
        # Check model đã train chưa
        if not global_data:
            return Response({"error": "Model chưa được train"}, status=503)
        
        indices = global_data['indices']
        cosine_sim = global_data['sim']
        df = global_data['df']
        
        if hotel_id not in indices.index:
            return Response({"message": "Hotel not found"}, status=404)
            
        # Lấy index của hotel
        idx = indices[hotel_id]
        
        # Tính điểm similarity
        # lấy số điểm tương đồng của hotel_id trong 1 hàng của ma trận và convert về dạng chỉ mục(cột, giá trị)
        sim_scores = list(enumerate(cosine_sim[idx]))
        # sắp xếp
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
        
        # Lấy top 10 (bỏ chính nó)
        limit = int(request.query_params.get('limit', 10))
        sim_scores = sim_scores[1:limit+1]
        hotel_indices = [i[0] for i in sim_scores]
        
        # Lấy thông tin source hotel
        source_row = df[df['id'] == hotel_id].iloc[0]
        
        # Lấy thông tin hotels
        result_df = df.iloc[hotel_indices][['id', 'name', 'address', 'star_rating', 'location__name', 
                                             'price_range', 'type', 'design_style', 'location__parent__name']]
        results = result_df.to_dict('records')
        
        # Lấy thumbnail cho mỗi hotel
        result_hotel_ids = [r['id'] for r in results]
        hotel_thumbnails = {}
        thumbnail_images = HotelImages.objects.filter(
            hotel_id__in=result_hotel_ids,
            caption='Thumbnail'
        ).values('hotel_id', 'image_url')
        for img in thumbnail_images:
            hotel_thumbnails[img['hotel_id']] = img['image_url']
        
        # Lấy giá phòng thấp nhất cho mỗi hotel
        min_room_prices = get_min_room_prices(result_hotel_ids)
        
        # Xử lý kết quả
        import math
        for i, result in enumerate(results):
            # Thêm thumbnail
            result['thumbnail'] = hotel_thumbnails.get(result['id'])
            
            # Thêm min_room_price
            result['min_room_price'] = min_room_prices.get(result['id'])
            
            # Xóa các field phụ không cần trả về
            del result['price_range']
            del result['type']
            del result['design_style']
            
            # Thay NaN bằng None để JSON serialize được
            for key, value in list(result.items()):
                if isinstance(value, float) and math.isnan(value):
                    result[key] = None
        
        return Response({
            "source_hotel_id": hotel_id,
            "source_hotel_name": source_row.get('name'),
            "recommendations": results
        })
        
    except Exception as e:
        return Response({"error": str(e)}, status=500)



@api_view(['POST'])
def retrain_model(request):
    """API để retrain tất cả models (Content-Based + Collaborative)"""
    try:
        # Retrain Content-Based (Phase 1)
        train_model()
        
        # Retrain Collaborative Filtering (Phase 2)
        from .collaborative import train_collaborative_model
        cf_success = train_collaborative_model()
        
        return Response({
            "message": "Tất cả models đã được train lại!",
            "content_based": "✅ Success",
            "collaborative": "✅ Success" if cf_success else "⚠️ Không đủ dữ liệu"
        })
    except Exception as e:
        return Response({"error": str(e)}, status=500)


# --- REAL-TIME PERSONALIZATION API ---

@api_view(['POST'])
def track_user_action(request):
    """
    🚀 Real-time Personalization API
    
    Java backend gọi API này khi user có action mới.
    Tự động cập nhật cold_start và CF model.
    
    Request Body:
    {
        "user_id": 1,
        "action_type": "view" | "book" | "favorite" | "review",
        "hotel_id": 123,
        "metadata": {
            "view_duration": 120,  // seconds (for view)
            "rating": 8.5          // (for review)
        }
    }
    """
    try:
        from .models import Accounts
        from . import collaborative
        
        data = request.data
        user_id = data.get('user_id')
        action_type = data.get('action_type')
        hotel_id = data.get('hotel_id')
        metadata = data.get('metadata', {})
        
        if not all([user_id, action_type, hotel_id]):
            return Response({
                "error": "Missing required fields: user_id, action_type, hotel_id"
            }, status=400)
        
        # Validate action_type
        valid_actions = ['view', 'book', 'favorite', 'review']
        if action_type not in valid_actions:
            return Response({
                "error": f"Invalid action_type. Must be one of: {valid_actions}"
            }, status=400)
        
        # 1. Cập nhật cold_start = False nếu còn là True
        cold_start_updated = False
        try:
            account = Accounts.objects.get(id=user_id)
            if account.cold_start:
                account.cold_start = False
                account.save()
                cold_start_updated = True
        except Accounts.DoesNotExist:
            return Response({"error": "User not found"}, status=404)
        
        # 2. Incremental update CF model
        cf_updated = False
        if collaborative.cf_global_data:
            # Tính rating score dựa trên action_type
            rating_map = {
                'view': 2.0 + min(metadata.get('view_duration', 0) / 180, 1.0),  # 2-3
                'favorite': 4.0,
                'book': 5.0,
                'review': metadata.get('rating', 4.0)
            }
            rating = rating_map.get(action_type, 2.0)
            
            # Update user-item matrix
            user_item_matrix = collaborative.cf_global_data.get('user_item_matrix')
            if user_item_matrix is not None:
                if user_id in user_item_matrix.index:
                    if hotel_id in user_item_matrix.columns:
                        # Cập nhật score (lấy max với score hiện tại)
                        current = user_item_matrix.loc[user_id, hotel_id]
                        user_item_matrix.loc[user_id, hotel_id] = max(current, rating)
                        cf_updated = True
        
        # 3. Lưu vào view_histories nếu là action view
        view_history_saved = False
        if action_type == 'view':
            from django.utils import timezone
            
            # Lấy thông tin hotel để snapshot
            try:
                hotel = Hotels.objects.select_related('location').get(id=hotel_id)
                
                ViewHistories.objects.create(
                    account_id=user_id,
                    hotel_id=hotel_id,
                    viewed_at=timezone.now(),
                    view_duration_seconds=metadata.get('view_duration', 0),
                    clicked_booking=metadata.get('clicked_booking', False),
                    clicked_favorite=metadata.get('clicked_favorite', False),
                    view_source=metadata.get('view_source', 'DIRECT'),
                    search_query=metadata.get('search_query'),
                    location_id=hotel.location_id if hotel.location else None,
                    hotel_star_rating=hotel.star_rating,
                    hotel_type=hotel.type,
                    hotel_price_range=hotel.price_range,
                    hotel_price_per_night=hotel.price_per_night_from,
                    hotel_average_rating=hotel.average_rating
                )
                view_history_saved = True
            except Hotels.DoesNotExist:
                pass  # Hotel không tồn tại, bỏ qua
        
        # 4. Lưu vào favorite_hotels nếu là action favorite
        favorite_saved = False
        if action_type == 'favorite':
            from django.utils import timezone
            
            # Dùng get_or_create để tránh duplicate
            _, created = FavoriteHotels.objects.get_or_create(
                account_id=user_id,
                hotel_id=hotel_id,
                defaults={'created_at': timezone.now()}
            )
            favorite_saved = created  # True nếu tạo mới, False nếu đã tồn tại
        
        return Response({
            "status": "success",
            "user_id": user_id,
            "action_type": action_type,
            "hotel_id": hotel_id,
            "cold_start_updated": cold_start_updated,
            "cf_model_updated": cf_updated,
            "view_history_saved": view_history_saved,
            "favorite_saved": favorite_saved,
            "message": "Action tracked successfully"
        })
        
    except Exception as e:
        import traceback
        return Response({
            "error": str(e),
            "traceback": traceback.format_exc()
        }, status=500)


# --- PHASE 3: SEARCH-BASED RECOMMENDATIONS ---

def is_cold_start_user(user_id):
    """
    Kiểm tra user có phải cold start không.
    Dựa vào cột cold_start trong bảng accounts
    """
    from .models import Accounts
    try:
        account = Accounts.objects.get(id=user_id)
        return account.cold_start
    except Accounts.DoesNotExist:
        return True  # User không tồn tại -> coi như cold start


def get_popular_hotels_list(limit=10):
    """
    Helper: Lấy danh sách popular hotels sử dụng HYBRID APPROACH
    Kết hợp các thuật toán đã tạo trong collaborative.py và hybrid.py:
    - Item-Based CF scores (từ collaborative.py)
    - Rating-based popularity
    - Booking/View/Favorite counts để tính overall popularity
    """
    from . import collaborative
    from django.db.models import Count
    
    # 1. Lấy tất cả hotels với rating
    hotels = Hotels.objects.select_related('location').filter(
        average_rating__isnull=False
    ).order_by('-average_rating', '-total_reviews')
    
    if not hotels.exists():
        return []
    
    # 2. Lấy collaborative filtering signals nếu có
    cf_hotel_scores = {}
    if collaborative.cf_global_data:
        # Lấy các hotels được nhiều users yêu thích (từ user-item matrix)
        user_item_matrix = collaborative.cf_global_data.get('user_item_matrix')
        if user_item_matrix is not None:
            # Tính tổng ratings cho mỗi hotel = popularity dựa trên CF
            hotel_popularity = user_item_matrix.sum(axis=0)  # Sum over all users
            max_pop = hotel_popularity.max() if hotel_popularity.max() > 0 else 1
            
            for hotel_id in user_item_matrix.columns:
                cf_hotel_scores[hotel_id] = float(hotel_popularity[hotel_id]) / max_pop
    
    # 3. Lấy booking/view/favorite counts
    booking_counts = dict(
        Bookings.objects.values('room__hotel_id').annotate(
            count=Count('id')
        ).values_list('room__hotel_id', 'count')
    )
    view_counts = dict(
        ViewHistories.objects.values('hotel_id').annotate(
            count=Count('id')
        ).values_list('hotel_id', 'count')
    )
    favorite_counts = dict(
        FavoriteHotels.objects.values('hotel_id').annotate(
            count=Count('id')
        ).values_list('hotel_id', 'count')
    )
    
    max_booking = max(booking_counts.values()) if booking_counts else 1
    max_view = max(view_counts.values()) if view_counts else 1
    max_favorite = max(favorite_counts.values()) if favorite_counts else 1
    
    # 4. Tính hybrid popularity score
    scored_hotels = []
    for hotel in hotels:
        # CF score (từ collaborative.py)
        cf_score = cf_hotel_scores.get(hotel.id, 0) * 3.0  # Weight = 3
        
        # Engagement scores (normalized)
        booking_score = (booking_counts.get(hotel.id, 0) / max_booking) * 5.0  # Weight = 5
        view_score = (view_counts.get(hotel.id, 0) / max_view) * 1.0  # Weight = 1
        favorite_score = (favorite_counts.get(hotel.id, 0) / max_favorite) * 3.0  # Weight = 3
        
        # Rating score
        rating_score = ((hotel.average_rating or 0) / 5.0) * 2.0  # Weight = 2
        review_score = min((hotel.total_reviews or 0) / 100.0, 1.0) * 1.5  # Cap at 100 reviews
        
        # Total hybrid score
        popularity_score = cf_score + booking_score + view_score + favorite_score + rating_score + review_score
        
        scored_hotels.append({
            'hotel': hotel,
            'popularity_score': round(popularity_score, 4),
            'breakdown': {
                'cf_score': round(cf_score, 4),
                'booking_score': round(booking_score, 4),
                'view_score': round(view_score, 4),
                'favorite_score': round(favorite_score, 4),
                'rating_score': round(rating_score, 4),
                'review_score': round(review_score, 4)
            }
        })
    
    # 5. Sort by hybrid popularity score
    scored_hotels.sort(key=lambda x: x['popularity_score'], reverse=True)
    
    # 6. Lấy thumbnails cho popular hotels
    top_hotels = scored_hotels[:limit]
    hotel_ids = [item['hotel'].id for item in top_hotels]
    hotel_thumbnails = {}
    images = HotelImages.objects.filter(
        hotel_id__in=hotel_ids,
        caption='Thumbnail'
    ).values('hotel_id', 'image_url')
    for img in images:
        hotel_thumbnails[img['hotel_id']] = img['image_url']
    
    # 7. Lấy giá phòng thấp nhất cho popular hotels
    min_room_prices = get_min_room_prices(hotel_ids)
    
    return [{
        'id': item['hotel'].id,
        'name': item['hotel'].name,
        'address': item['hotel'].address,
        'star_rating': item['hotel'].star_rating,
        'average_rating': item['hotel'].average_rating,
        'total_reviews': item['hotel'].total_reviews,
        'location': item['hotel'].location.name if item['hotel'].location else None,
        'thumbnail': hotel_thumbnails.get(item['hotel'].id),
        'min_room_price': min_room_prices.get(item['hotel'].id)
    } for item in top_hotels]

@api_view(['GET'])
def get_smart_recommendations(request, user_id):
    """
    🚀 API CHÍNH CHO GIAO DIỆN HOTEL
    
    Lấy hotel recommendations dựa trên:
    1. ViewHistory của user -> Lấy hotels đã xem
    2. Đưa vào thuật toán HYBRID (hybrid.py) để tìm similar hotels
    3. Kết hợp với Collaborative Filtering (collaborative.py)
    4. Cold start users -> Fallback về popular hotels (hybrid approach)
    
    Query params:
        - limit: Số lượng kết quả (mặc định 10)
        - content_weight: Trọng số Content-Based (mặc định 0.6)
        - collab_weight: Trọng số Collaborative (mặc định 0.4)
    """
    try:
        user_id = int(user_id)
        limit = int(request.query_params.get('limit', 10))
        content_weight = float(request.query_params.get('content_weight', 0.6))
        collab_weight = float(request.query_params.get('collab_weight', 0.4))
        
        from .hybrid import get_hybrid_recommendations, get_personalized_recommendations
        from . import collaborative
        
        # 1. Kiểm tra cold start
        if is_cold_start_user(user_id):
            return Response({
                "user_id": user_id,
                "is_cold_start": True,
                "message": "Chào mừng bạn! Đây là các khách sạn phổ biến được nhiều người yêu thích.",
                "recommendation_type": "popular_hybrid",
                "recommendations": get_popular_hotels_list(limit)
            })
        
        # 2. Lấy ViewHistory gần nhất của user (hotels đã xem)
        recent_views = ViewHistories.objects.filter(
            account_id=user_id
        ).select_related('hotel').order_by('-viewed_at')[:5]  # Lấy 5 hotels gần nhất
        
        viewed_hotel_ids = [v.hotel_id for v in recent_views if v.hotel_id]
        
        # 3. Nếu có ViewHistory -> Sử dụng HYBRID recommendations
        all_hybrid_recs = {}
        
        for hotel_id in viewed_hotel_ids:
            # Gọi thuật toán hybrid.py cho từng hotel đã xem
            hybrid_recs = get_hybrid_recommendations(
                hotel_id=hotel_id,
                user_id=user_id,
                content_weight=content_weight,
                collab_weight=collab_weight,
                limit=limit
            )
            
            # Merge results (cộng dồn scores)
            for rec in hybrid_recs:
                hid = rec['hotel_id']
                if hid not in viewed_hotel_ids:  # Không gợi ý hotels đã xem
                    if hid not in all_hybrid_recs:
                        all_hybrid_recs[hid] = {
                            'hotel_id': hid,
                            'hybrid_score': rec['hybrid_score'],
                            'content_score': rec['content_score'],
                            'collab_score': rec['collab_score'],
                            'source_hotels': [hotel_id]
                        }
                    else:
                        # Cộng dồn scores và merge sources
                        all_hybrid_recs[hid]['hybrid_score'] += rec['hybrid_score']
                        all_hybrid_recs[hid]['content_score'] += rec['content_score']
                        all_hybrid_recs[hid]['collab_score'] += rec['collab_score']
                        all_hybrid_recs[hid]['source_hotels'].append(hotel_id)
        
        # 4. Nếu không đủ kết quả từ hybrid -> Thêm personalized CF
        if len(all_hybrid_recs) < limit:
            personalized_recs = get_personalized_recommendations(user_id, limit)
            for rec in personalized_recs:
                hid = rec.get('hotel_id') or rec.get('id')
                if hid and hid not in viewed_hotel_ids and hid not in all_hybrid_recs:
                    all_hybrid_recs[hid] = {
                        'hotel_id': hid,
                        'hybrid_score': rec.get('cf_score', 0) * 0.8,  # Slightly lower weight
                        'content_score': 0,
                        'collab_score': rec.get('cf_score', 0),
                        'source_hotels': [],
                        'from_cf': True
                    }
        
        # 5. Sort và lấy top results
        sorted_recs = sorted(
            all_hybrid_recs.values(),
            key=lambda x: x['hybrid_score'],
            reverse=True
        )[:limit]
        
        # 6. Enrich với hotel info từ database
        if sorted_recs:
            hotel_ids = [rec['hotel_id'] for rec in sorted_recs]
            hotels = Hotels.objects.filter(id__in=hotel_ids).select_related('location').values(
                'id', 'name', 'address', 'star_rating', 'average_rating', 'total_reviews', 'location__name'
            )
            hotels_dict = {h['id']: h for h in hotels}
            
            # Lấy thumbnail cho mỗi hotel
            hotel_thumbnails = {}
            images = HotelImages.objects.filter(
                hotel_id__in=hotel_ids,
                caption='Thumbnail'
            ).values('hotel_id', 'image_url')
            for img in images:
                hotel_thumbnails[img['hotel_id']] = img['image_url']
            
            # Lấy giá phòng thấp nhất cho mỗi hotel
            min_room_prices = get_min_room_prices(hotel_ids)
            
            for rec in sorted_recs:
                hotel_info = hotels_dict.get(rec['hotel_id'], {})
                rec['name'] = hotel_info.get('name')
                rec['address'] = hotel_info.get('address')
                rec['star_rating'] = hotel_info.get('star_rating')
                rec['average_rating'] = hotel_info.get('average_rating')
                rec['total_reviews'] = hotel_info.get('total_reviews')
                rec['location'] = hotel_info.get('location__name')
                rec['thumbnail'] = hotel_thumbnails.get(rec['hotel_id'])
                rec['min_room_price'] = min_room_prices.get(rec['hotel_id'])
                rec['hybrid_score'] = round(rec['hybrid_score'], 4)
                rec['content_score'] = round(rec['content_score'], 4)
                rec['collab_score'] = round(rec['collab_score'], 4)
        
        # 7. Lấy thông tin về history patterns cho response
        user_history = {
            'viewed_hotels_count': len(viewed_hotel_ids),
            'recently_viewed': [{
                'hotel_id': v.hotel_id,
                'hotel_name': v.hotel.name if v.hotel else None,
                'viewed_at': v.viewed_at.isoformat() if v.viewed_at else None
            } for v in recent_views[:3]]  # Top 3 gần nhất
        }
        
        return Response({
            "user_id": user_id,
            "is_cold_start": False,
            "recommendation_type": "hybrid",
            "algorithm_weights": {
                "content_based": content_weight,
                "collaborative": collab_weight
            },
            "user_history": user_history,
            "recommendations": sorted_recs
        })
        
    except Exception as e:
        import traceback
        return Response({
            "error": str(e),
            "traceback": traceback.format_exc()
        }, status=500)