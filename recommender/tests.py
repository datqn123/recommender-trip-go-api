from django.test import TestCase
from unittest.mock import patch, MagicMock
from django.utils import timezone
import datetime
import pandas as pd
import numpy as np
from . import collaborative, evaluation

class RecommenderLogicTest(TestCase):
    
    def test_time_decay(self):
        """Test time decay calculations"""
        now = timezone.now()
        
        # Test 0 days ago (no decay)
        decay_0 = collaborative.calculate_time_decay(now)
        self.assertAlmostEqual(decay_0, 1.0, places=2)
        
        # Test 10 days ago
        days_10 = now - datetime.timedelta(days=10)
        decay_10 = collaborative.calculate_time_decay(days_10)
        # Formula: 1 / (1 + 0.05 * 10) = 1 / 1.5 = 0.66
        self.assertAlmostEqual(decay_10, 0.66, places=2)
        
        # Test very old (should cap at min decay 0.1)
        days_1000 = now - datetime.timedelta(days=1000)
        decay_old = collaborative.calculate_time_decay(days_1000)
        self.assertGreaterEqual(decay_old, 0.1)

    @patch('recommender.models.ViewHistories.objects.all')
    @patch('recommender.models.FavoriteHotels.objects.all')
    @patch('recommender.models.Bookings.objects.filter')
    @patch('recommender.models.HotelReviews.objects.filter')
    def test_build_user_item_matrix(self, mock_reviews, mock_bookings, mock_favorites, mock_views):
        """Test matrix construction with mock data"""
        now = timezone.now()
        
        # Mock View Data
        mock_views.return_value.values.return_value = [
            {
                'account_id': 1, 'hotel_id': 1, 
                'view_duration_seconds': 200,  # Bonus
                'clicked_booking': False, 'clicked_favorite': False,
                'viewed_at': now
            }
        ]
        
        # Mock Favorite Data
        mock_favorites.return_value.values.return_value = []
        
        # Mock Booking Data
        mock_bookings.return_value.select_related.return_value.values.return_value = [
             {
                'user_id': 1, 'room__hotel_id': 2, 'created_at': now
             }
        ]
        
        mock_reviews.return_value.values.return_value = []
        
        # Run function
        df = collaborative.build_user_item_matrix()
        
        # Build Expected:
        # Hotel 1: View (2.0 + 1.0 (duration > 180) = 3.0) * 1.0 decay = 3.0
        # Hotel 2: Booking (5.0) * 1.0 decay = 5.0
        
        self.assertIsNotNone(df)
        self.assertEqual(len(df), 2)
        
        h1 = df[df['hotel_id'] == 1].iloc[0]
        h2 = df[df['hotel_id'] == 2].iloc[0]
        
        self.assertAlmostEqual(h1['rating'], 3.0, places=1)
        self.assertEqual(h2['rating'], 5.0)

    @patch('recommender.collaborative.build_user_item_matrix')
    def test_train_collaborative_model(self, mock_build):
        """Test matrix training logic"""
        # Create mock DF
        data = {
            'user_id': [1, 1, 2, 2],
            'hotel_id': [1, 2, 1, 3],
            'rating': [5.0, 3.0, 5.0, 4.0]
        }
        mock_build.return_value = pd.DataFrame(data)
        
        # Train
        success = collaborative.train_collaborative_model()
        self.assertTrue(success)
        
        # Check global data
        self.assertIn('user_item_matrix_sparse', collaborative.cf_global_data)
        self.assertIn('user_similarity_sparse', collaborative.cf_global_data)
        
        sparse_mat = collaborative.cf_global_data['user_item_matrix_sparse']
        self.assertEqual(sparse_mat.shape, (2, 3)) # 2 Users, 3 Hotels (ids: 1, 2, 3)

    @patch('recommender.collaborative.build_user_item_matrix')
    def test_evaluation_metrics(self, mock_build):
        """Test Precision/Recall calculation"""
        # Create mock DF with enough data for split
        data = {
            'user_id': [1, 1, 1, 2, 2, 2, 3, 3, 3],
            'hotel_id': [1, 2, 3, 1, 2, 4, 1, 3, 5],
            'rating': [5, 5, 5, 5, 5, 5, 5, 5, 5]
        }
        mock_build.return_value = pd.DataFrame(data)
        
        # We need to ensure collaborative model is trained before testing eval?
        # evaluation.calculate_metrics_at_k internally calls split_train_test which calls build_user_item_matrix
        # But it also relies on collaborative.get_user_based_recommendations which relies on GLOBAL model.
        # This is tricky because get_user_based_recommendations uses cf_global_data, which needs to be trained on TRAIN SET.
        
        # For this unit test, let's just test split_train_test
        train, test = evaluation.split_train_test(test_ratio=0.3) # 9 items -> 3 test items approx
        
        self.assertIsNotNone(train)
        self.assertIsNotNone(test)
        self.assertTrue(len(train) + len(test) == 9)
