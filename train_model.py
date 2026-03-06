"""
Standalone script to train and save the Random Forest model.
Run: python train_model.py
"""

import os
from ml_model import train_model

if __name__ == '__main__':
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'all_job_post.csv')
    metrics = train_model(csv_path, n_estimators=200, max_depth=None)
    print(f"\nTraining complete! Accuracy: {metrics['accuracy'] * 100:.2f}%")
