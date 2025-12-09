from django.urls import path
from . import views

urlpatterns = [
    # Phase 1: Content-Based
    path('recommend/<int:hotel_id>/', views.get_recommendations, name='recommendations'),
    path('hotels/popular/', views.get_popular_hotels, name='popular-hotels'),
    path('hotels/top-star/', views.get_top_star_hotels, name='top-star-hotels'),
    
    # Admin
    path('model/retrain/', views.retrain_model, name='retrain-model'),
]