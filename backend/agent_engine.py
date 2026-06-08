"""
agent_engine.py — SpendWise AI Agentic Copilot

This is the BRAIN of the system. It does NOT do ML or vector search itself.
It ORCHESTRATES the other engines:
  1. Receives a user query + transaction context.
  2. Decides if it needs RAG context (credit card policy lookup).
  3. Packages everything into a strict system prompt.
  4. Sends it to the local Ollama API (gemma:2b) and returns the response.

Think of it as a dispatcher that knows WHAT to ask and HOW to frame it,
while the LLM does the actual natural language reasoning.
"""

import requests
import json

# Import our existing engines
from rag_engine import query_policies

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
OLLAMA_BASE_URL = "http://localhost:11434"
MODEL_NAME = "gemma4:e2b"

# ---------------------------------------------------------------------------
# System Prompt — This is the personality and rules of our financial copilot.
# The LLM sees this EVERY time. It constrains hallucination and keeps
# responses grounded in the data we provide.
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are SpendWise AI, a direct, highly-trained local financial intelligence copilot.

You MUST respond ONLY in a valid raw JSON object matching the JSON schema.

JSON SCHEMA SCHEMA:
{
  "response_text": "your direct analysis or reply here",
  "is_dispute_request": false, // true if user requested to write/draft a letter, otherwise false
  "dispute_letter": "" // draft of the letter here if is_dispute_request is true, otherwise empty string
}

EXAMPLE RESPONSE 1 (General Query):
{
  "response_text": "I analyzed your statement. You have 2 anomalous transactions: a Starbucks charge of $450.00 and an Amazon charge of $2899.99. Both are much higher than your normal spending patterns.",
  "is_dispute_request": false,
  "dispute_letter": ""
}

EXAMPLE RESPONSE 2 (Dispute Letter Request):
{
  "response_text": "Here is the formal dispute letter drafted for the unauthorized Starbucks charge of $450.00 on 2026-05-02. Under your card policy, this charge is eligible for dispute because it is within the 60-day reporting window.",
  "is_dispute_request": true,
  "dispute_letter": "Date: June 9, 2026\\n\\nTo: Billing Dispute Department\\n\\nI am writing to formally dispute an unauthorized charge on my account: Starbucks Coffee in the amount of $450.00 on 2026-05-02. According to my cardholder agreement terms, I am not liable for unauthorized transactions reported within 60 days of the statement date. Please credit my account."
}

