import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import accuracy_score, classification_report

df = pd.read_csv("dataset.csv")

# Exclude link-failure samples because their latency and jitter
# values are unavailable, not measured.
df = df[df["label"].isin(["normal", "congestion"])].copy()

FEATURES = ["avg_latency_ms", "max_latency_ms", "jitter_ms"]
X = df[FEATURES]
y = df["label"]
groups = df["timestamp"]

splitter = GroupShuffleSplit(
    n_splits=1,
    test_size=0.30,
    random_state=42,
)
train_idx, test_idx = next(splitter.split(X, y, groups=groups))

model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X.iloc[train_idx], y.iloc[train_idx])
pred = model.predict(X.iloc[test_idx])

print("NORMAL VS CONGESTION: LATENCY/JITTER ONLY")
print("Features:", FEATURES)
print("Train rows:", len(train_idx))
print("Test rows:", len(test_idx))
print("Accuracy:", round(accuracy_score(y.iloc[test_idx], pred), 4))
print("\nClassification report:")
print(classification_report(
    y.iloc[test_idx],
    pred,
    labels=["normal", "congestion"],
    zero_division=0,
))
