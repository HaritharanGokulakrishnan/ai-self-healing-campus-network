import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

FEATURES = [
    "packet_loss_pct",
    "avg_latency_ms",
    "max_latency_ms",
    "jitter_ms",
]

df = pd.read_csv("dataset.csv")
X = df[FEATURES]
y = df["label"]
groups = df["timestamp"]

splitter = GroupShuffleSplit(
    n_splits=1,
    test_size=0.30,
    random_state=42,
)
train_idx, test_idx = next(splitter.split(X, y, groups=groups))

X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)
pred = model.predict(X_test)

print("Timestamp-grouped evaluation")
print("Train rows:", len(train_idx))
print("Test rows:", len(test_idx))
print("Train timestamps:", groups.iloc[train_idx].nunique())
print("Test timestamps:", groups.iloc[test_idx].nunique())
print("\nTraining label counts:")
print(y_train.value_counts().to_string())
print("\nTest label counts:")
print(y_test.value_counts().to_string())
print("\nAccuracy:", round(accuracy_score(y_test, pred), 4))
print("\nClassification report:")
print(classification_report(y_test, pred, zero_division=0))
print("Confusion matrix (normal, link_failure, congestion):")
print(confusion_matrix(y_test, pred, labels=[
    "normal", "link_failure", "congestion"
]))
