import os
import cv2
import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity as ssim

class VisualComparator:
    def __init__(self, threshold=0.95):
        self.threshold = threshold
        
    def compare_images(self, baseline_path, current_path):
        """
        Compare two images and return the similarity score and diff image
        
        Args:
            baseline_path: Path to the baseline image
            current_path: Path to the current image
            
        Returns:
            tuple: (similarity_score, diff_image_path)
        """
        # Load images
        baseline_img = cv2.imread(baseline_path)
        current_img = cv2.imread(current_path)
        
        # Check if images were loaded successfully
        if baseline_img is None or current_img is None:
            raise ValueError("Failed to load one or both images")
            
        # Resize images to match dimensions if needed
        if baseline_img.shape != current_img.shape:
            current_img = cv2.resize(current_img, (baseline_img.shape[1], baseline_img.shape[0]))
            
        # Convert images to grayscale
        baseline_gray = cv2.cvtColor(baseline_img, cv2.COLOR_BGR2GRAY)
        current_gray = cv2.cvtColor(current_img, cv2.COLOR_BGR2GRAY)
        
        # Calculate SSIM
        score, diff = ssim(baseline_gray, current_gray, full=True)
        
        # Generate diff image
        diff = (diff * 255).astype("uint8")
        thresh = cv2.threshold(diff, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
        
        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Draw contours on original image
        diff_img = current_img.copy()
        cv2.drawContours(diff_img, contours, -1, (0, 0, 255), 2)
        
        # Save diff image
        diff_path = os.path.splitext(current_path)[0] + "_diff.png"
        cv2.imwrite(diff_path, diff_img)
        
        return score, diff_path
        
    def is_match(self, baseline_path, current_path):
        """Check if two images match based on the threshold"""
        score, _ = self.compare_images(baseline_path, current_path)
        return score >= self.threshold