"""
Train a multinomial logistic regression to classify stress (low/medium/high)
from session transcripts and the `csi_score` stored in the backend DB.

Usage:
  python tools/train_stress_model.py

Requirements:
  pip install scikit-learn pandas joblib
"""
from __future__ import annotations

import json
import os
import sys
from typing import Tuple
from urllib.request import urlopen

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from scipy import sparse
from tools.feature_engineering import compute_text_features


def _json_or_empty(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _sessions_to_dataframe(rows: list[dict]) -> pd.DataFrame:
    data = []
    for r in rows:
        if r.get('csi_score') is None:
            continue
        data.append({
            'session_id': int(r.get('session_id') or r.get('id')),
            'user_id': int(r.get('user_id') or 0),
            'session_number': int(r.get('session_number') or 0),
            'transcript': r.get('transcript') or '',
            'csi_score': int(r.get('csi_score')),
            'acoustic_features': _json_or_empty(r.get('acoustic_features')),
            'temporal_features': _json_or_empty(r.get('temporal_features')),
            'linguistic_features': _json_or_empty(r.get('linguistic_features')),
        })
    return pd.DataFrame(data)


def load_sessions_from_api(api_url: str) -> pd.DataFrame:
    url = api_url.rstrip('/')
    if not url.endswith('/api/sessions'):
        url = f'{url}/api/sessions'

    with urlopen(url, timeout=30) as response:
        payload = json.loads(response.read().decode('utf-8'))

    sessions = payload.get('sessions', payload if isinstance(payload, list) else [])
    return _sessions_to_dataframe(sessions)


def load_sessions_from_db() -> pd.DataFrame:
    api_url = os.getenv('COGNIVARA_SESSIONS_API', '').strip()
    if api_url:
        return load_sessions_from_api(api_url)

    BACKEND_DIR = os.path.join(os.getcwd(), 'backend')
    if BACKEND_DIR not in sys.path:
        sys.path.insert(0, BACKEND_DIR)

    from database import SessionLocal
    from models.session import Session

    db = SessionLocal()
    try:
        rows = db.query(Session).filter(Session.transcript != None).filter(Session.csi_score != None).all()
    finally:
        db.close()

    data = [
        {
            'session_id': int(r.id),
            'user_id': int(r.user_id),
            'session_number': int(r.session_number),
            'transcript': r.transcript or '',
            'csi_score': int(r.csi_score) if r.csi_score is not None else None,
            'acoustic_features': r.acoustic_features or {},
            'temporal_features': r.temporal_features or {},
            'linguistic_features': r.linguistic_features or {},
        }
        for r in rows
    ]
    return _sessions_to_dataframe(data)


def map_scores_to_labels(scores: np.ndarray) -> Tuple[np.ndarray, dict]:
    # Use 33/66 percentiles to create roughly balanced low/medium/high bins
    q1, q2 = np.percentile(scores, [33.3333, 66.6666])

    def f(x):
        if x <= q1:
            return 'low'
        if x <= q2:
            return 'medium'
        return 'high'

    labels = np.array([f(x) for x in scores])
    bins = {'q1': float(q1), 'q2': float(q2)}
    return labels, bins


def build_and_train(df: pd.DataFrame, out_dir: str = 'tools') -> None:
    os.makedirs(out_dir, exist_ok=True)

    texts = df['transcript'].astype(str).tolist()
    scores = df['csi_score'].astype(int).to_numpy()

    y, bins = map_scores_to_labels(scores)

    vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
    X_text = vectorizer.fit_transform(texts)

    # Build numeric feature matrix from stored JSON features (acoustic/temporal/linguistic)
    numeric_feature_names = [
        'mfcc_variance_avg',
        'pitch_mean',
        'pitch_var',
        'pitch_range',
        'voiced_fraction',
        'jitter_local',
        'shimmer_local',
        'spectral_centroid_mean',
        'spectral_centroid_var',
        'energy_mean',
        'energy_var',
        'duration_sec',
        'speech_rate',
        'response_latency',
        'rhythm_consistency',
        'pause_variability',
        'speed_variability',
        'mean_pause_duration',
        'max_pause_duration',
        'pause_count',
        'speech_ratio',
        'speech_duration_sec',
        'speech_segment_count',
        'sentence_length_mean',
        'lexical_diversity',
        'avg_word_length',
        'filler_ratio',
        'content_word_ratio',
        'syntactic_complexity',
        'vocabulary_richness',
        # engineered text features
        'sentiment_compound',
        'negative_ratio',
        'stress_keyword_count',
    ]

    numeric_rows = []
    for idx, row in df.iterrows():
        a = row.get('acoustic_features') or {}
        t = row.get('temporal_features') or {}
        l = row.get('linguistic_features') or {}
        # engineered text features
        eng = compute_text_features(row.get('transcript') or '')
        vals = []
        for k in numeric_feature_names:
            v = None
            # prefer acoustic-derived keys first
            if k in a:
                v = a.get(k)
            elif k in t:
                v = t.get(k)
            elif k in l:
                v = l.get(k)
            elif k in eng:
                v = eng.get(k)
            try:
                vals.append(float(v) if v is not None else 0.0)
            except Exception:
                vals.append(0.0)
        numeric_rows.append(vals)

    X_num = np.array(numeric_rows, dtype=float)
    # standardize numeric columns
    if X_num.size == 0:
        X_num_scaled = X_num
    else:
        scaler = StandardScaler()
        X_num_scaled = scaler.fit_transform(X_num)

    # combine sparse TF-IDF with dense numeric features
    if X_num_scaled.size == 0:
        X = X_text
    else:
        X_num_sparse = sparse.csr_matrix(X_num_scaled)
        X = sparse.hstack([X_text, X_num_sparse], format='csr')

    # Use stratified split where possible
    stratify = y if len(set(y)) > 1 else None
    if stratify is not None:
        # ensure each class has at least 2 samples for stratify
        counts = pd.Series(y).value_counts()
        if counts.min() < 2:
            stratify = None

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=stratify)

    # Create classifier with broad compatibility across sklearn versions
    try:
        clf = LogisticRegression(max_iter=2000, multi_class='multinomial', solver='saga')
    except TypeError:
        clf = LogisticRegression(max_iter=2000, solver='lbfgs')
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)

    report = classification_report(y_test, y_pred, digits=4)
    cm = confusion_matrix(y_test, y_pred, labels=['low', 'medium', 'high'])

    print('=== Classification Report ===')
    print(report)
    print('=== Confusion Matrix (rows=true, cols=pred) ===')
    print(cm)

    # Persist artifacts
    joblib.dump(clf, os.path.join(out_dir, 'stress_model.joblib'))
    joblib.dump(vectorizer, os.path.join(out_dir, 'tfidf_vectorizer.joblib'))
    with open(os.path.join(out_dir, 'label_bins.json'), 'w', encoding='utf-8') as f:
        json.dump(bins, f, ensure_ascii=False, indent=2)

    # Save dataset used for training
    df2 = df.copy()
    df2['label'] = y
    df2.to_csv(os.path.join(out_dir, 'training_data_with_labels.csv'), index=False)

    print('\nSaved model and artifacts to:', os.path.abspath(out_dir))


def main():
    df = load_sessions_from_db()
    if df.empty:
        print('No sessions with transcripts and csi_score found in DB. Record sessions first.')
        return

    print(f'Found {len(df)} labelled sessions. Training classifier...')
    build_and_train(df)


if __name__ == '__main__':
    main()
