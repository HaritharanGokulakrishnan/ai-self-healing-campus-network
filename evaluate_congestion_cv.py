import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedGroupKFold, cross_validate
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer

df = pd.read_csv("dataset.csv")
df = df[df["label"].isin(["normal", "congestion"])].copy()

features = ["avg_latency_ms", "max_latency_ms", "jitter_ms"]
X = df[features]
y = df["label"]
groups = df["timestamp"]

cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)

model = make_pipeline(
    SimpleImputer(strategy="median"),
    RandomForestClassifier(n_estimators=100, random_state=42),
)

scores = cross_validate(
    model,
    X,
    y,
    groups=groups,
    cv=cv,
    scoring=["accuracy", "precision_macro", "recall_macro", "f1_macro"],
)

for metric in ["accuracy", "precision_macro", "recall_macro", "f1_macro"]:
    values = scores["test_" + metric]
    print(f"{metric}: mean={values.mean():.4f}, std={values.std():.4f}, folds={values.round(4)}")
