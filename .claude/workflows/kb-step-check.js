export const meta = {
  name: 'kb-step-check',
  description: 'Independent check of one KB build step, as in A1: fresh KB appliers re-decide the affected cases, four reviewers each check one dimension, and one skeptic per reviewer tries to refute every finding',
  whenToUse: 'After each v0.2 build step (A1 to A4) and its fixes. Run round 1; run round 2 only when round 1 had CRITICAL or MAJOR findings (CLAUDE.md stop rules: at most two rounds).',
  phases: [
    { title: 'Apply', detail: 'fresh KB appliers decide the affected cases from the KB only' },
    { title: 'Review', detail: 'fidelity and scope; sources and credibility; adversarial test; consistency' },
    { title: 'Verify', detail: 'one skeptic per reviewer tries to refute each finding' },
  ],
}

// args: {
//   step: 'A2', round: 1, base: '<commit before the step>', head: '<commit to check>',
//   task: 'what the step had to do, quoted from the fix list, NEXT_STEPS and the owner\'s decisions',
//   apply_cases: ['E07'],                     // round 1 cases (validation/V4_e2e/cases) a fresh KB applier re-decides
//   focus: { fidelity: '...', grounding: '...', adversarial: '...', consistency: '...' },   // step-specific checks
//   prior: 'validation/build_checks/<step>/...disposition.jsonl or null (round 2: what round 1 found and how it was handled)',
// }
// The engine reruns (validation/tools/rerun_engine.py) and the build are E steps the builder runs outside this workflow.
const A = args || {}
const REPO = '/home/user/fairryde'
const STEP = A.step || 'step'
const ROUND = A.round || 1
const SCRATCH = `/tmp/${STEP.toLowerCase()}check${ROUND}/`
const FOCUS = A.focus || {}
const SEVERITY = 'Severity: CRITICAL = would change an outcome, an amount or the automatic-versus-human decision (tier) in an in-scope type; MAJOR = wrong, but outcome-neutral in the current scope, or affects an out-of-scope type; MINOR = wording, labeling or missing detail.'
const READONLY = `You did not write this change and you never edit anything: do not modify, create or delete any file under ${REPO} (no git commands that change state either). Put scratch scripts under ${SCRATCH} only. Your structured output is your only deliverable.`

const APPLY_SCHEMA = {
  type: 'object',
  properties: {
    case_id: { type: 'string' }, kb_type: { type: 'string' }, playbook: { type: 'string' },
    steps: { type: 'array', items: { type: 'object', properties: {
      step: { type: 'string' }, rule_id: { type: 'string' }, finding: { type: 'string' }, case_evidence: { type: 'string' } },
      required: ['step', 'rule_id', 'finding', 'case_evidence'] } },
    outcome: { type: 'string' }, amount_sgd: { type: ['number', 'null'] }, payer: { type: ['string', 'null'] }, payee: { type: ['string', 'null'] },
    reasons: { type: 'array', items: { type: 'string' } }, tier: { type: 'string', enum: ['AUTO', 'APPROVE', 'HUMAN'] }, tier_basis: { type: 'string' },
    rules_cited: { type: 'array', items: { type: 'string' } }, kb_silent: { type: 'array', items: { type: 'string' } },
    confidence: { type: 'integer', enum: [1, 2, 3] }, note: { type: ['string', 'null'] },
  },
  required: ['case_id', 'kb_type', 'playbook', 'steps', 'outcome', 'amount_sgd', 'reasons', 'tier', 'tier_basis', 'rules_cited', 'kb_silent', 'confidence'],
}

