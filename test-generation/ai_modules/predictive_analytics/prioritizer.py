import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

class TestPrioritizer:
    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.is_fitted = False
        
    def fit(self, test_history):
        """
        Fit the model on test execution history
        
        Args:
            test_history: DataFrame with test execution history
                (test_id, execution_time, failure_rate, last_failed, etc.)
        """
        # Prepare features and target
        X, y = self._prepare_data(test_history)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Fit the model
        self.model.fit(X_scaled, y)
        self.is_fitted = True
        
    def prioritize(self, tests):
        """
        Prioritize tests based on their likelihood of failing
        
        Args:
            tests: DataFrame with test information
            
        Returns:
            DataFrame with tests sorted by priority
        """
        if not self.is_fitted:
            raise ValueError("Model is not fitted yet. Call fit() first.")
            
        # Prepare features
        X = self._extract_features(tests)
        
        # Scale features
        X_scaled = self.scaler.transform(X)
        
        # Predict failure probability
        failure_probs = self.model.predict_proba(X_scaled)[:, 1]  # Probability of class 1 (failure)
        
        # Add failure probability to tests
        result = tests.copy()
        result['failure_probability'] = failure_probs
        
        # Calculate priority score (combination of failure probability and impact)
        if 'impact' in result.columns:
            result['priority_score'] = result['failure_probability'] * result['impact']
        else:
            result['priority_score'] = result['failure_probability']
            
        # Sort by priority score in descending order
        result = result.sort_values('priority_score', ascending=False)
        
        return result
        
    def _prepare_data(self, test_history):
        """Prepare features and target from test history"""
        # Extract features
        X = self._extract_features(test_history)
        
        # Extract target (whether the test failed or not)
        y = test_history['failed'].astype(int)
        
        return X, y
        
    def _extract_features(self, tests):
        """Extract features from test data"""
        features = []
        
        # Basic features
        if 'execution_time' in tests.columns:
            features.append('execution_time')
            
        if 'failure_rate' in tests.columns:
            features.append('failure_rate')
            
        if 'last_failed' in tests.columns:
            # Convert to days since last failure
            tests['days_since_failure'] = (pd.Timestamp.now() - pd.to_datetime(tests['last_failed'])).dt.days
            features.append('days_since_failure')
            
        if 'code_churn' in tests.columns:
            features.append('code_churn')
            
        if 'test_age' in tests.columns:
            features.append('test_age')
            
        if 'complexity' in tests.columns:
            features.append('complexity')
            
        # Check if we have enough features
        if not features:
            raise ValueError("No valid features found in the test data")
            
        # Return the feature matrix
        return tests[features].fillna(0)
    
    def feature_importance(self):
        """Get feature importance from the model"""
        if not self.is_fitted:
            raise ValueError("Model is not fitted yet. Call fit() first.")
            
        # Get feature names
        feature_names = self._extract_features(pd.DataFrame()).columns.tolist()
        
        # Get feature importance
        importance = self.model.feature_importances_
        
        # Create a DataFrame with feature names and importance
        result = pd.DataFrame({
            'feature': feature_names,
            'importance': importance
        })
        
        # Sort by importance in descending order
        result = result.sort_values('importance', ascending=False)
        
        return result