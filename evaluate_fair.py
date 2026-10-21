#!/usr/bin/env python3
"""
Fairer evaluation of the fault detector (leave-one-scenario-out).
    python3 evaluate_fair.py --input dataset.csv
"""
import argparse

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from sklearn.model_selection import LeaveOneGroupOut, train_test_split

FEATURES = ['packet_loss_pct', 'avg_latency_ms', 'max_latency_ms', 'jitter_ms']
BUILDINGS = ['LIB', 'CS', 'ADMIN', 'HOSTEL']
PAIRS = ['lib-admin', 'cs-hos', 'lib-hos']
PAIRS_PER_SWEEP = 6          # 4 hosts -> 6 host pairs, written in this order


def add_groups(df, normal, per_fault):
    """Name the scenario each row came from, using the generator's fixed order."""
    names = []
    for sweep in np.arange(len(df)) // PAIRS_PER_SWEEP:
        if sweep < normal:
            names.append('normal_%d' % (sweep // per_fault))
        else:
            k = (sweep - normal) // per_fault
            names.append('link_failure_' + BUILDINGS[k] if k < 4 else 'congestion_' + PAIRS[k - 4])
    df['group'] = names


def iso_flags(Xtr, ytr, Xte):
    """Isolation Forest trained on normal rows only; True = flagged as anomaly."""
    iso = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
    iso.fit(Xtr[ytr == 'normal'])
    return iso.predict(Xte) == -1


def rf_predict(Xtr, ytr, Xte):
    return RandomForestClassifier(n_estimators=100, random_state=42).fit(Xtr, ytr).predict(Xte)


def binary_scores(y, flagged):
    truth = (y != 'normal')
    p, r, f1, _ = precision_recall_fscore_support(truth, flagged, average='binary', zero_division=0)
    return accuracy_score(truth, flagged), p, r, f1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', default='dataset.csv')
    ap.add_argument('--normal', type=int, default=40, help='normal sweeps used when generating')
    ap.add_argument('--per-fault', type=int, default=10, help='sweeps per fault scenario')
    ap.add_argument('--output', default='fair_results.txt')
    a = ap.parse_args()

    df = pd.read_csv(a.input)
    expected = PAIRS_PER_SWEEP * (a.normal + 7 * a.per_fault)
    if len(df) != expected:
        raise SystemExit('Expected %d rows for these settings, found %d. '
                         'Pass the same --normal/--per-fault used for generate_dataset.py.'
                         % (expected, len(df)))
    add_groups(df, a.normal, a.per_fault)
    X, y, groups = df[FEATURES], df['label'], df['group']

    # A) original random split (what Review 2 reported)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, stratify=y, random_state=42)
    rand_if = binary_scores(yte, iso_flags(Xtr, ytr, Xte))
    rand_rf = accuracy_score(yte, rf_predict(Xtr, ytr, Xte))

    # B) leave-one-scenario-out
    flagged = np.zeros(len(df), dtype=bool)
    pred = np.empty(len(df), dtype=object)
    for tr, te in LeaveOneGroupOut().split(X, y, groups):
        flagged[te] = iso_flags(X.iloc[tr], y.iloc[tr], X.iloc[te])
        pred[te] = rf_predict(X.iloc[tr], y.iloc[tr], X.iloc[te])
    loso_if = binary_scores(y, flagged)
    loso_rf = accuracy_score(y, pred)

    lines = ['Rows: %d, scenarios held out one at a time: %d' % (len(df), groups.nunique()), '',
             '%-34s %9s %9s %9s %9s' % ('Anomaly detection (Isolation Forest)', 'Accuracy', 'Precision', 'Recall', 'F1'),
             '%-34s %9.3f %9.3f %9.3f %9.3f' % ('Random split (Review 2)', *rand_if),
             '%-34s %9.3f %9.3f %9.3f %9.3f' % ('Leave-one-scenario-out', *loso_if), '',
             '%-34s %9s' % ('Fault classification (Random Forest)', 'Accuracy'),
             '%-34s %9.3f' % ('Random split (Review 2)', rand_rf),
             '%-34s %9.3f' % ('Leave-one-scenario-out', loso_rf), '',
             'Per held-out fault scenario (fault rows only):',
             '%-28s %6s %12s %12s' % ('Scenario', 'Rows', 'IF detected', 'RF correct')]
    for g in sorted(groups.unique()):
        if g.startswith('normal'):
            continue
        m = ((groups == g) & (y != 'normal')).to_numpy()
        lines.append('%-28s %6d %11.0f%% %11.0f%%' % (g, m.sum(), 100 * flagged[m].mean(),
                                                    100 * (pred[m] == y[m].to_numpy()).mean()))
    text = '\n'.join(lines)
    print(text)
    open(a.output, 'w').write(text + '\n')
    print('\nSaved:', a.output)


if __name__ == '__main__':
    main()