const applyPrompt = (cid) => `You decide one dispute case using only a knowledge base (KB), the way the future dispute agent will use it. You did not build the KB. You only apply it; you never edit it. Every step must cite a KB rule ID and the case evidence it used.

${READONLY}

Read only:
- the KB: ${REPO}/kb/taxonomy.yaml, ontology.yaml, rules.yaml, reference_data.yaml, playbooks.yaml
- the case ${REPO}/validation/V4_e2e/cases/${cid}.json
Do NOT open anything else: not the Ryde policy pack, not validation/V4_e2e/4*.jsonl, not validation/build_checks, not validation/V5_scorecard, not docs/, not kb/open_items.yaml, not kb/tools, not kb/out, and do not run git log or git diff. The project's CLAUDE.md mentions a fix list; do not open it.

1. Classify the case with the taxonomy and the classification rules (CLS-*), and find its playbook (playbooks.yaml; taxonomy entries name their playbook or scope).
2. Follow the playbook's steps. At each step apply the rule it names to the evidence in the case file, using parameter values from reference_data.yaml (a case that carries its own policy object uses it, as the META rules say).
3. Decide the outcome with the KB's outcome vocabulary (TX-OUTCOME), the remedy amount, payer and payee, the reason code(s) (TX-REASON), and the autonomy tier (AUTO, APPROVE or HUMAN) under the AUTH rules.
4. Use only what the KB says. Where the KB is silent or ambiguous for something the case needs, record it in kb_silent and follow the KB's own fallback rule if it has one (for example its rule for policy gaps). Do not fill gaps from your own knowledge of Ryde.

Return the decision for ${cid} as structured output.`

const FINDINGS_SCHEMA = {
  type: 'object',
  properties: {
    dimension: { type: 'string' },
    checked_ok: { type: 'array', items: { type: 'string' }, description: 'what you checked and found correct, one line each' },
    findings: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, severity: { type: 'string', enum: ['CRITICAL', 'MAJOR', 'MINOR'] },
      file: { type: 'string' }, line: { type: 'integer' }, claim: { type: 'string' },
      evidence: { type: 'string', description: 'verbatim quote(s) from the file(s) or command output that show the problem' },
      failure_scenario: { type: 'string', description: 'concrete input or case and the wrong result it produces' },
      suggested_fix: { type: 'string' } },
      required: ['id', 'severity', 'file', 'claim', 'evidence', 'failure_scenario', 'suggested_fix'] } },
  },
  required: ['dimension', 'checked_ok', 'findings'],
}

const CONTEXT = `Context. ${REPO} is FairRyde's knowledge base (KB) for ride-hailing dispute resolution. Step ${STEP} changed it; see the change with: cd ${REPO} && git diff ${A.base} ${A.head} (and git log --oneline ${A.base}..${A.head}). This is review round ${ROUND} of at most two.${A.prior ? ` The earlier round's findings and how each was handled are in ${A.prior}.` : ''}
What the step had to do:
${A.task || '(see docs/NEXT_STEPS.md)'}
Project rules that apply (CLAUDE.md): every rule element needs a source or an open FairRyde label; a rule's credibility is its weakest essential element and a Ryde condition extended by FairRyde is D; docs and messages use no em dashes or en dashes and American spelling; names, plates, phone numbers and account IDs never appear in new test data. The build (python3 kb/build_kb.py --no-xlsx) must end ERROR 0 | WARN 0.
${SEVERITY}
Report only real problems you can show with evidence. Do not report style preferences as MAJOR. If you find nothing wrong in an area, say so in checked_ok.`

const DIMENSIONS = [
  { key: 'fidelity', prompt: `Dimension: FIX FIDELITY AND SCOPE. Check that the change does everything the step asked, exactly as the owner decided, and nothing else: compare each changed rule card with its version at ${A.base} (git show ${A.base}:kb/rules.yaml) and say whether any rule's meaning changed beyond what the task covers. Check that the self-tests in kb/tools/selftest.py really test the new behavior (and would fail without it). Run python3 kb/build_kb.py --no-xlsx, python3 kb/tools/selftest.py and python3 validation/tools/rerun_engine.py ${SCRATCH}rerun.json E01 E02 E03 E04 and report the result lines. ${FOCUS.fidelity || ''}` },
  { key: 'grounding', prompt: `Dimension: SOURCE GROUNDING AND CREDIBILITY of every new or changed rule element. For each: does it have a source or an explicit FairRyde label (or a recorded owner decision in kb/open_items.yaml); does every quoted source say what the rule uses it for (Ryde articles are in kb/sources/ryde_policy_corpus.json under articles, keyed by id, with body_text; the Terms of Use under terms_of_use); is the rule's credibility its weakest essential element under the credibility_principle at the top of kb/rules.yaml; is anything overgeneralized beyond its source or missing an exception the source states; do the zh texts say the same as the English (meaning, not style). ${FOCUS.grounding || ''}` },
  { key: 'adversarial', prompt: `Dimension: ADVERSARIAL TEST OF THE CHANGED LOGIC. Try hard to break what the step changed, in kb/tools/engine_noshow.py and in the rule text as an LLM would apply it. Write scratch scripts under ${SCRATCH} that import the engine (sys.path.insert(0, '${REPO}/kb/tools'); from kbload import KB; import engine_noshow as E; the self-test baseline is selftest.clean on copy.deepcopy(KB().disp002); see kb/tools/selftest.py for how variants change a case). Build at least 30 realistic edge cases aimed at the change (window edges, missing or reordered events, mixed evidence, advance bookings, organizer and Ryde profiles) and run the full engine (E.run) on each. The unsafe error is a case that should go to a person (escalation or approval) but is decided automatically (tier AUTO), or a fee upheld that the rules waive; report each with the exact case change, outcome and tier. Safe-direction errors that send routine cases to a person matter less; report the frequent ones. Severity: an unsafe error in a common pattern is CRITICAL, in a rare pattern MAJOR. ${FOCUS.adversarial || ''}` },
  { key: 'consistency', prompt: `Dimension: CONSISTENCY ACROSS FILES AND PARTY-FACING TEXT. Check that every consumer of the changed rules agrees with them: kb/tools/explain.py (run E.run and explain.noshow on the self-test variants the step added and on validation/V4_e2e/cases/E01.json and E03.json, and read every sentence of the rider and driver explanations against the case facts: nothing false, nothing misleading), kb/tools/make_xlsx.py and kb/tools/report_md.py, kb/annotation_schema.yaml, kb/playbooks.yaml, kb/taxonomy.yaml, kb/ontology.yaml, kb/scope.yaml, kb/open_items.yaml (are the decisions recorded accurately and consistently with the rules?) and docs/NEXT_STEPS.md. Grep kb/ (excluding kb/sources) for wording that still describes the old behavior. Check the changed text for em dashes or en dashes and British spellings, and new test data for names, plates, phone numbers or account IDs. ${FOCUS.consistency || ''}` },
]

