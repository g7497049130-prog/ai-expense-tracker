import json
import time
from datetime import date
from io import BytesIO
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from google import genai

client = genai.Client()
FILE = Path("expenses.csv")
MODEL = "gemini-3.8-flash"


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
                model=MODEL,
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
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df = df.dropna(subset=["date", "amount"])
    df["month"] = df["date"].dt.strftime("%Y-%m")

    st.metric("Total spent", f"₹{df['amount'].sum():,.0f}")

    months = sorted(df["month"].unique(), reverse=True)
    chosen = st.selectbox("Month chuno", months)
    month_df = df[df["month"] == chosen]

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Category-wise kharch")
        pie_data = month_df.groupby("category", as_index=False)["amount"].sum()
        st.plotly_chart(px.pie(pie_data, names="category", values="amount", hole=0.4),
                        use_container_width=True)
    with col2:
        st.subheader("Roz ka spending trend")
        daily = df.groupby("date", as_index=False)["amount"].sum()
        st.plotly_chart(px.line(daily, x="date", y="amount", markers=True),
                        use_container_width=True)

    st.subheader("Saari entries")
    st.dataframe(df.drop(columns=["month"]))

    export_df = df.drop(columns=["month"]).copy()
    export_df["date"] = export_df["date"].dt.strftime("%Y-%m-%d")

    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "📄 CSV download karo",
            data=export_df.to_csv(index=False).encode("utf-8"),
            file_name="expenses.csv",
            mime="text/csv",
        )
    with c2:
        buffer = BytesIO()
        export_df.to_excel(buffer, index=False, sheet_name="Expenses")
        st.download_button(
            "📊 Excel download karo",
            data=buffer.getvalue(),
            file_name="expenses.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    # ---------- AI Financial Advisor ----------
    st.divider()
    st.subheader("🤖 AI Financial Advisor")

    if "chat" not in st.session_state:
        st.session_state.chat = []

    for m in st.session_state.chat:
        with st.chat_message(m["role"]):
            st.write(m["content"])

    question = st.chat_input("Poochho: main kahan zyada kharch kar raha hoon?")
    if question:
        st.session_state.chat.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.write(question)

        history_csv = export_df.tail(100).to_csv(index=False)
        advisor_prompt = (
            "You are a friendly personal finance advisor for an Indian college student. "
            "Use ONLY the expense data below (amounts are in rupees). "
            "Reply in simple Hinglish, in under 150 words, with 2 to 3 practical tips. "
            "If the data is too little to judge, say so.\n\n"
            f"Expense data (CSV):\n{history_csv}\n\n"
            f"Question: {question}"
        )

        answer = None
        with st.chat_message("assistant"):
            with st.spinner("Soch raha hoon..."):
                for attempt in range(3):
                    try:
                        resp = client.models.generate_content(model=MODEL, contents=advisor_prompt)
                        answer = resp.text
                        break
                    except Exception:
                        time.sleep(2)
            if answer is None:
                answer = "Server busy hai, thodi der baad try karo."
            st.write(answer)
        st.session_state.chat.append({"role": "assistant", "content": answer})

    st.divider()
    confirm = st.checkbox("Haan, saara data hatana hai")
    if st.button("Reset all data") and confirm:
        FILE.unlink(missing_ok=True)
        st.session_state.chat = []
        st.rerun()
