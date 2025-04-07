from .test_generation.generator import TestGenerator
from .visual_regression.comparator import VisualComparator
from .anomaly_detection.detector import AnomalyDetector
from .predictive_analytics.prioritizer import TestPrioritizer

class AITestingEngine:
    def __init__(self):
        self.test_generator = TestGenerator()
        self.visual_comparator = VisualComparator()
        self.anomaly_detector = AnomalyDetector()
        self.test_prioritizer = TestPrioritizer()
        
    def generate_tests(self, url, test_types=None):
        """Generate test cases from a URL"""
        return self.test_generator.generate_from_url(url, test_types)
        
    def generate_selenium_test(self, test_data):
        """Generate a Selenium test script from test data"""
        return self.test_generator.generate_selenium_test(test_data)
        
    def compare_screenshots(self, baseline_path, current_path):
        """Compare two screenshots and return the similarity score"""
        return self.visual_comparator.compare_images(baseline_path, current_path)
        
    def detect_test_anomalies(self, test_results):
        """Detect anomalies in test results"""
        return self.anomaly_detector.detect_anomalies(test_results)
        
    def prioritize_tests(self, tests, test_history=None):
        """Prioritize tests based on their likelihood of failing"""
        if test_history is not None and not self.test_prioritizer.is_fitted:
            self.test_prioritizer.fit(test_history)
            
        return self.test_prioritizer.prioritize(tests)