const VERDICT_SCHEMA = {
  type: 'object',
  properties: { verdicts: { type: 'array', items: { type: 'object', properties: {
    id: { type: 'string' }, verdict: { type: 'string', enum: ['CONFIRMED', 'REFUTED', 'UNCERTAIN'] },
    severity_after_check: { type: 'string', enum: ['CRITICAL', 'MAJOR', 'MINOR', 'NONE'] },
    reason: { type: 'string', description: 'what you re-read or re-ran, with the evidence' } },
    required: ['id', 'verdict', 'severity_after_check', 'reason'] } } },
  required: ['verdicts'],
}

phase('Apply')
const applied = parallel((A.apply_cases || []).map(cid => () =>
  agent(applyPrompt(cid), { label: `apply:${cid}`, phase: 'Apply', schema: APPLY_SCHEMA })))

const reviewed = pipeline(
  DIMENSIONS,
  d => agent(`${CONTEXT}\n\n${READONLY}\n\n${d.prompt}`, { label: `review:${d.key}`, phase: 'Review', schema: FINDINGS_SCHEMA }),
  (rev, d) => {
    if (!rev || !rev.findings || rev.findings.length === 0) return { dimension: d.key, review: rev, verify: { verdicts: [] } }
    return agent(`${CONTEXT}\n\n${READONLY}\n\nYou are a skeptic. Another reviewer reported the findings below about step ${STEP} (dimension: ${d.key}). For EACH finding, try to refute it: re-read the cited files and lines yourself, re-run any command or scratch script needed (scratch only under ${SCRATCH}), and check whether the failure scenario really happens and whether the severity is right under the definitions above. Default to REFUTED if the evidence does not hold up; CONFIRMED only if you reproduced it or read it yourself; UNCERTAIN if it depends on a judgment the KB owner must make. Give severity_after_check (NONE if refuted).\n\nFindings:\n${JSON.stringify(rev.findings, null, 1)}`,
      { label: `verify:${d.key}`, phase: 'Verify', schema: VERDICT_SCHEMA })
      .then(v => ({ dimension: d.key, review: rev, verify: v }))
  },
)

const [applyResults, reviewResults] = await Promise.all([applied, reviewed])
return { step: STEP, round: ROUND, apply: applyResults, reviews: reviewResults }
