"""FairRyde dispute resolution: Streamlit UI.

    streamlit run app/app.py

Pick a case, press Run, and watch the pipeline: the deterministic stages, then the Rider Advocate, the Driver Advocate and the Judge as a chat
timeline, then the verifier and the ruling with its confidence, tier, citations and the two explanations. With no ANTHROPIC_API_KEY the app
replays saved responses, so the demo works offline. Every run of a listed case is saved as a JSON log in app/runs/.

New input: the complaint of a listed case can be edited, and a case can be uploaded as JSON (fairryde_app/userinput.py). Neither has saved
answers, so the agents need live mode. ANTHROPIC_API_KEY and LIVE_ACCESS_CODE come from st.secrets or the environment and are never shown;
with LIVE_ACCESS_CODE set, live mode needs that code, and a browser session gets at most 10 live runs.
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import streamlit as st                                    # noqa: E402

from fairryde_app import cases, config, llm, pipeline, privacy, userinput     # noqa: E402
from fairryde_app.kbaccess import ORGANIZER_PROFILE, case_adapter, get_kb      # noqa: E402

st.set_page_config(page_title="FairRyde", page_icon="⚖️", layout="wide")

API_KEY = userinput.secret("ANTHROPIC_API_KEY", st.secrets)          # never displayed or logged
ACCESS_CODE = userinput.secret("LIVE_ACCESS_CODE", st.secrets)

AVATAR = {"rider_advocate": "🧑", "driver_advocate": "🚗", "judge": "⚖️", "engine": "⚙️", "intake": "🗂️", "evidence": "🔎", "verifier": "🛡️"}
TIER_STYLE = {"AUTO": ("success", "AUTO: the AI ruling is final (both parties can still ask for a human review)"),
              "APPROVE": ("warning", "APPROVE: a person confirms or changes the recommended ruling"),
              "HUMAN": ("error", "HUMAN: a person decides; the agents prepared the case file only")}
STAGES = [("intake", "Intake"), ("evidence", "Evidence"), ("engine", "Engines"), ("rider_advocate", "Rider Advocate"), ("driver_advocate", "Driver Advocate"),
          ("judge", "Judge"), ("resolve", "Verifier + tier")]
ID_TOKEN = re.compile(r"(E-[A-Z]{3}-(?:\d{2}|[RD])|(?:Section|Sections|Precedent) \d+(?:\.\d+)?|(?<![A-Za-z0-9-])[A-Z]{2,4}-[A-Z]?\d+[A-Z]?(?![A-Za-z0-9-]))")


# ------------------------------------------------------------------ helpers
@st.cache_resource
def kb():
    return get_kb()


def esc(text) -> str:
    """Streamlit markdown reads $...$ as LaTeX; every amount (S$3.44) in party or agent text must be escaped."""
    return str(text).replace("$", "\\$")


def money(x) -> str:
    return "none" if x in (None, 0, 0.0) else f"S${x:,.2f}"


def chips(ids, limit: int = 40) -> str:
    return " ".join(f"`{i}`" for i in list(ids)[:limit]) or "none"


def typed(text: str, delay: float):
    for tok in re.split(r"(\s+)", esc(text)):
        yield tok
        if delay and tok.strip():
            time.sleep(delay)


def say(text: str, animate: bool, delay: float = 0.012):
    if animate and delay:
        st.write_stream(typed(text, delay))
    else:
        st.markdown(esc(text))


def shown_complaint(raw: dict) -> str:
    """The complaint as the agents would see it (pseudonymized)."""
    canon, _ = case_adapter.prepare(raw)
    return privacy.pseudonymize(userinput.complaint_of(raw), privacy.build_terms(canon))


def rule_label(rid: str) -> str:
    r = kb().rules.get(rid)
    return f"{rid} {r['name']}" if r else rid


def evidence_df(items):
    return [{"ID": i["id"], "Type": i["type"], "Cred.": i["tier"], "Time": (i["ts"] or "")[11:19], "Summary": i["summary"], "Note": "withheld (GEN-R03)" if i["withheld"] else ("party text" if i["untrusted_text"] else "")}
            for i in items]


# ------------------------------------------------------------------ renderers (the same code draws a live run and a saved one)
def render_case(run, container):
    with container:
        c = run["classification"]
        st.subheader("1. Case and evidence")
        st.caption("This is the pseudonymized view the agents work from: names, plates, phone numbers and account IDs are replaced before any text reaches an LLM. "
                   "Account history is withheld on purpose (the Judge is history-blind).")
        col1, col2 = st.columns([3, 2])
        tk = next(i for i in run["evidence"] if i["id"] == "E-TKT-01")
        with col1:
            st.markdown(f"**{run['case_id']}** · {c['claim_label'] or c['dispute_type_raw']} · filed by the {c['filed_by'].lower()} · profile `{c['profile']}`")
            if run.get("input_label"):
                st.caption(f"🧪 {run['input_label'].capitalize()}.")
            st.info(esc(tk["data"].get("description") or ""))
        with col2:
            st.markdown("**Classification (CLS rules)**")
            for r in c["rules_fired"]:
                st.markdown(esc(f"- `{r['rule']}` {r['result']}"))
        with st.expander(f"Evidence items ({len(run['evidence'])})", expanded=False):
            st.dataframe(evidence_df(run["evidence"]), hide_index=True)
            pick = st.selectbox("Inspect an item", [i["id"] for i in run["evidence"]], key=f"insp-{run['case_id']}")
            st.json(next(i for i in run["evidence"] if i["id"] == pick)["data"] or {"withheld": True})


def render_engine(run):
    e = run["engine"]
    with st.chat_message("engine", avatar=AVATAR["engine"]):
        st.markdown(f"**Rules engine** `{e['engine']}` · profile `{e['profile']}` · claim `{e['claim_type']}`")
        if e["case_file_only"]:
            why = "a safety case (policy v2.1 Section 5.2)" if e["case_file_reason"] == "SAFETY" else "no written rule in code decides it (GEN-R07)"
            st.markdown(f"Result: **{e['outcome']}**. This case is handled as a case file only, because it is {why}. No outcome, amount or measure is proposed.")
        else:
            st.markdown(esc(f"Result: **{e['outcome']}** · amount **{money(e['amount_sgd'])}** · engine tier **{e['engine_tier']}** · reasons {chips(e['reasons'])}"))
        st.caption("Deterministic: no LLM. The advocates see its findings, not its verdict; the Judge sees the verdict.")
        with st.expander("Engine steps and findings"):
            for s in e["steps"]:
                st.markdown(esc(f"- `{s['rule']}` {s['result']}"))
            if e["findings"]:
                st.json(e["findings"], expanded=False)


def render_citations(j, label="Cites"):
    parts = []
    for key, name in (("policy_sections", "policy"), ("rules", "rules"), ("evidence", "evidence"), ("precedents", "precedents")):
        if j.get(key):
            parts.append(f"{name}: {chips(j[key])}")
    if parts:
        st.caption(esc(f"{label} · " + " · ".join(parts)))


def render_message(m, verification, animate, delay):
    agent = m["agent"]
    j = m.get("json_shown") or m.get("json")
    with st.chat_message(agent, avatar=AVATAR[agent]):
        mode_note = "saved response (mock)" if m.get("mock") else f"{m['model']}, {m['latency_s']} s"
        retry = " · retry after verification" if m["attempt"] else ""
        st.markdown(f"**{m['role']}** · {'case file mode' if m['mode'] == 'case_file' else 'ruling mode'}{retry}")
        if m.get("error") or not j:
            st.error(m.get("error") or "no usable answer")
            return
        if agent == "judge" and m["mode"] == "ruling":
            say(j.get("reasoning", ""), animate, delay)
            st.markdown(esc(f"**Judge's ruling:** {j.get('outcome')} · {money(j.get('amount_sgd'))} · confidence **{j.get('confidence')}** · proposed tier **{j.get('tier')}**")
                        + ("" if j.get("agreement_with_engine", True) else " · :red[disagrees with the rules engine]"))
            render_citations(j)
        elif agent == "judge":
            say(j.get("case_summary", ""), animate, delay)
            if j.get("timeline"):
                with st.expander("Timeline from the records"):
                    for t in j["timeline"]:
                        st.markdown(esc(f"- {t.get('ts', '')} {t.get('event', '')} {chips(t.get('evidence', []))}"))
            for k, title in (("disputed_points", "Where the accounts differ or the record is silent"), ("open_questions", "Open questions for the reviewer")):
                if j.get(k):
                    with st.expander(title):
                        for x in j[k]:
                            st.markdown(esc("- " + (f"{x.get('point')} {chips(x.get('evidence', []))}" if isinstance(x, dict) else str(x))))
        elif m["mode"] == "case_file":
            say(j.get("account_summary", ""), animate, delay)
            render_citations(j)
            if j.get("open_questions"):
                with st.expander("Open questions"):
                    for x in j["open_questions"]:
                        st.markdown(esc(f"- {x}"))
        else:
            st.markdown(esc(f"*Stance:* **{j.get('stance', '')}**"))
            say(j.get("brief", ""), animate, delay)
            with st.expander(f"Arguments ({len(j.get('arguments', []))}) and what the other side can say"):
                for i, a in enumerate(j.get("arguments", []), 1):
                    st.markdown(esc(f"**{i}.** {a.get('point')}  \n{chips(a.get('evidence', []))} {chips(a.get('rules', []))} {chips(a.get('policy_sections', []))} {chips(a.get('precedents', []))}"))
                for r in j.get("rebuttals", []):
                    st.markdown(esc(f"↩︎ *to rider argument {r.get('to_rider_argument')}:* {r.get('reply')}  \n{chips(r.get('evidence', []))}"))
                for key, title in (("weaknesses", "Weak point"), ("concessions", "Concession")):
                    for w in j.get(key, []):
                        st.markdown(esc(f"*{title}:* {w.get('point')}  {chips(w.get('evidence', []))}"))
            st.caption("An advocate's brief is an argument, never evidence.")
        if verification:
            bad = [c for c in verification["checks"] if c["status"] in ("FAIL", "WARN")]
            if not bad:
                st.success("Verifier: every cited ID exists" + (" and the amount equals the engine's" if agent == "judge" and m["mode"] == "ruling" else ""), icon="🛡️")
            else:
                for c in bad:
                    (st.error if c["status"] == "FAIL" else st.warning)(esc(f"Verifier: {c['detail']}"), icon="🛡️")
        st.caption(mode_note + (f" · request {m['request_chars']:,} characters, privacy check passed" if m.get("privacy_boundary") is not None else ""))


def render_timeline_from(run, container, animate=False, delay=0.0, pace=0.0):
    """Draw the conversation of a finished run from its events."""
    with container:
        st.subheader("2. The agents argue")
        render_engine(run)
        pending = None
        for ev in run["events"]:
            if ev["type"] == "message":
                pending = ev["message"]
                if pace and animate:
                    with st.spinner(f"{pending['role']} is working..."):
                        time.sleep(pace)
                vr = next((e for e in run["events"] if e["type"] == "verification" and e["agent"] == pending["agent"] and e.get("attempt", 0) == pending["attempt"]
                           and run["events"].index(e) > run["events"].index(ev)), None)
                render_message(pending, vr, animate, delay)
            elif ev["type"] == "notice":
                (st.warning if ev["level"] == "warning" else st.info)(esc(ev["text"]), icon="⚠️")


def render_result(run, container):
    r, e = run["result"], run["engine"]
    with container:
        st.subheader("3. Ruling")
        kind, text = TIER_STYLE[r["tier"]]
        getattr(st, kind)(esc(f"**{r['status'].replace('_', ' ')}** · tier **{text}**"))
        conf = r.get("confidence") or {}
        cols = st.columns([2.2, 1.2, 2.2, 1.2, 1.2])
        for col, (label, value) in zip(cols, [("Outcome", r["outcome"]), ("Amount", money(r["amount_sgd"])), ("Payer → payee", f"{r['payer'] or '-'} → {r['payee'] or '-'}"),
                                              ("Confidence", f"{conf['final']:.2f}" if conf.get("final") is not None else "n/a"), ("Tier", r["tier"])]):
            col.caption(label)
            col.markdown(esc(f"#### {value}"))
        if conf.get("final") is not None:
            thr = conf.get("threshold")
            st.progress(min(1.0, conf["final"]), text=f"confidence {conf['final']:.2f} = lower of Judge {conf.get('judge')} and engine {conf.get('engine')}"
                        + (f" · Section 6 threshold {thr:.2f}" if thr else ""))
        if r["fee_stands_sgd"] and r["outcome"] == "UPHOLD":
            st.caption(esc(f"The fee of {money(r['fee_stands_sgd'])} stands and goes to the driver."))
        st.markdown("**Why this tier**")
        for t in (r["tier_reasons"] or ["Section 6.1 / the AUTH rules ask for nothing more: the ruling is final."])[:6]:
            st.markdown(esc(f"- {t}"))
        if r["escalation"]["required"]:
            st.warning(f"Escalated to a human reviewer (gate {r['escalation']['gate']}) with the full case file.", icon="🙋")
        st.markdown("**Citations** (all verified to exist)")
        rows = ([{"Kind": "Policy", "ID": s, "What": ""} for s in r["policy_sections"]] + [{"Kind": "Rule", "ID": x, "What": rule_label(x).split(" ", 1)[-1] if " " in rule_label(x) else ""} for x in r["rules"]]
                + [{"Kind": "Evidence", "ID": x, "What": next((i["summary"] for i in run["evidence"] if i["id"] == x), "")} for x in r["evidence"]]
                + [{"Kind": "Precedent", "ID": x, "What": ""} for x in r["precedents"]])
        if rows:
            st.dataframe(rows, hide_index=True, height=min(38 * (len(rows) + 1), 430))
        else:
            st.caption("No citations: the agents prepared a case file.")
        a, b = st.columns(2)
        with a:
            st.markdown("**Explanation for the rider**")
            st.info(esc(r["rider_explanation"]))
        with b:
            st.markdown("**Explanation for the driver**")
            st.info(esc(r["driver_explanation"]))
        st.caption(f"Explanations: {'written by the Judge and checked (EXP-03)' if r['explanation_source'] == 'judge' else 'drafted by the rules engine from its findings' if r['explanation_source'] == 'engine_draft' else 'standard notice'}.")
        ec = run.get("expected_check")
        if run.get("input_label"):
            st.info(f"{run['input_label'].capitalize()}: the result is not compared with an expected result.", icon="🧪")
        elif ec:
            x = ec["expected"]
            msg = f"Expected (from {x['source']}): {x['outcome']}, {money(x['amount_sgd'])}, tier {x['tier']}."
            (st.success if ec["ok"] else st.warning)(esc(("Matches. " if ec["ok"] else "Differs. ") + msg), icon="🎯")
        with st.expander("Verifier checks"):
            for v in run["verification"]["judge"]:
                st.markdown(f"**Judge, attempt {v['attempt']}**")
                for c in v["checks"]:
                    st.markdown(esc(f"- {'✅' if c['status'] == 'PASS' else '❌' if c['status'] == 'FAIL' else '⚠️' if c['status'] == 'WARN' else 'ℹ️'} {c['detail']}"))
            for k in ("rider_advocate", "driver_advocate"):
                v = run["verification"].get(k)
                if v:
                    st.markdown(f"**{k.replace('_', ' ').title()}**")
                    for c in v["checks"]:
                        st.markdown(esc(f"- {'✅' if c['status'] == 'PASS' else '❌' if c['status'] == 'FAIL' else '⚠️'} {c['detail']}"))
        d1, d2 = st.columns(2)
        d1.download_button("Download run log (JSON)", json.dumps(run, indent=1, ensure_ascii=False), file_name=f"{run['run_id']}.json", mime="application/json")
        if r.get("case_file"):
            d2.download_button("Download case file for the reviewer (JSON)", json.dumps(r["case_file"], indent=1, ensure_ascii=False), file_name=f"case_file_{run['case_id']}.json", mime="application/json")
        if run.get("log_file"):
            st.caption(f"Saved: {Path(run['log_file']).relative_to(config.ROOT) if str(config.ROOT) in run['log_file'] else run['log_file']}")


def render_stages_note(container):
    with container:
        st.subheader("3. Ruling")
        st.info("Deterministic stages only: intake, evidence and the rules engine ran, and their result is shown above. The three agents (Rider Advocate, "
                "Driver Advocate, Judge) need live mode (the sidebar says why it is off), so there is no ruling, verifier check or approval tier for this run.", icon="🔒")


def render_progress(done: set, current: str | None, container):
    cols = container.columns(len(STAGES))
    for col, (key, label) in zip(cols, STAGES):
        icon = "✅" if key in done else "⏳" if key == current else "▫️"
        col.markdown(f"{icon} {label}")


# ------------------------------------------------------------------ page
st.title("⚖️ FairRyde")
st.caption("Multi-agent resolution of ride-hailing disputes · Tencent Cloud × AI Singapore hackathon 2026, Ryde track · knowledge base "
           f"v{kb().version} · Ryde Dispute Resolution Policy v2.1")

with st.sidebar:
    st.header("Case")
    source = st.radio("Input", ["Listed case", "Upload a case"], horizontal=True, key="source")
    custom_case, profile, input_label, info = None, None, None, None      # custom_case: an edited or uploaded case (no saved answers, no reference ruling)
    if source == "Listed case":
        catalog = cases.list_cases()
        groups = {"organizer": "Organizer samples", "validation": "Validation cases (E01 to E15)", "demo": "Demo"}
        options = [i.case_id for k in ("organizer", "validation", "demo") for i in catalog if i.kind == k]
        case_id = st.selectbox("Pick a case", options, format_func=lambda c: f"{c}  ·  {cases.get_info(c).dispute_type}", key="case")
        info = cases.get_info(case_id)
        st.caption(f"{groups[info.kind]}. " + ("Profile organizer_v2_1 (policy v2.1)." if info.kind == "organizer" or info.profile_override else "Regression case: Ryde's published policy."))
        original = shown_complaint(cases.load_case(case_id))
        text = st.text_area("Complaint (edit it to try your own wording)", value=original, key=f"complaint-{case_id}", height=180)
        if text.strip() and text.strip() != original.strip():
            case_id, custom_case, profile = userinput.edited_case(case_id, text)
            input_label = userinput.EDITED_LABEL
            st.caption(f"Edited: the run uses a copy of the case with this text, under profile `{profile}`, and has no reference ruling.")
    else:
        case_id = None
        st.download_button("Download an example case (JSON)", json.dumps(userinput.example_upload(), indent=1, ensure_ascii=False), file_name="fairryde_example_case.json",
                           mime="application/json", help="A synthetic surge-fare dispute in the organizer's sample format, built from our own demo data.")
        up = st.file_uploader("Case file in the organizer's sample format (JSON, max 1 MB)", type=["json"], key="upload")
        if up is not None:
            try:
                case_id, custom_case = userinput.parse_upload(up.getvalue())
                profile, input_label = ORGANIZER_PROFILE, userinput.UPLOADED_LABEL
                st.success(f"{case_id}: a valid case ({custom_case['dispute_ticket']['dispute_type']}). It runs under organizer_v2_1 and has no reference ruling.")
            except userinput.InvalidCase as exc:
                st.error(f"This file cannot be used. {exc}")
    st.header("Agents")
    has_key, code_required = bool(API_KEY), bool(ACCESS_CODE)
    unlocked = False
    if has_key and code_required:
        entered = st.text_input("Access code for live mode", type="password", key="access_code")
        unlocked = userinput.code_ok(entered, ACCESS_CODE)
        if entered and not unlocked:
            st.error("That access code is not right.")
    used = st.session_state.get("live_runs", 0)
    choice = st.radio("LLM mode", ["Auto", "Mock (saved responses)", "Live (Claude API)"],
                      help="Auto uses the Claude API when it is available here (an API key, the access code if one is set, live runs left), else replays saved responses.")
    custom = custom_case is not None
    mode, why_not_live = userinput.decide_mode(choice.split()[0], has_key=has_key, code_required=code_required, unlocked=unlocked, live_runs_used=used, custom=custom)
    if custom and mode == "stages":
        if choice.startswith("Mock") and why_not_live is None:
            st.info("An edited or uploaded case has no saved responses: choose Auto or Live to run the three agents. Mock shows the deterministic stages only.")
        elif why_not_live == "live mode needs the access code":
            st.info("The three agents (Rider Advocate, Driver Advocate, Judge) need the access code. Without it, this run shows the deterministic stages only: intake, evidence and the rules engine.")
        else:
            st.info(f"The three agents need live mode, and {why_not_live}. This run shows the deterministic stages only: intake, evidence and the rules engine.")
    elif choice.startswith("Live") and mode != "live":
        st.warning(f"Live mode is off: {why_not_live}. Replaying saved responses instead.")
    st.markdown("Running the **deterministic stages only** (no agents)." if mode == "stages" else f"Running in **{mode}** mode" + (f" with `{config.MODEL}`." if mode == "live" else " (offline replay)."))
    scenario = "normal"
    if mode == "mock":
        scenario = st.selectbox("Mock scenario", list(llm.MOCK_SCENARIOS), format_func=lambda s: s, help="Change the saved Judge answer on purpose to see the verifier at work.")
        st.caption(llm.MOCK_SCENARIOS[scenario])
    typing = st.checkbox("Typing effect and pacing", value=True)
    run_clicked = st.button("▶ Run the pipeline", type="primary", disabled=case_id is None)
    if run_clicked and mode == "live":
        used = st.session_state["live_runs"] = used + 1                 # counted when the run starts, so a failed run counts too
    if has_key:
        st.caption(f"Live runs left in this browser session: {max(0, userinput.LIVE_RUN_CAP - used)} of {userinput.LIVE_RUN_CAP}.")
    saved = sorted(config.RUNS_DIR.glob("*.json"), reverse=True)[:8] if config.RUNS_DIR.exists() else []
    if saved:
        with st.expander("Open a saved run"):
            pick = st.selectbox("Run log", [p.name for p in saved], key="saved_pick")
            if st.button("Open"):
                st.session_state["run"] = pipeline.load_run(config.RUNS_DIR / pick)

c_progress = st.container()
c_case = st.container()
c_time = st.container()
c_result = st.container()

if run_clicked:
    st.session_state.pop("run", None)
    done: set = set()
    progress_slot = c_progress.empty()
    status = c_progress.status(f"Running {case_id} in {mode} mode", expanded=False)
    live_run = {"events": [], "input_label": input_label}

    def draw_progress(current):
        with progress_slot.container():
            render_progress(done, current, st)

    draw_progress("intake")
    time_box = c_time.container()
    with time_box:
        st.subheader("2. The agents argue")

    def on_event(ev):
        live_run["events"].append(ev)
        t = ev["type"]
        if t == "stage" and ev["status"] == "start":
            key = ev["stage"]
            draw_progress(key)
            status.update(label=f"{ev['title']}...")
            if key in ("rider_advocate", "driver_advocate", "judge") and typing and mode == "mock":
                time.sleep(0.7)
        elif t == "stage" and ev["status"] == "end":
            done.add(ev["stage"])
            if ev["stage"] == "intake":
                live_run["classification"] = ev["data"]
            elif ev["stage"] == "evidence":
                live_run.update(evidence=ev["data"]["items"], case_id=case_id)
                render_case(live_run, c_case)
            elif ev["stage"] == "engine":
                live_run["engine"] = ev["data"]
                with time_box:
                    render_engine(live_run)
        elif t == "message":
            m = ev["message"]
            with time_box:
                live_run["last_message"] = m
                live_run["slot"] = st.container()
                with live_run["slot"]:
                    render_message(m, None, animate=typing, delay=0.006 if typing else 0)
        elif t == "verification":
            m = live_run.get("last_message")
            if m is not None:
                bad = [c for c in ev["checks"] if c["status"] in ("FAIL", "WARN")]
                with live_run["slot"]:
                    if not bad:
                        st.success("Verifier: every cited ID exists" + (" and the amount equals the engine's" if ev["agent"] == "judge" and m["mode"] == "ruling" else ""), icon="🛡️")
                    for c in bad:
                        (st.error if c["status"] == "FAIL" else st.warning)(esc(f"Verifier: {c['detail']}"), icon="🛡️")
        elif t == "notice":
            with time_box:
                st.warning(esc(ev["text"]), icon="⚠️")

    # the pipeline's events are drawn as they arrive; the case section is drawn from the stage events once the evidence is known
    try:
        if mode == "stages":
            run = pipeline.run_stages(case_id, custom_case, profile=profile, emit=on_event, input_label=input_label)
        else:
            client = llm.AnthropicClient(api_key=API_KEY) if mode == "live" else None
            run = pipeline.run_case(case_id, mode=mode, scenario=scenario, emit=on_event, client=client, raw_case=custom_case, profile=profile,
                                    input_label=input_label, save=not custom)          # edited and uploaded runs are not kept on the server
    except Exception as exc:                                    # a privacy block or a programming error must be visible, never silent
        status.update(label="The run stopped", state="error")
        st.exception(exc)
        st.stop()
    if mode == "stages":
        status.update(label=f"Done: deterministic stages only · engine {run['engine']['outcome']}", state="complete")
        draw_progress(None)
        render_stages_note(c_result)
    else:
        status.update(label=f"Done: {run['result']['outcome']} · tier {run['result']['tier']}", state="complete")
        done.update(k for k, _ in STAGES)
        draw_progress(None)
        render_result(run, c_result)
    st.session_state["run"] = run
elif st.session_state.get("run"):
    run = st.session_state["run"]
    stages_only = run["mode"] == "stages"
    with c_progress:
        render_progress({"intake", "evidence", "engine"} if stages_only else {k for k, _ in STAGES}, None, st)
    render_case(run, c_case)
    if stages_only:
        with c_time:
            st.subheader("2. The agents argue")
            render_engine(run)
        render_stages_note(c_result)
    else:
        render_timeline_from(run, c_time, animate=False)
        render_result(run, c_result)
else:
    with c_case:
        st.subheader("Pick a case, then press Run")
        st.markdown("The pipeline: **intake and classification** (CLS rules) → **evidence extraction** with evidence IDs → **reference engines** (no-show, route, toll, surge) → "
                    "**Rider Advocate** → **Driver Advocate** → **Judge** → **verifier** → **approval tier** (AUTH rules, policy v2.1 Section 6).")
        raw = custom_case if custom_case is not None else cases.load_case(case_id) if case_id else None
        if raw is None:
            st.info("Upload a case file (JSON, max 1 MB) in the sidebar, or download the example file to see the format.")
        else:
            st.markdown(esc(f"**{case_id}** · `{raw['dispute_ticket']['dispute_type']}` · filed by the {raw['dispute_ticket'].get('filed_by', 'rider')}"))
            st.info(esc(shown_complaint(raw)))
            if input_label:
                st.caption(f"🧪 {input_label.capitalize()}: the result will not be compared with an expected result.")
            else:
                x = info.expected
                with st.expander("Expected result (used to score the run, never an input)"):
                    st.markdown(esc(f"Outcome **{x.get('outcome')}** · amount **{money(x.get('amount_sgd'))}** · tier **{x.get('tier')}**  \nSource: {x.get('source')}"))
