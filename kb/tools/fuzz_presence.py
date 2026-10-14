"""Randomized check of the GPS presence logic (CW-R06, CW-F04, CW-F04B): an automatic ruling must never rest on GPS that leaves the
question open. Random variants of the clean baseline V06: both profiles, with and without the platform arrival check,
approach pings before the arrival, random gaps (5 to 180 s), positions inside or 60, 150 or 400 m out, data that stops early.

    python3 tools/fuzz_presence.py 2000 11      # cases, seed

Invariant for AUTO rulings (independent of the engine's run logic; uses only the engine's wait start and window):
  UPHOLD (D29, step A3): no ping outside the area in [start, wend], the engine's F-GPS-LOGIC is false, and the first ping
          away after the window end does not follow a last inside ping more than tol before the window end.
  UPHOLD: every outside ping in [start, wend + tol] that is not a data error is certainly brief (inside observations
          around it within LEFT_MIN_OUTSIDE_S), or a departure at or after the threshold within tolerance, or an approach
          ping within tolerance of the start.
  WAIVE R4: some outside stretch overlapping the counting window is certainly a departure.
"""
import copy
import random
import sys
from datetime import datetime, timedelta

import engine_noshow as E
import selftest as S
TOL, LMIN, VMAX = 30, 60, 120
OFFS = {"in": 0.0, "60": 0.00054, "150": 0.00135, "400": 0.0036}


def T(h):
    return datetime.fromisoformat(S._ts(h))


def hms(t):
    return t.strftime("%H:%M:%S")


def make(kb, rng):
    c = copy.deepcopy(kb.disp002)
    ryde = rng.random() < 0.5
    t0 = T("08:43:00")
    end_s = rng.choice([170, 180, 181, 200, 240, 300]) if ryde else rng.choice([470, 479, 480, 481, 500, 540, 600])
    end = t0 + timedelta(seconds=end_s)
    S.clean(c, end=hms(end))
    if ryde:
        c.pop("cancellation_policy")
        c["trip_data"]["booking_type"] = "ON_DEMAND"
    platform = rng.random() < 0.6
    if not platform:
        S._no_platform_check(c)
    if rng.random() < 0.5:
        c["dispute_ticket"]["description"] = S.NON_CONTESTING
    pings = []
    if platform and rng.random() < 0.4:
        # targeted: steady pings, silence, a short trip away near the end of the waiting window, then maybe back
        thr = 180 if ryde else 480
        met = (end_s > thr) if ryde else (end_s >= thr)
        wend = t0 + timedelta(seconds=thr) if met else end
        step = rng.choice([10, 20, 30])
        t_quiet = wend - timedelta(seconds=rng.choice([20, 40, 60, 100, 200]))
        t = t0
        while t <= t_quiet:
            pings.append((hms(t), *S.VENUE, "waiting"))
            t += timedelta(seconds=step)
        t_out = wend + timedelta(seconds=rng.choice([-40, -20, -5, 0, 10, 25, 40]))
        where = S.VENUE[0] + OFFS[rng.choice(["60", "150", "400"])]
        n_out = rng.choice([1, 1, 2])
        for i in range(n_out):
            pings.append((hms(t_out + timedelta(seconds=10 * i)), where, S.VENUE[1], "waiting"))
        if rng.random() < 0.7:
            t_back = t_out + timedelta(seconds=10 * (n_out - 1) + rng.choice([10, 20, 60]))
            pings += [(hms(t_back + timedelta(seconds=20 * i)), *S.VENUE, "waiting") for i in range(3)]
        pings = sorted({p[0]: p for p in pings}.values())
    else:
        t = t0 - timedelta(seconds=rng.choice([0, 20, 60, 200]))
        pos = rng.choice(["in", "60", "150"])
        while t <= end + timedelta(seconds=rng.choice([0, 30, 120])):
            if rng.random() < 0.25:
                pos = rng.choice(["in", "in", "60", "150", "400"])
            pings.append((hms(t), S.VENUE[0] + OFFS[pos], S.VENUE[1], "waiting"))
            t += timedelta(seconds=rng.choice([5, 10, 30, 60, 90, 120, 180]))
        if rng.random() < 0.3:
            pings = pings[: rng.randint(1, len(pings))]
    keep = [g for g in c["gps_telemetry"] if g["timestamp"] < S._ts(pings[0][0])] if pings else c["gps_telemetry"]
    c["gps_telemetry"] = keep + [{"timestamp": S._ts(h), "lat": la, "lng": lo, "speed_kmh": 0, "status": st} for h, la, lo, st in pings]
    return c, platform


