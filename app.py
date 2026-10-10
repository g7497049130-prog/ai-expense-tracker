import json
import time
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st
from google import genai

client = genai.Client()
FILE = Path("expenses.csv")

def load():
    if FILE.exists():
        return pd.read_csv(FILE)
    return pd.DataFrame(columns=["date", "amount", "category", "note"])

st.title("💸 AI Expense Tracker")
text = st.text_input("What did you spend on?", placeholder="e.g. 250 on pizza with friends")

if st.button("Add") and text.strip():
    prompt = (
        "Extract the expense from the text below. Reply with ONLY JSON like "
        '{"amount": 250, "category": "Food", "note": "pizza with friends"}. '
        "Categories: Food, Travel, Study, Entertainment, Shopping, Other.\n\n"
        "Text: " + text
    )

    reply = None
    for attempt in range(3):
        try:
            reply = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt,
                config={"response_mime_type": "application/json"},
            )
            break
        except Exception:
            time.sleep(2)

    if reply is None:
        st.error("Server busy hai, thodi der baad try karo.")
        st.stop()

    try:
        data = json.loads(reply.text)
        df = load()
        df.loc[len(df)] = [str(date.today()), data["amount"], data["category"], data["note"]]
        df.to_csv(FILE, index=False)
        st.success(f"Added: ₹{data['amount']} on {data['category']}")
    except (json.JSONDecodeError, KeyError):
        st.error("Couldn't understand that. Try rephrasing.")

df = load()
if not df.empty:
    st.metric("Total spent", f"₹{df['amount'].sum():,.0f}")
    st.bar_chart(df.groupby("category")["amount"].sum())
    st.dataframe(df)