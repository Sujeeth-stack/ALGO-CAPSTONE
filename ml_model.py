"""
Machine Learning Pipeline for Job Skill Portal
Random Forest Classifier with TF-IDF vectorization
"""

import pandas as pd
import numpy as np
import re
import ast
import os
import joblib
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    accuracy_score, classification_report,
    confusion_matrix, f1_score, precision_score, recall_score
)

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')


def clean_skills(skill_str):
    """Parse and clean the skill set string."""
    if pd.isna(skill_str) or not skill_str:
        return ''
    try:
        skills = ast.literal_eval(skill_str)
        if isinstance(skills, list):
            cleaned = [s.strip().lower() for s in skills if isinstance(s, str)]
            return ', '.join(cleaned)
    except (ValueError, SyntaxError):
        pass
    # Fallback: treat as comma-separated string
    skill_str = re.sub(r"[\[\]']", '', str(skill_str))
    skills = [s.strip().lower() for s in skill_str.split(',') if s.strip()]
    return ', '.join(skills)


def load_and_preprocess(csv_path):
    """Load dataset and preprocess for training."""
    df = pd.read_csv(csv_path)

    # Clean columns
    df.columns = df.columns.str.strip().str.lower()

    # Drop rows with missing critical fields
    df = df.dropna(subset=['category', 'job_skill_set'])

    # Clean skill sets
    df['cleaned_skills'] = df['job_skill_set'].apply(clean_skills)

    # Remove empty skill rows
    df = df[df['cleaned_skills'].str.len() > 0]

    # Clean category
    df['category'] = df['category'].str.strip().str.upper()

    return df


def train_model(csv_path, n_estimators=200, max_depth=None, test_size=0.2, random_state=42):
    """Train Random Forest model and return metrics."""
    print("=" * 60)
    print("  JOB SKILL PORTAL — Random Forest Model Training")
    print("=" * 60)

    # Load and preprocess
    print("\n[1/5] Loading and preprocessing data...")
    df = load_and_preprocess(csv_path)
    print(f"  → Total samples: {len(df)}")
    print(f"  → Categories: {df['category'].nunique()}")
    print(f"  → Category distribution:")
    for cat, count in df['category'].value_counts().items():
        print(f"      {cat}: {count}")

    # TF-IDF Vectorization
    print("\n[2/5] TF-IDF Vectorizing skills...")
    tfidf = TfidfVectorizer(max_features=5000, ngram_range=(1, 2), stop_words='english')
    X = tfidf.fit_transform(df['cleaned_skills'])
    print(f"  → Feature matrix shape: {X.shape}")

    # Encode labels
    le = LabelEncoder()
    y = le.fit_transform(df['category'])
    print(f"  → Classes: {list(le.classes_)}")

    # Split data
    print("\n[3/5] Splitting data (train/test)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )
    print(f"  → Train size: {X_train.shape[0]}")
    print(f"  → Test size: {X_test.shape[0]}")

    # Train Random Forest
    print("\n[4/5] Training Random Forest Classifier...")
    print(f"  → n_estimators={n_estimators}, max_depth={max_depth}")
    rf = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        random_state=random_state,
        n_jobs=-1,
        class_weight='balanced'
    )
    rf.fit(X_train, y_train)

    # Evaluate
    print("\n[5/5] Evaluating model...")
    y_pred = rf.predict(X_test)

    accuracy = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, average='weighted')
    precision = precision_score(y_test, y_pred, average='weighted')
    recall = recall_score(y_test, y_pred, average='weighted')
    cm = confusion_matrix(y_test, y_pred)
    report = classification_report(y_test, y_pred, target_names=le.classes_, output_dict=True)

    print(f"\n{'=' * 60}")
    print(f"  RESULTS")
    print(f"{'=' * 60}")
    print(f"  Accuracy:  {accuracy:.4f} ({accuracy * 100:.2f}%)")
    print(f"  F1 Score:  {f1:.4f}")
    print(f"  Precision: {precision:.4f}")
    print(f"  Recall:    {recall:.4f}")
    print(f"\n  Classification Report:")
    print(classification_report(y_test, y_pred, target_names=le.classes_))

    # Save model artifacts
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(rf, os.path.join(MODEL_DIR, 'rf_model.pkl'))
    joblib.dump(tfidf, os.path.join(MODEL_DIR, 'tfidf_vectorizer.pkl'))
    joblib.dump(le, os.path.join(MODEL_DIR, 'label_encoder.pkl'))

    # Save metrics
    metrics = {
        'accuracy': float(accuracy),
        'f1_score': float(f1),
        'precision': float(precision),
        'recall': float(recall),
        'confusion_matrix': cm.tolist(),
        'classification_report': report,
        'categories': list(le.classes_),
        'train_size': int(X_train.shape[0]),
        'test_size': int(X_test.shape[0]),
        'total_features': int(X.shape[1]),
        'n_estimators': n_estimators,
        'total_samples': int(len(df))
    }
    joblib.dump(metrics, os.path.join(MODEL_DIR, 'metrics.pkl'))

    print(f"\n  Model saved to: {MODEL_DIR}")
    print(f"{'=' * 60}")

    return metrics


def load_model():
    """Load pre-trained model artifacts."""
    rf = joblib.load(os.path.join(MODEL_DIR, 'rf_model.pkl'))
    tfidf = joblib.load(os.path.join(MODEL_DIR, 'tfidf_vectorizer.pkl'))
    le = joblib.load(os.path.join(MODEL_DIR, 'label_encoder.pkl'))
    return rf, tfidf, le


def predict_category(skills_text, top_n=5):
    """Predict job category from a list of skills."""
    rf, tfidf, le = load_model()

    # Clean input
    if isinstance(skills_text, list):
        skills_text = ', '.join(skills_text)
    skills_text = skills_text.lower().strip()

    # Vectorize
    X = tfidf.transform([skills_text])

    # Get prediction probabilities
    proba = rf.predict_proba(X)[0]

    # Build results
    results = []
    for idx in np.argsort(proba)[::-1][:top_n]:
        results.append({
            'category': le.classes_[idx],
            'confidence': float(proba[idx]),
            'confidence_pct': f"{proba[idx] * 100:.1f}%"
        })

    return results


def get_metrics():
    """Load and return saved model metrics."""
    metrics_path = os.path.join(MODEL_DIR, 'metrics.pkl')
    if os.path.exists(metrics_path):
        return joblib.load(metrics_path)
    return None


def get_feature_importance(top_n=30):
    """Get top N most important features from the model."""
    rf, tfidf, le = load_model()
    feature_names = tfidf.get_feature_names_out()
    importances = rf.feature_importances_
    indices = np.argsort(importances)[::-1][:top_n]
    return [
        {'feature': feature_names[i], 'importance': float(importances[i])}
        for i in indices
    ]