def check(c, platform, r):
    tr, tier = r["trace"], r["tier"]
    if tier["tier"] != "AUTO" or tr.findings["F-ARRIVAL-VALID"]["value"] != "TRUE":
        return None
    start = tr.wait_start
    wend = datetime.fromisoformat(tr.presence_detail["window"][1])
    t_arr = datetime.fromisoformat(tr.arrival_detail["t_arr"])
    obs = []
    for g in sorted(c["gps_telemetry"], key=lambda g: g["timestamp"]):
        obs.append((datetime.fromisoformat(g["timestamp"]), E.hav(g["lat"], g["lng"], *S.VENUE) <= 50, g["lat"], g["lng"]))
    if platform:
        k = next((i for i, o in enumerate(obs) if o[0] >= t_arr), len(obs))
        obs.insert(k, (t_arr, True, S.VENUE[0], S.VENUE[1]))
    first_in = next((i for i, o in enumerate(obs) if o[1]), None)

    def kmh(a, b):
        dt = (b[0] - a[0]).total_seconds()
        return E.hav(a[2], a[3], b[2], b[3]) / dt * 3.6 if dt > 0 else 0
    if tr.outcome == "UPHOLD":
        if tr.findings.get("F-GPS-LOGIC", {}).get("value"):
            return "AUTO UPHOLD while F-GPS-LOGIC is true (D29: FairRyde's own GPS logic decides, so approval)"
        out_in_window = [o for o in obs if not o[1] and start <= o[0] <= wend]
        if out_in_window:                                 # D29: on the pings alone, every ping in the window is inside the area
            return f"AUTO UPHOLD with an outside ping in the window at {hms(out_in_window[0][0])} (start {hms(start)}, wend {hms(wend)}; D29)"
        end_t = datetime.fromisoformat(c["trip_data"]["cancellation_time"])
        for i, o in enumerate(obs):                       # window end (A3 check round 2): first seen away after the window end, last seen at the pin too early
            if not o[1] and wend < o[0] <= end_t:
                prev_in = [x[0] for x in obs[:i] if x[1]]
                if prev_in and prev_in[-1] < wend - timedelta(seconds=TOL):
                    return f"AUTO UPHOLD: last inside {hms(prev_in[-1])}, more than {TOL} s before wend {hms(wend)}, then outside at {hms(o[0])}"
                break
        for i, o in enumerate(obs):
            if o[1] or not (start <= o[0] <= wend + timedelta(seconds=TOL)):
                continue
            if first_in is None or i < first_in:          # approach ping
                if o[0] <= start + timedelta(seconds=TOL) or o[0] >= wend - timedelta(seconds=TOL):
                    continue
                return f"AUTO UPHOLD with an approach ping at {hms(o[0])} (start {hms(start)}, wend {hms(wend)})"
            j0 = max(k for k in range(i) if obs[k][1])
            nxt = [k for k in range(i + 1, len(obs)) if obs[k][1]]
            st0, st1 = j0 + 1, ((nxt[0] - 1) if nxt else len(obs) - 1)
            if kmh(obs[j0], obs[st0]) > VMAX or (nxt and kmh(obs[st1], obs[nxt[0]]) > VMAX):
                continue
            prev_in, next_in = obs[j0][0], (obs[nxt[0]][0] if nxt else None)
            brief = next_in is not None and (next_in - prev_in).total_seconds() <= LMIN
            after_thr = o[0] >= wend - timedelta(seconds=TOL) and prev_in >= wend - timedelta(seconds=TOL)
            if not (brief or after_thr):
                return f"AUTO UPHOLD with outside ping at {hms(o[0])}: last inside {hms(prev_in)}, next inside {hms(next_in) if next_in else None}, start {hms(start)}, wend {hms(wend)}"
    if tr.outcome == "WAIVE_FEE" and tr.dt_row == "R4":
        ok, i = False, (first_in + 1 if first_in is not None else 0)
        while i < len(obs):
            if obs[i][1]:
                i += 1
                continue
            j = i
            while j + 1 < len(obs) and not obs[j + 1][1]:
                j += 1
            a, b, ret = obs[i][0], obs[j][0], j + 1 < len(obs)
            if a <= wend - timedelta(seconds=TOL) and b >= start and ((b - a).total_seconds() >= LMIN or (not ret and j > i)):
                ok = True
            i = j + 1
        if not ok:
            return "AUTO R4 WAIVE without a certain departure"
    return None


def run(kb, n, seed):
    """Returns (cases, automatic rulings, crashes, findings)."""
    rng = random.Random(seed)
    bad, autos, crashes = [], 0, 0
    for it in range(n):
        c, platform = make(kb, rng)
        try:
            r = E.run(kb, c, None)
        except Exception as e:                        # any crash is a finding
            crashes += 1
            bad.append((it, f"CRASH {type(e).__name__}: {e}", platform, [(g["timestamp"][11:19], round(E.hav(g["lat"], g["lng"], *S.VENUE))) for g in c["gps_telemetry"]]))
            continue
        autos += r["tier"]["tier"] == "AUTO"
        msg = check(c, platform, r)
        if msg:
            bad.append((it, msg, r["trace"].dt_row, platform, r["trace"].profile,
                        [(g["timestamp"][11:19], round(E.hav(g["lat"], g["lng"], *S.VENUE))) for g in c["gps_telemetry"] if g["timestamp"] >= S._ts("08:40:00")],
                        c["trip_data"]["cancellation_time"][11:19]))
    return n, autos, crashes, bad


if __name__ == "__main__":
    from kbload import KB
    n_, autos_, crashes_, bad_ = run(KB(), int(sys.argv[1]) if len(sys.argv) > 1 else 300, int(sys.argv[2]) if len(sys.argv) > 2 else 11)
    print(f"{n_} cases, {autos_} AUTO, {crashes_} crashes, {len(bad_)} findings")
    for b in bad_[:10]:
        print(b)
