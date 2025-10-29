import time

import requests
import streamlit as st


def chat_stream(prompt):
    response = requests.post(
        "http://localhost:8910/michelin-recommendation/api/v1/retrieve/",
        json={"user_input": prompt},
    ).json()
    for char in response:
        yield char
        time.sleep(0.01)


def save_feedback(index):
    st.session_state.history[index]["feedback"] = st.session_state[f"feedback_{index}"]


if "history" not in st.session_state:
    st.session_state.history = []

if st.button("Reset", type="primary"):
    response = requests.post(
        "http://localhost:8910/michelin-recommendation/api/v1/retrieve/reset",
    ).json()
    if "history" in st.session_state:
        st.session_state.history = []
        st.session_state.clear()

if "history" in st.session_state:
    for i, message in enumerate(st.session_state.history):
        with st.chat_message(message["role"]):
            st.write(message["content"])
            if message["role"] == "assistant":
                feedback = message.get("feedback", None)
                st.session_state[f"feedback_{i}"] = feedback
                st.feedback(
                    "thumbs",
                    key=f"feedback_{i}",
                    disabled=feedback is not None,
                    on_change=save_feedback,
                    args=(i,),
                )

if prompt := st.chat_input("Say something"):
    with st.chat_message("user"):
        st.write(prompt)
    st.session_state.history.append({"role": "user", "content": prompt})
    with st.chat_message("assistant"):
        response = st.write_stream(chat_stream(prompt))
        st.feedback(
            "thumbs",
            key=f"feedback_{len(st.session_state.history)}",
            on_change=save_feedback,
            args=(len(st.session_state.history),),
        )
    st.session_state.history.append({"role": "assistant", "content": response})