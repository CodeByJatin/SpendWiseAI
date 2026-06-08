from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import joblib
import os
import io

from agent_engine import query_agent, query_agent_stream

app = FastAPI(title="SpendWise AI API")

# Enable CORS so our React frontend can talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")

# Global state to keep things simple for this local app
MODELS = {}
CURRENT_ANOMALIES = []
PROCESSED_TRANSACTIONS = []

@app.on_event("startup")
def load_models():
    """Load our Scikit-Learn models into memory when the server starts."""
    try:
        MODELS["classifier"] = joblib.load(os.path.join(MODELS_DIR, "category_classifier.joblib"))
        MODELS["vectorizer"] = joblib.load(os.path.join(MODELS_DIR, "tfidf_vectorizer.joblib"))
        MODELS["anomaly_detector"] = joblib.load(os.path.join(MODELS_DIR, "anomaly_detector.joblib"))
        print("✅ ML Models loaded successfully.")
    except Exception as e:
        print(f"⚠️ Warning: Could not load models. Did you run ml_engine.py? Error: {e}")

@app.post("/api/upload")
async def upload_transactions(file: UploadFile = File(...)):
    """Accepts a CSV file, runs categorization and anomaly detection on it."""
    global CURRENT_ANOMALIES, PROCESSED_TRANSACTIONS
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")
        
    content = await file.read()
    try:
        df = pd.read_csv(io.StringIO(content.decode('utf-8')))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading CSV: {e}")
        
    if not all(col in df.columns for col in ["date", "description", "amount"]):
        raise HTTPException(status_code=400, detail="CSV must contain 'date', 'description', and 'amount' columns.")
        
    # 1. Run Classification Inference
    if "classifier" in MODELS and "vectorizer" in MODELS:
        X_text = MODELS["vectorizer"].transform(df["description"])
        df["predicted_category"] = MODELS["classifier"].predict(X_text)
    else:
        df["predicted_category"] = "Unknown"
        
    # 2. Run Anomaly Detection Inference
    if "anomaly_detector" in MODELS:
        X_amounts = df[["amount"]].values
        predictions = MODELS["anomaly_detector"].predict(X_amounts)
        anomaly_scores = MODELS["anomaly_detector"].decision_function(X_amounts)
        
        df["is_anomaly"] = predictions == -1
        # Convert float32 scores to float for JSON serialization
        df["anomaly_score"] = [float(score) for score in anomaly_scores] 
    else:
        df["is_anomaly"] = False
        df["anomaly_score"] = 0.0
        
    # Save to global state
    records = df.to_dict(orient="records")
    PROCESSED_TRANSACTIONS = records
    CURRENT_ANOMALIES = [r for r in records if r.get("is_anomaly")]
    
    return {
        "message": "File processed successfully", 
        "total_transactions": len(records), 
        "anomalies_found": len(CURRENT_ANOMALIES)
    }

@app.get("/api/transactions")
def get_transactions():
    """Returns the most recently processed transactions and anomalies."""
    return {
        "transactions": PROCESSED_TRANSACTIONS,
        "anomalies": CURRENT_ANOMALIES
    }

class ChatRequest(BaseModel):
    message: str
    history: list = []

@app.post("/api/chat")
def chat_with_agent(req: ChatRequest):
    """Passes the user's message, chat history, and anomaly context to the local Ollama LLM and streams response."""
    try:
        generator = query_agent_stream(
            user_query=req.message,
            anomaly_data=CURRENT_ANOMALIES,
            chat_history=req.history
        )
        return StreamingResponse(generator, media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
