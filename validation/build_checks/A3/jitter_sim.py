"""Clean no-show upholds with ordinary GPS jitter: driver parked 0 to 25 m from the pin, jitter sigma 2 to 8 m, pings every
5 to 30 s, both profiles, platform check in 70% of cases (A3 tier report, check round 1 finding ADV-2).

    python3 -I validation/build_checks/A3/jitter_sim.py kb/tools 600 5

KB_TOOLS_DIR selects the engine (kb/tools of any checkout); the case shape comes from that checkout's selftest.clean."""
import copy, math, random, sys
sys.path.insert(0, sys.argv[1])
from datetime import datetime, timedelta
from kbload import KB
import engine_noshow as E
import selftest as S
kb = KB(); n = int(sys.argv[2]); rng = random.Random(int(sys.argv[3]))
M_LAT = 1 / 111320.0
res = {"cases": 0, "upheld": 0, "auto": 0, "all_in_10m": 0, "auto_all_in_10m": 0}
for i in range(n):
    c = copy.deepcopy(kb.disp002)
    ryde = rng.random() < 0.5
    end_s = rng.choice([200, 240, 300]) if ryde else rng.choice([500, 540, 600])
    t0 = datetime.fromisoformat(S._ts("08:43:00")); end = t0 + timedelta(seconds=end_s)
    S.clean(c, end=end.strftime("%H:%M:%S"))
    if ryde:
        c.pop("cancellation_policy"); c["trip_data"]["booking_type"] = "ON_DEMAND"
    if rng.random() >= 0.7:
        S._no_platform_check(c)
    c["dispute_ticket"]["description"] = S.NON_CONTESTING
    park = rng.uniform(0, 25); ang = rng.uniform(0, 2 * math.pi); sig = rng.uniform(2, 8); step = rng.choice([5, 10, 15, 20, 30])
    base = (S.VENUE[0] + park * math.cos(ang) * M_LAT, S.VENUE[1] + park * math.sin(ang) * M_LAT)
    pings, t, maxd = [], t0, 0.0
    while t <= end:
        la, lo = base[0] + rng.gauss(0, sig) * M_LAT, base[1] + rng.gauss(0, sig) * M_LAT
        d = E.hav(la, lo, *S.VENUE)
        if d > 48:
            la, lo, d = base[0], base[1], park
        maxd = max(maxd, d)
        pings.append((t.strftime("%H:%M:%S"), la, lo, "arrived" if not pings else "waiting")); t += timedelta(seconds=step)
    S._set_wait_pings(c, pings)
    r = E.run(kb, c, None)
    res["cases"] += 1
    if r["trace"].outcome == "UPHOLD":
        res["upheld"] += 1; res["auto"] += r["tier"]["tier"] == "AUTO"
        if maxd <= 10:
            res["all_in_10m"] += 1; res["auto_all_in_10m"] += r["tier"]["tier"] == "AUTO"
print(res)
