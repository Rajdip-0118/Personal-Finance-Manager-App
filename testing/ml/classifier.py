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
CSV_PATH = os.path.join(BASE_DIR, "synthetic_expense_dataset_v2.csv")
MODEL_PATH = os.path.join(BASE_DIR, "expense_classifier_model.pkl")

# ------------------ Main Categories ------------------ #
MAIN_CATEGORIES = [
    "Food & Dining", "Transportation", "Housing & Utilities", "Personal & Shopping",
    "Health & Fitness", "Entertainment & Leisure", "Education", "Financial",
    "Travel & Vacation"
]
MISC_CATEGORY = "Miscellaneous"

# ------------------ Preprocessing (minimal) ------------------ #
def clean_text(text: str):
    return str(text).lower().strip()

def preprocess_texts(texts):
    return [clean_text(t) for t in texts]

# ------------------ Keyword mapping for very obvious cases ------------------ #
KEYWORD_CATEGORY_MAP = {
    # Food & Dining
    "food": "Food & Dining",
    "dining": "Food & Dining",
    "restaurant": "Food & Dining",
    "meal": "Food & Dining",
    "lunch": "Food & Dining",
    "breakfast": "Food & Dining",
    "dinner": "Food & Dining",
    
    # Transportation
    "transport": "Transportation",
    "taxi": "Transportation",
    "uber": "Transportation",
    "lyft": "Transportation",
    "bus": "Transportation",
    "train": "Transportation",
    
    # Housing & Utilities
    "rent": "Housing & Utilities",
    "electricity": "Housing & Utilities",
    "water": "Housing & Utilities",
    "gas": "Housing & Utilities",
    "utility": "Housing & Utilities",
    
    # Personal & Shopping
    "shopping": "Personal & Shopping",
    "clothes": "Personal & Shopping",
    "apparel": "Personal & Shopping",
    "retail": "Personal & Shopping",
    
    # Health & Fitness
    "gym": "Health & Fitness",
    "fitness": "Health & Fitness",
    "doctor": "Health & Fitness",
    "pharmacy": "Health & Fitness",
    "medicine": "Health & Fitness",
    
    # Entertainment & Leisure
    "movie": "Entertainment & Leisure",
    "concert": "Entertainment & Leisure",
    "game": "Entertainment & Leisure",
    "netflix": "Entertainment & Leisure",
    
    # Education
    "school": "Education",
    "college": "Education",
    "university": "Education",
    "course": "Education",
    
    # Financial
    "bank": "Financial",
    "insurance": "Financial",
    "loan": "Financial",
    
    # Travel & Vacation
    "hotel": "Travel & Vacation",
    "flight": "Travel & Vacation",
    "airline": "Travel & Vacation",
    "vacation": "Travel & Vacation",
    "trip": "Travel & Vacation",
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
    if "Merchant_Text" not in df.columns or "Category" not in df.columns:
        raise ValueError("CSV must contain 'Merchant_Text' and 'Category' columns.")

    df["Merchant_Text"] = preprocess_texts(df["Merchant_Text"])

    X_train_text, X_test_text, y_train, y_test = train_test_split(
        df["Merchant_Text"], df["Category"], test_size=0.2, stratify=df["Category"], random_state=42
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

def predict_category(texts, confidence_threshold=0.4):
    model_bundle = load_classifier()
    embedder = model_bundle["embedder"]
    clf = model_bundle["classifier"]

    clean_texts_list = preprocess_texts(texts)
    preds = []

    for t in clean_texts_list:
        # 1️⃣ Keyword mapping first
        mapped = keyword_category_mapping(t)
        if mapped:
            preds.append(mapped)
            continue

        # 2️⃣ Model prediction with confidence threshold
        emb = encode_texts(embedder, [t])
        probs = clf.predict_proba(emb)[0]
        max_prob = np.max(probs)
        pred = clf.classes_[np.argmax(probs)]

        if max_prob < confidence_threshold:
            preds.append(MISC_CATEGORY)
        else:
            preds.append(pred if pred in MAIN_CATEGORIES else MISC_CATEGORY)

    return preds