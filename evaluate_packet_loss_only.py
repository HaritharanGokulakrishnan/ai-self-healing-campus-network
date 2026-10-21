import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import accuracy_score, classification_report

df = pd.read_csv("dataset.csv")

X = df[["packet_loss_pct"]]
y = df["label"]
groups = df["timestamp"]

splitter = GroupShuffleSplit(
    n_splits=1,
    test_size=0.30,
    random_state=42
)

train_idx, test_idx = next(splitter.split(X, y, groups=groups))

model = RandomForestClassifier(
    n_estimators=100,
    random_state=42
)

model.fit(X.iloc[train_idx], y.iloc[train_idx])
pred = model.predict(X.iloc[test_idx])

print("PACKET-LOSS-ONLY EVALUATION")
print("Features:", list(X.columns))
print("Accuracy:", round(accuracy_score(y.iloc[test_idx], pred), 4))
print("\nClassification report:")
print(classification_report(
    y.iloc[test_idx],
    pred,
    labels=["normal", "link_failure", "congestion"],
    zero_division=0
))
