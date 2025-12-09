from django.urls import path
from . import views

urlpatterns = [
    # Phase 1: Content-Based
    path('recommend/<int:hotel_id>/', views.get_recommendations, name='recommendations'),
    path('hotels/popular/', views.get_popular_hotels, name='popular-hotels'),
    
    # Phase 2: Hybrid Recommendations
    path('recommend/user/<int:user_id>/', views.get_user_recommendations, name='user-recommendations'),
    path('recommend/hybrid/<int:hotel_id>/', views.get_hybrid_recommendations, name='hybrid-recommendations'),
    
    # Admin
    path('model/retrain/', views.retrain_model, name='retrain-model'),
]
