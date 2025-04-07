import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend to avoid GUI issues
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import threading

class AnomalyDetector:
    def __init__(self, contamination=0.05):
        self.model = IsolationForest(contamination=contamination, random_state=42, n_jobs=-1)  # Use all CPU cores
        self.scaler = StandardScaler()
        self.is_fitted = False
        self.history = []
        self._lock = threading.Lock()  # Add thread safety
        
    def fit(self, test_results):
        """
        Fit the anomaly detection model on test results
        
        Args:
            test_results: DataFrame with test execution metrics
                (execution_time, memory_usage, cpu_usage, etc.)
        """
        # Extract numerical features
        features = self._extract_features(test_results)
        
        if len(features) == 0 or features.shape[1] == 0:
            raise ValueError("No valid numerical features found in test results")
            
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
            # Auto-fit if not fitted yet
            self.fit(test_results)
            
        # Extract numerical features
        features = self._extract_features(test_results)
        
        if len(features) == 0 or features.shape[1] == 0:
            # Handle case with no valid features
            result = test_results.copy()
            result['anomaly'] = False
            result['anomaly_score'] = 0.0
            result['detection_time'] = datetime.now()
            return result
            
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
        
        # Add timestamp for tracking
        result['detection_time'] = datetime.now()
        
        # Store in history with thread safety
        with self._lock:
            if len(self.history) > 100:  # Limit history size
                self.history = self.history[-100:]
            self.history.append(result)
        
        return result
    
    def analyze_trends(self, metric_name, window_size=10):
        """
        Analyze trends in a specific metric over time
        
        Args:
            metric_name: Name of the metric to analyze
            window_size: Size of the rolling window for trend analysis
            
        Returns:
            DataFrame with trend analysis
        """
        if not self.history:
            raise ValueError("No detection history available")
            
        # Combine all history data
        combined = pd.concat(self.history)
        
        # Sort by timestamp
        combined = combined.sort_values('detection_time')
        
        # Calculate rolling statistics
        if metric_name in combined.columns:
            combined[f'{metric_name}_rolling_mean'] = combined[metric_name].rolling(window=window_size).mean()
            combined[f'{metric_name}_rolling_std'] = combined[metric_name].rolling(window=window_size).std()
            combined[f'{metric_name}_trend'] = combined[metric_name].diff().rolling(window=window_size).mean()
            
            return combined
        else:
            raise ValueError(f"Metric '{metric_name}' not found in detection history")
    
    def visualize_anomalies(self, test_results, x_feature, y_feature, output_path=None):
        """
        Visualize anomalies in a 2D plot
        
        Args:
            test_results: DataFrame with test results and anomaly predictions
            x_feature: Feature to plot on x-axis
            y_feature: Feature to plot on y-axis
            output_path: Path to save the visualization
            
        Returns:
            Path to the saved visualization or None
        """
        if x_feature not in test_results.columns or y_feature not in test_results.columns:
            raise ValueError(f"Features {x_feature} or {y_feature} not found in test results")
            
        if 'anomaly' not in test_results.columns:
            raise ValueError("Anomaly predictions not found in test results")
            
        # Create plot
        plt.figure(figsize=(10, 8))
        sns.scatterplot(
            data=test_results,
            x=x_feature,
            y=y_feature,
            hue='anomaly',
            palette={True: 'red', False: 'blue'},
            s=100
        )
        
        plt.title(f'Anomaly Detection: {x_feature} vs {y_feature}')
        plt.xlabel(x_feature)
        plt.ylabel(y_feature)
        plt.legend(title='Anomaly', labels=['Normal', 'Anomaly'])
        
        # Save if output path is provided
        if output_path:
            plt.savefig(output_path)
            plt.close()
            return output_path
        else:
            plt.show()
            plt.close()
            return None
        
    def _extract_features(self, test_results):
        """Extract numerical features from test results"""
        # Select only numerical columns
        numerical_cols = test_results.select_dtypes(include=[np.number]).columns
        return test_results[numerical_cols].fillna(0)
    
    def get_anomaly_report(self, test_results):
        """
        Generate a detailed report of detected anomalies
        
        Args:
            test_results: DataFrame with test results and anomaly predictions
            
        Returns:
            Dictionary with anomaly report
        """
        if 'anomaly' not in test_results.columns:
            raise ValueError("Anomaly predictions not found in test results")
            
        # Filter anomalies
        anomalies = test_results[test_results['anomaly']]
        
        # Calculate statistics
        total_tests = len(test_results)
        total_anomalies = len(anomalies)
        anomaly_rate = total_anomalies / total_tests if total_tests > 0 else 0
        
        # Get top anomalies by score
        top_anomalies = anomalies.sort_values('anomaly_score').head(5)
        
        # Create report
        report = {
            'total_tests': total_tests,
            'total_anomalies': total_anomalies,
            'anomaly_rate': anomaly_rate,
            'top_anomalies': top_anomalies.to_dict(orient='records'),
            'report_time': datetime.now().isoformat()
        }
        
        return report