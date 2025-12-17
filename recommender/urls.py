from django.urls import path
from . import views

urlpatterns = [
    # Content-Based: Gợi ý hotels tương tự dựa trên hotel_id
    path('recommend/<int:hotel_id>/', views.get_recommendations, name='recommendations'),
    
    # Smart Recommendations: API CHÍNH cho giao diện hotel
    # Tích hợp hybrid algorithms (Content-Based + Collaborative Filtering)
    path('recommend/smart/<int:user_id>/', views.get_smart_recommendations, name='smart-recommendations'),
    
    # Real-time Personalization: Track user actions
    path('user/action/', views.track_user_action, name='track-action'),
    
    # Admin: Retrain models
    path('model/retrain/', views.retrain_model, name='retrain-model'),
]