CRITICAL RULES:
1. Do NOT copy the example texts or instructions literally. Create custom values based on the user's specific query and actual transaction data.
2. Grounding: ONLY use transaction details and policy agreement rules present in the provided CONTEXT. Never invent facts.
3. No Conversational Fluff: Avoid introductory chat filler like "Certainly, here is the information".
4. Output ONLY the raw JSON. Do not wrap in ```json or ``` tags.
"""


def check_ollama_connection():
    """
    Pings the Ollama server to verify it's alive.
    Returns True if reachable, False otherwise.
    """
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            print(f"Ollama is running. Available models: {model_names}")
            # Check if our target model is available
            has_gemma = any(MODEL_NAME in name for name in model_names)
            if not has_gemma:
                print(f"WARNING: '{MODEL_NAME}' not found in available models!")
                print(f"Run: ollama pull {MODEL_NAME}")
            return True
        return False
    except requests.ConnectionError:
        print("ERROR: Cannot reach Ollama at", OLLAMA_BASE_URL)
        print("Make sure Ollama is running (it usually auto-starts).")
        return False


def build_context_prompt(user_query, anomaly_data=None, rag_results=None):
    """
    Constructs the full context block that gets injected into the prompt.

    This is where the magic happens. Instead of letting the LLM guess,
    we FEED it the exact data it needs to reason about:
      - Transaction anomalies from ML Engine
      - Credit card policy excerpts from RAG Engine
    """
    context_parts = []

    # --- Inject ML anomaly data if available ---
    if anomaly_data and len(anomaly_data) > 0:
        context_parts.append("## FLAGGED ANOMALOUS TRANSACTIONS (from ML Engine)")
        context_parts.append("These transactions were flagged by our Isolation Forest anomaly detector:")
        context_parts.append("")
        for i, txn in enumerate(anomaly_data):
            context_parts.append(
                f"  {i+1}. Date: {txn.get('date', 'N/A')} | "
                f"Description: {txn.get('description', 'N/A')} | "
                f"Amount: ${txn.get('amount', 0):.2f} | "
                f"Category: {txn.get('predicted_category', txn.get('category', 'N/A'))} | "
                f"Anomaly Score: {txn.get('anomaly_score', 'N/A')}"
            )
        context_parts.append("")

    # --- Inject RAG policy context if available ---
    if rag_results and len(rag_results) > 0:
        context_parts.append("## RELEVANT CREDIT CARD POLICY EXCERPTS (from Vector DB)")
        context_parts.append("These are the most semantically relevant sections from the user's card agreement:")
        context_parts.append("")
        for i, match in enumerate(rag_results):
            context_parts.append(f"  Policy Excerpt {i+1} (Section: {match['metadata'].get('section', 'General')}):")
            context_parts.append(f"  \"{match['text']}\"")
            context_parts.append("")

    if not context_parts:
        context_parts.append("No specific transaction or policy context available for this query.")

    return "\n".join(context_parts)


def query_agent(user_query, anomaly_data=None, chat_history=None):
    """
    The main entry point. Takes a user question, optionally with anomaly data,
    retrieves relevant policies from RAG, builds the prompt, and calls Ollama.

    Parameters:
        user_query (str): The user's question.
        anomaly_data (list[dict]): List of anomalous transactions from ml_engine.
        chat_history (list[dict]): Previous messages [{"role": "user"/"assistant", "content": "..."}]

    Returns:
        str: The LLM's response text.
    """

    # Step 1: Retrieve relevant credit card policies via RAG
    print(f"[Agent] Searching policies for: '{user_query}'")
    rag_results = query_policies(user_query, n_results=3)
    print(f"[Agent] Found {len(rag_results)} relevant policy excerpts.")

    # Step 2: Build the data context
    data_context = build_context_prompt(user_query, anomaly_data, rag_results)

    # Step 3: Construct the messages array for Ollama chat API.
    # We combine system prompt and context data into a single system message
    # to avoid context dilution and instruction-following failure in small 2B models.
    messages = [
        {
            "role": "system",
            "content": f"{SYSTEM_PROMPT}\n\nCONTEXT DATA FOR THIS QUERY:\n{data_context}"
        }
    ]

    # Inject chat history if available (for multi-turn conversation)
    if chat_history:
        for msg in chat_history:
            messages.append({"role": msg["role"], "content": msg["content"]})

    # Add the current user query
    messages.append({"role": "user", "content": user_query})

    # Step 4: Call Ollama Chat API
    print(f"[Agent] Sending to Ollama ({MODEL_NAME})...")
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": MODEL_NAME,
                "messages": messages,
                "stream": False,  # We get the full response at once for simplicity
                "format": "json",  # Force Ollama to output valid JSON
                "options": {
                    "temperature": 0.3,  # Low temp = more factual, less creative
                    "num_predict": 1024,  # Max tokens in response
                }
            },
            timeout=120  # 2 minute timeout for slow machines
        )
        resp.raise_for_status()

        result = resp.json()
        assistant_reply = result.get("message", {}).get("content", "")

        if not assistant_reply:
            return "I received an empty response from the model. Please try again."

        return assistant_reply

    except requests.ConnectionError:
        return (
            "ERROR: Cannot connect to Ollama. "
            "Make sure it's running: check your system tray or run 'ollama serve'."
        )
    except requests.Timeout:
        return (
            "ERROR: Ollama took too long to respond. "
            "Gemma 2B should respond within 2 minutes on most laptops. "
            "Check if another process is hogging your CPU/RAM."
        )
    except Exception as e:
        return f"ERROR: Unexpected error calling Ollama: {str(e)}"


def query_agent_stream(user_query, anomaly_data=None, chat_history=None):
    """
    Same as query_agent, but streams the response from Ollama chunk by chunk (generator).
    """
    print(f"[Agent] Searching policies for stream: '{user_query}'")
    rag_results = query_policies(user_query, n_results=3)
    data_context = build_context_prompt(user_query, anomaly_data, rag_results)

    # Construct the messages array
    messages = [
        {
            "role": "system",
            "content": f"{SYSTEM_PROMPT}\n\nCONTEXT DATA FOR THIS QUERY:\n{data_context}"
        }
    ]

    # Inject chat history if available
    if chat_history:
        for msg in chat_history:
            messages.append({"role": msg["role"], "content": msg["content"]})

    # Add the current user query
    messages.append({"role": "user", "content": user_query})

    print(f"[Agent] Streaming from Ollama ({MODEL_NAME})...")
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": MODEL_NAME,
                "messages": messages,
                "stream": True,  # Enable streaming inside Ollama
                "format": "json",  # Force Ollama to output valid JSON
                "options": {
                    "temperature": 0.3,
                    "num_predict": 1024,
                }
            },
            stream=True,
            timeout=120
        )
        resp.raise_for_status()

        for line in resp.iter_lines():
            if line:
                chunk = json.loads(line.decode('utf-8'))
                content = chunk.get("message", {}).get("content", "")
                if content:
                    yield content

    except requests.ConnectionError:
        yield "ERROR: Cannot connect to Ollama. Make sure it is running."
    except requests.Timeout:
        yield "ERROR: Ollama took too long to respond."
    except Exception as e:
        yield f"ERROR: Unexpected error calling Ollama stream: {str(e)}"


# ---------------------------------------------------------------------------
# Stand-alone test — Run this file directly to verify the full pipeline works
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("  SpendWise AI — Agent Engine Test")
    print("=" * 60)

    # 1. Check Ollama connection
    print("\n[1] Checking Ollama connection...")
    if not check_ollama_connection():
        print("\nFATAL: Ollama is not reachable. Exiting.")
        exit(1)

    # 2. Simulate some anomalous transactions (as if ml_engine flagged them)
    mock_anomalies = [
        {
            "date": "2024-03-15",
            "description": "CRYPTO EXCHANGE WIRE TRANSFER",
            "amount": 4999.99,
            "predicted_category": "Investment",
            "anomaly_score": -0.42
        },
        {
            "date": "2024-03-16",
            "description": "LUXURY WATCHES INTL",
            "amount": 2899.00,
            "predicted_category": "Shopping",
            "anomaly_score": -0.38
        },
    ]

    # 3. Test Query 1: Ask about anomalies
    print("\n[2] Test Query: Anomaly Analysis")
    print("-" * 40)
    query1 = "I see some suspicious charges on my statement. Can you explain these anomalies and tell me if I can dispute them?"
    response1 = query_agent(query1, anomaly_data=mock_anomalies)
    print(f"\nUser: {query1}")
    print(f"\nSpendWise AI:\n{response1}")

    # 4. Test Query 2: Ask a policy question (pure RAG)
    print("\n\n[3] Test Query: Policy Question")
    print("-" * 40)
    query2 = "What is the penalty APR if I miss a payment?"
    response2 = query_agent(query2)
    print(f"\nUser: {query2}")
    print(f"\nSpendWise AI:\n{response2}")

    # 5. Test Query 3: Ask it to draft a dispute letter
    print("\n\n[4] Test Query: Dispute Letter Draft")
    print("-" * 40)
    query3 = "Draft a formal dispute letter for the CRYPTO EXCHANGE WIRE TRANSFER charge of $4999.99 on March 15. I did not authorize this."
    response3 = query_agent(query3, anomaly_data=mock_anomalies)
    print(f"\nUser: {query3}")
    print(f"\nSpendWise AI:\n{response3}")

    print("\n" + "=" * 60)
    print("  Agent Engine Test Complete!")
    print("=" * 60)
