import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, classification_report

FEATURES = [
    "packet_loss_pct",
    "avg_latency_ms",
    "max_latency_ms",
    "jitter_ms",
]
LATENCY_FEATURES = [
    "avg_latency_ms",
    "max_latency_ms",
    "jitter_ms",
]

df = pd.read_csv("dataset.csv")
X = df[FEATURES].copy()
y = df["label"]
groups = df["timestamp"]

# Convert the artificial missing-measurement sentinel to NaN.
X[LATENCY_FEATURES] = X[LATENCY_FEATURES].replace(1000.0, float("nan"))

splitter = GroupShuffleSplit(
    n_splits=1,
    test_size=0.30,
    random_state=42,
)
train_idx, test_idx = next(splitter.split(X, y, groups=groups))

model = make_pipeline(
    SimpleImputer(strategy="median"),
    RandomForestClassifier(n_estimators=100, random_state=42),
)

model.fit(X.iloc[train_idx], y.iloc[train_idx])
pred = model.predict(X.iloc[test_idx])

print("SENTINEL-REMOVED, MEDIAN-IMPUTED EVALUATION")
print("Train rows:", len(train_idx))
print("Test rows:", len(test_idx))
print("Accuracy:", round(accuracy_score(y.iloc[test_idx], pred), 4))
print("\nClassification report:")
print(classification_report(
    y.iloc[test_idx],
    pred,
    labels=["normal", "link_failure", "congestion"],
    zero_division=0,
))
