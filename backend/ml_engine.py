import os
import joblib
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import IsolationForest
from sklearn.metrics import classification_report, confusion_matrix

# Paths
DATA_DIR = "c:/Users/jatin/ragprojects/project_1/backend/data"
MODELS_DIR = "c:/Users/jatin/ragprojects/project_1/backend/models"

def train_category_classifier(df):
    print("--- Training Category Classifier (Supervised) ---")
    
    # 1. Feature Extraction: Convert merchant text description using TF-IDF
    # We use character and word n-grams to handle typos and text fragments nicely
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), analyzer="char_wb")
    X = vectorizer.fit_transform(df["description"])
    y = df["category"]
    
    # Train/Test Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # We use Logistic Regression (highly stable, fast, and multi-class friendly)
    classifier = LogisticRegression(max_iter=1000, random_state=42)
    classifier.fit(X_train, y_train)
    
    # Evaluation
    y_pred = classifier.predict(X_test)
    print("\nModel Evaluation Metrics:")
    print(classification_report(y_test, y_pred))
    
    # Save model and vectorizer
    joblib.dump(classifier, os.path.join(MODELS_DIR, "category_classifier.joblib"))
    joblib.dump(vectorizer, os.path.join(MODELS_DIR, "tfidf_vectorizer.joblib"))
    print("Category Classifier and Vectorizer successfully saved to disk.")
    
    return classifier, vectorizer

def train_anomaly_detector(df):
    print("\n--- Training Anomaly Detector (Unsupervised Isolation Forest) ---")
    
    # We train the unsupervised anomaly detector on completely normal transaction patterns.
    # An Isolation Forest isolates observations by randomly selecting a feature and split value.
    # Outliers are isolated much faster (shorter path lengths in the trees).
    
    # We extract numerical features: "amount" is the main one.
    # Since different categories have vastly different typical amount ranges (e.g. food vs utilities),
    # we should scale/normalize the amount relative to its category, OR train a global model.
    # To demonstrate high-fidelity engineering, we will fit an IsolationForest on the global transaction amounts,
    # but in inference we can also look at category deviations. Let's start with a global Isolation Forest
    # tuned with a contamination rate (expected ratio of anomalies, set very low in training).
    
    X = df[["amount"]].values
    
    # We set contamination to 0.01 (1%) because our training set is mostly clean.
    anomaly_detector = IsolationForest(contamination=0.01, random_state=42)
    anomaly_detector.fit(X)
    
    # Save the anomaly detector
    joblib.dump(anomaly_detector, os.path.join(MODELS_DIR, "anomaly_detector.joblib"))
    print("Anomaly Detector successfully saved to disk.")
    
    return anomaly_detector

def run_inference_on_test():
    print("\n--- Running Inference on Test Dataset (Simulating Upload) ---")
    
    # Load serialized models
    classifier = joblib.load(os.path.join(MODELS_DIR, "category_classifier.joblib"))
    vectorizer = joblib.load(os.path.join(MODELS_DIR, "tfidf_vectorizer.joblib"))
    anomaly_detector = joblib.load(os.path.join(MODELS_DIR, "anomaly_detector.joblib"))
    
    # Load test statement (with target anomalies)
    test_csv = os.path.join(DATA_DIR, "transactions_test.csv")
    if not os.path.exists(test_csv):
        print(f"Error: {test_csv} not found. Please run the data generator first!")
        return
        
    test_df = pd.read_csv(test_csv)
    
    # 1. Categorization Inference
    X_test_text = vectorizer.transform(test_df["description"])
    test_df["predicted_category"] = classifier.predict(X_test_text)
    
    # 2. Anomaly Detection Inference
    # IsolationForest predict returns: 1 for normal, -1 for anomaly
    X_test_amounts = test_df[["amount"]].values
    predictions = anomaly_detector.predict(X_test_amounts)
    anomaly_scores = anomaly_detector.decision_function(X_test_amounts)
    
    test_df["is_anomaly"] = predictions == -1
    test_df["anomaly_score"] = anomaly_scores
    
    # Let's inspect the labeled anomalies in our output
    print("\nFlagged Anomalies:")
    flagged = test_df[test_df["is_anomaly"]]
    print(flagged[["date", "description", "amount", "predicted_category", "anomaly_score"]])
    
    # Let's check accuracy of the text classification on the test set
    accuracy = (test_df["category"] == test_df["predicted_category"]).mean()
    print(f"\nCategorization accuracy on test set: {accuracy * 100:.2f}%")
    
    # Save the processed test results to show what the API will send
    test_df.to_csv(os.path.join(DATA_DIR, "transactions_processed_results.csv"), index=False)
    print("\nProcessed test results saved to data/transactions_processed_results.csv")

if __name__ == "__main__":
    train_csv = os.path.join(DATA_DIR, "transactions_train.csv")
    if not os.path.exists(train_csv):
        print("Training data not found. Please generate the data first!")
    else:
        df_train = pd.read_csv(train_csv)
        train_category_classifier(df_train)
        train_anomaly_detector(df_train)
        run_inference_on_test()
