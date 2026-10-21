#!/usr/bin/env python3
"""
Phase 5: Train + evaluate the fault detector.
  - Isolation Forest (trained on NORMAL rows only)  -> anomaly detection
  - Random Forest classifier                        -> fault-type classification
    python3 train_model.py --input dataset.csv
"""
import argparse, joblib
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (classification_report, confusion_matrix,
                             precision_recall_fscore_support, accuracy_score)

FEATURES = ['packet_loss_pct', 'avg_latency_ms', 'max_latency_ms', 'jitter_ms']
LABELS = ['normal', 'link_failure', 'congestion']


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', default='dataset.csv')
    a = p.parse_args()

    df = pd.read_csv(a.input)
    X, y = df[FEATURES], df['label']
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, stratify=y, random_state=42)
    lines = ['Dataset rows: %d' % len(df), str(y.value_counts().to_string()), '']

    # --- Anomaly detection (Isolation Forest, normal-only training) ---
    iso = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
    iso.fit(Xtr[ytr == 'normal'])
    pred_anom = (iso.predict(Xte) == -1)
    true_anom = (yte != 'normal')
    pr, rc, f1, _ = precision_recall_fscore_support(true_anom, pred_anom, average='binary', zero_division=0)
    lines += ['== Isolation Forest (anomaly detection) ==',
              'Accuracy : %.3f' % accuracy_score(true_anom, pred_anom),
              'Precision: %.3f' % pr, 'Recall   : %.3f' % rc, 'F1       : %.3f' % f1, '']

    # --- Fault classification (Random Forest) ---
    rf = RandomForestClassifier(n_estimators=100, random_state=42)
    rf.fit(Xtr, ytr)
    pred = rf.predict(Xte)
    lines += ['== Random Forest (fault classification) ==',
              'Accuracy: %.3f' % accuracy_score(yte, pred),
              classification_report(yte, pred, labels=LABELS, zero_division=0)]

    cm = confusion_matrix(yte, pred, labels=LABELS)
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.imshow(cm, cmap='Blues')
    ax.set_xticks(range(3)); ax.set_xticklabels(LABELS, rotation=20)
    ax.set_yticks(range(3)); ax.set_yticklabels(LABELS)
    for i in range(3):
        for j in range(3):
            ax.text(j, i, cm[i, j], ha='center', va='center')
    ax.set_xlabel('Predicted'); ax.set_ylabel('Actual'); ax.set_title('Fault classification')
    fig.tight_layout(); fig.savefig('confusion_matrix.png', dpi=150)

    joblib.dump({'iso': iso, 'rf': rf, 'features': FEATURES}, 'model.pkl')
    text = '\n'.join(lines)
    open('results.txt', 'w').write(text)
    print(text)
    print('\nSaved: model.pkl, results.txt, confusion_matrix.png')


if __name__ == '__main__':
    main()
