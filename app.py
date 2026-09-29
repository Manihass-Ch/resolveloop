"""ResolveLoop: learn from confirmed backend incident resolutions."""
import os
from dotenv import load_dotenv
import streamlit as st
from hindsight_client import Hindsight

load_dotenv()
st.set_page_config(page_title="ResolveLoop", page_icon="🧠", layout="wide")

@st.cache_resource
def memory_client():
    key = os.getenv("HINDSIGHT_API_KEY", "").strip()
    if not key or key == "replace-with-your-key":
        return None
    return Hindsight(
        base_url=os.getenv("HINDSIGHT_BASE_URL", "https://api.hindsight.vectorize.io"),
        api_key=key,
    )

def bank_id():
    return os.getenv("HINDSIGHT_BANK_ID", "resolveloop-backend-demo")

def ensure_bank(client):
    # Creating an existing bank may fail; recall below checks the connection.
    try:
        client.create_bank(bank_id=bank_id(), name="ResolveLoop backend incidents")
    except Exception:
        pass

st.title("ResolveLoop")
st.caption("An engineering incident assistant that remembers confirmed fixes across services")
st.info("Demo with fictional data only. Do not enter customer, employee, or proprietary records.")

client = memory_client()
if client is None:
    st.error("Add HINDSIGHT_API_KEY to a local .env file, then restart Streamlit.")
    st.code("copy .env.example .env\n# Edit .env and add your key")
    st.stop()

with st.sidebar:
    st.header("Memory")
    st.write(f"Hindsight bank: `{bank_id()}`")
    st.write("1. Recall past outcomes\n2. Reflect on a new observation\n3. Retain a confirmed resolution")
    st.caption("Use a different bank ID in .env to reset the demo.")

st.subheader("1 · Investigate an incident")
with st.form("investigate"):
    case_id = st.text_input("Fictional incident ID", "INC-204")
    template = st.text_input("Service", "orders-api")
    observation = st.text_area(
        "Symptoms and relevant logs",
        "After deployment, GET /api/orders returns 401 for valid bearer tokens. Login still succeeds. Downstream Spring Security logs show no Authorization header.",
        height=110,
    )
    investigate = st.form_submit_button("Recall and suggest checks", type="primary")

if investigate:
    if not observation.strip():
        st.warning("Enter an observation first.")
    else:
        try:
            ensure_bank(client)
            query = f"Backend incident in service {template}: {observation} What confirmed fixes or failed attempts are relevant?"
            memories = client.recall(bank_id=bank_id(), query=query)
            recalled = [item.text for item in memories.results]
            st.session_state["case"] = (case_id.strip(), template.strip(), observation.strip())
            st.session_state["recalled"] = recalled
            prompt = (
                f"An engineer is investigating fictional incident {case_id} in service {template}. "
                f"Symptoms and logs: {observation}. Based on remembered confirmed outcomes, "
                "give up to three specific checks in priority order. Clearly separate remembered evidence "
                "from hypotheses. If there is no relevant memory, say so and suggest generic checks. "
                "Do not claim the issue is fixed."
            )
            answer = client.reflect(bank_id=bank_id(), query=prompt)
            st.session_state["answer"] = answer.text
        except Exception as exc:
            st.error(f"Hindsight request failed: {exc}")

if "answer" in st.session_state:
    left, right = st.columns([2, 1])
    with left:
        st.subheader("Suggested investigation")
        st.write(st.session_state["answer"])
    with right:
        st.subheader("Recalled evidence")
        if st.session_state["recalled"]:
            for i, item in enumerate(st.session_state["recalled"], 1):
                st.markdown(f"**Memory {i}** · {item}")
        else:
            st.write("No matching past resolution found. This is the before-memory moment.")

st.divider()
st.subheader("2 · Record the verified outcome")
with st.form("resolve"):
    resolution = st.text_area(
        "Root cause, fix, and verification",
        placeholder="Example: Gateway route dropped the Authorization header; restored forwarding and confirmed authenticated requests returned 200.",
        height=95,
    )
    failed = st.text_input("What did not work? (optional)")
    confirmed = st.checkbox("I verified this outcome using fictional/demo data")
    save = st.form_submit_button("Retain confirmed resolution")

if save:
    if "case" not in st.session_state:
        st.warning("Investigate the case first, then record its outcome.")
    elif not resolution.strip() or not confirmed:
        st.warning("Enter the verified outcome and tick the confirmation box.")
    else:
        case_id, template, observation = st.session_state["case"]
        content = (
            f"Backend incident {case_id}. Service: {template}. "
            f"Symptoms and logs: {observation}. Confirmed root cause and resolution: {resolution.strip()}. "
            f"Unsuccessful attempt: {failed.strip() or 'not recorded'}. "
            "Outcome: verified using fictional demo data."
        )
        try:
            ensure_bank(client)
            client.retain(bank_id=bank_id(), content=content)
            st.success("Resolution retained in Hindsight. Investigate a similar case above to see the change.")
        except Exception as exc:
            st.error(f"Could not retain the resolution: {exc}")

with st.expander("Demo sequence"):
    st.markdown("""
1. Start with an empty bank and investigate the default 401 incident. Notice the generic answer and empty recalled evidence.
2. Record: **A gateway configuration change dropped the Authorization header; restored forwarding and verified GET /api/orders returned 200 with a valid token.** Tick the confirmation box and retain it.
3. Change the case to **INC-205**, service to **billing-api**, and symptoms to **After a gateway deployment, GET /api/invoices returns 401 for valid bearer tokens while login succeeds; downstream logs show no Authorization header.** Investigate again.
4. Show the retrieved incident and targeted checks. A past fix remains a hypothesis until verified on the new service.
""")
