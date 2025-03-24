import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

class AnomalyDetector:
    def __init__(self):
        self.model = IsolationForest(contamination=0.05, random_state=42)
        self.scaler = StandardScaler()
        self.is_fitted = False
        
    def fit(self, test_results):
        """
        Fit the anomaly detection model on test results
        
        Args:
            test_results: DataFrame with test execution metrics
                (execution_time, memory_usage, cpu_usage, etc.)
        """
        # Extract numerical features
        features = self._extract_features(test_results)
        
        # Scale features
        scaled_features = self.scaler.fit_transform(features)
        
        # Fit the model
        self.model.fit(scaled_features)
        self.is_fitted = True
        
    def detect_anomalies(self, test_results):
        """
        Detect anomalies in test results
        
        Args:
            test_results: DataFrame with test execution metrics
            
        Returns:
            DataFrame with anomaly scores and predictions
        """
        if not self.is_fitted:
            raise ValueError("Model is not fitted yet. Call fit() first.")
            
        # Extract numerical features
        features = self._extract_features(test_results)
        
        # Scale features
        scaled_features = self.scaler.transform(features)
        
        # Predict anomalies
        # -1 for anomalies, 1 for normal
        predictions = self.model.predict(scaled_features)
        
        # Get anomaly scores
        scores = self.model.decision_function(scaled_features)
        
        # Add predictions and scores to the original data
        result = test_results.copy()
        result['anomaly'] = predictions == -1
        result['anomaly_score'] = scores
        
        return result
        
    def _extract_features(self, test_results):
        """Extract numerical features from test results"""
        # Select only numerical columns
        numerical_cols = test_results.select_dtypes(include=[np.number]).columns
        return test_results[numerical_cols].fillna(0)