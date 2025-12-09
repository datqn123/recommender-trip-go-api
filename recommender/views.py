from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Hotels, HotelsAmenities, Amenities, Locations, HotelViews
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

# --- BIẾN TOÀN CỤC ĐỂ LƯU MODEL (CACHE) ---
global_data = {}

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
    location_weights = (df_hotels['location__name'].fillna('')+ " ") * 3
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
        
        # Thêm similarity score, similarity_reason và xóa NaN
        import math
        for i, result in enumerate(results):
            result['similarity_score'] = round(float(sim_scores[i][1]), 4)
            
            # Tìm lý do giống nhau
            reasons = []
            if result.get('location__name') == source_row.get('location__name'):
                reasons.append(f"Cùng địa điểm: {result.get('location__name')}")
            elif result.get('location__parent__name') == source_row.get('location__parent__name'):
                reasons.append(f"Cùng tỉnh/thành: {result.get('location__parent__name')}")
            
            if result.get('price_range') == source_row.get('price_range') and result.get('price_range'):
                reasons.append(f"Cùng phân khúc giá: {result.get('price_range')}")
            
            if result.get('star_rating') == source_row.get('star_rating') and result.get('star_rating'):
                reasons.append(f"Cùng {int(result.get('star_rating'))} sao")
            
            if result.get('type') == source_row.get('type') and result.get('type'):
                reasons.append(f"Cùng loại: {result.get('type')}")
            
            if result.get('design_style') == source_row.get('design_style') and result.get('design_style'):
                reasons.append(f"Cùng phong cách: {result.get('design_style')}")
            
            result['similarity_reasons'] = reasons if reasons else ["Tương đồng về mô tả và tiện nghi"]
            
            # Xóa các field phụ không cần trả về
            del result['price_range']
            del result['type']
            del result['design_style']
            del result['location__parent__name']
            
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


@api_view(['GET'])
def get_popular_hotels(request):
    """API lấy hotels phổ biến (theo rating và reviews)"""
    try:
        limit = int(request.query_params.get('limit', 10))
        
        hotels = Hotels.objects.select_related('location').filter(
            average_rating__isnull=False
        ).order_by('-average_rating', '-total_reviews')[:limit]
        
        results = []
        for hotel in hotels:
            results.append({
                'id': hotel.id,
                'name': hotel.name,
                'address': hotel.address,
                'star_rating': hotel.star_rating,
                'average_rating': hotel.average_rating,
                'total_reviews': hotel.total_reviews,
                'location': hotel.location.name if hotel.location else None
            })
        
        return Response({"popular_hotels": results})
        
    except Exception as e:
        return Response({"error": str(e)}, status=500)


@api_view(['POST'])
def retrain_model(request):
    """API để retrain model (Gọi khi có hotels mới)"""
    try:
        train_model()
        return Response({"message": "Model đã được train lại!"})
    except Exception as e:
        return Response({"error": str(e)}, status=500)