import os
import joblib
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, accuracy_score, f1_score
from sentence_transformers import SentenceTransformer

# ------------------ Paths ------------------ #
BASE_DIR = os.path.dirname(__file__)
CSV_PATH = os.path.join(BASE_DIR, "synthetic_income_dataset_v2.csv")
MODEL_PATH = os.path.join(BASE_DIR, "income_classifier_model.pkl")

# ------------------ Main Categories ------------------ #
INCOME_CATEGORIES = [
    "Salary", "Business", "Freelance", "Rental Income", "Dividends",
    "Interest Income", "Gifts & Donations", "Refunds",
    "Retirement Income", "Bonus & Incentives", "Other Income"
]
MISC_CATEGORY = "Other Income"

# ------------------ Preprocessing ------------------ #
def clean_text(text: str):
    return str(text).lower().strip()

def preprocess_texts(texts):
    return [clean_text(t) for t in texts]

# ------------------ Keyword mapping ------------------ #
KEYWORD_CATEGORY_MAP = {
    # Salary / Job-related
    "salary": "Salary",
    "paycheck": "Salary",
    "wages": "Salary",
    "employment": "Salary",
    "company": "Salary",
    "office": "Salary",
    "monthly pay": "Salary",

    # Business
    "business": "Business",
    "sales": "Business",
    "revenue": "Business",
    "store": "Business",
    "client payment": "Business",

    # Freelance
    "freelance": "Freelance",
    "project": "Freelance",
    "contract": "Freelance",
    "gig": "Freelance",

    # Rental Income
    "rent": "Rental Income",
    "tenant": "Rental Income",
    "lease": "Rental Income",

    # Dividends
    "dividend": "Dividends",
    "shares": "Dividends",
    "stocks": "Dividends",

    # Interest Income
    "interest": "Interest Income",
    "savings": "Interest Income",
    "bank interest": "Interest Income",
    "fixed deposit": "Interest Income",

    # Gifts & Donations
    "gift": "Gifts & Donations",
    "donation": "Gifts & Donations",
    "charity": "Gifts & Donations",
    "present": "Gifts & Donations",

    # Refunds
    "refund": "Refunds",
    "rebate": "Refunds",
    "cashback": "Refunds",

    # Retirement Income
    "pension": "Retirement Income",
    "retirement": "Retirement Income",
    "social security": "Retirement Income",

    # Bonus & Incentives
    "bonus": "Bonus & Incentives",
    "incentive": "Bonus & Incentives",
    "reward": "Bonus & Incentives",
    "performance": "Bonus & Incentives",
}

def keyword_category_mapping(text: str):
    text = text.lower()
    for keyword, category in KEYWORD_CATEGORY_MAP.items():
        if keyword in text:
            return category
    return None

# ------------------ Embedding ------------------ #
def encode_texts(embedder, texts, batch_size=64):
    embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        batch_emb = embedder.encode(batch, show_progress_bar=False)
        embeddings.append(batch_emb)
    return np.concatenate(embeddings, axis=0)

# ------------------ Model caching ------------------ #
_model_bundle = None

def load_classifier():
    global _model_bundle
    if _model_bundle is None:
        if os.path.exists(MODEL_PATH):
            _model_bundle = joblib.load(MODEL_PATH)
        else:
            _model_bundle = train_classifier(CSV_PATH)
    return _model_bundle

# ------------------ Training ------------------ #
def train_classifier(csv_path=CSV_PATH, save_model=True):
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)
    if "Source_Text" not in df.columns or "Category" not in df.columns:
        raise ValueError("CSV must contain 'Source_Text' and 'Category' columns.")

    df["Source_Text"] = preprocess_texts(df["Source_Text"])

    X_train_text, X_test_text, y_train, y_test = train_test_split(
        df["Source_Text"], df["Category"], test_size=0.2, stratify=df["Category"], random_state=42
    )

    embedder = SentenceTransformer('all-MiniLM-L6-v2')
    X_train_emb = encode_texts(embedder, X_train_text.tolist())
    X_test_emb = encode_texts(embedder, X_test_text.tolist())

    clf = LogisticRegression(max_iter=2000, class_weight="balanced", n_jobs=-1)
    clf.fit(X_train_emb, y_train)

    y_pred = clf.predict(X_test_emb)
    print("Accuracy:", accuracy_score(y_test, y_pred))
    print("Macro F1-score:", f1_score(y_test, y_pred, average="macro"))
    print(classification_report(y_test, y_pred, zero_division=0))

    X_emb_all = np.concatenate([X_train_emb, X_test_emb], axis=0)
    y_all = np.concatenate([y_train.values, y_test.values], axis=0)
    cv_scores = cross_val_score(clf, X_emb_all, y_all, cv=5, scoring="f1_macro", n_jobs=-1)
    print("Average CV Macro F1-score:", cv_scores.mean())

    if save_model:
        joblib.dump({"embedder": embedder, "classifier": clf}, MODEL_PATH)
        print(f"Model saved at {MODEL_PATH}")

    global _model_bundle
    _model_bundle = {"embedder": embedder, "classifier": clf}
    return _model_bundle

# ------------------ Prediction ------------------ #
def predict_category(texts, confidence_threshold=0.2):
    model_bundle = load_classifier()
    embedder = model_bundle["embedder"]
    clf = model_bundle["classifier"]

    clean_texts_list = preprocess_texts(texts)
    preds = []

    for t in clean_texts_list:
        # 1️⃣ Keyword mapping first (for obvious matches)
        mapped = keyword_category_mapping(t)
        if mapped:
            preds.append(mapped)
            continue

        # 2️⃣ Model prediction with confidence threshold
        emb = encode_texts(embedder, [t])
        probs = clf.predict_proba(emb)[0]
        max_prob = np.max(probs)
        pred = clf.classes_[np.argmax(probs)]

        # If model isn't confident, fallback to "Other Income"
        if max_prob < confidence_threshold:
            preds.append(MISC_CATEGORY)
        else:
            preds.append(pred if pred in INCOME_CATEGORIES else MISC_CATEGORY)

    return preds
