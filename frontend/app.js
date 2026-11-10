import {createClient} from 'genlayer-js';
import {studionet} from 'genlayer-js/chains';
import {TransactionHashVariant} from 'genlayer-js/types';
import {explorer, hashPattern, idPattern, receiptState, trustedEvidence} from './chain.mjs';
import {mtaFeed, matchOutages} from "./mta.mjs";
import config from './config.json';

const byId = id => document.getElementById(id);
const client = createClient({chain: studionet});
const studio = 'https://studio.genlayer.com/?import-contract=' + config.address;
byId('studio').href = byId('write-studio').href = studio;
byId('contract').href = explorer + '/address/' + config.address;
let caseRequest = 0;
let txRequest = 0;

function add(parent, type, text, css) {
  const node = document.createElement(type);
  if (text) node.textContent = text;
  if (css) node.className = css;
  parent.append(node);
  return node;
}

const reasons = {
  COMPLETE_MAPS_CONFLICT: 'Published complete maps disagree about routes to this platform.',
  VERIFIED_STEP_FREE_ROUTE: 'The evidence shows a continuous step-free route for the full window.',
  COMPLETE_MAP_HAS_NO_USABLE_ROUTE: 'The complete map shows no step-free route or each mapped route has a confirmed closure.',
  ROUTE_OR_STATUS_COVERAGE_INCOMPLETE: 'The evidence does not establish whether another route was usable.',
};

function renderCase(record) {
  const output = byId('case-output');
  const header = add(output, 'div', '', 'record');
  add(header, 'h3', `${record.claim.station} · ${record.claim.platform}`);
  add(header, 'p', `Entrance scope ${record.claim.entrance} · ${record.claim.from} to ${record.claim.to}`);
  add(header, 'span', record.phase.replaceAll('_', ' '), 'tag neutral');
  if (record.synthetic) add(header, 'p', 'Synthetic publisher evidence. Station and outages are fictional.');
  if (record.phase === 'REVIEWED') add(header, 'p', 'Challenge deadline ' + new Date(record.challenge_until * 1000).toISOString());
  for (const decision of record.history) {
    const row = add(output, 'article', '', 'record');
    add(row, 'h3', decision.round === 'INITIAL' ? 'Initial review' : 'Challenge review');
    add(row, 'span', decision.verdict, 'tag ' + (decision.verdict === 'ACCESSIBLE' ? 'green' : 'orange'));
    add(row, 'p', reasons[decision.reason] ?? decision.reason);
    if (decision.routes.length) {
      const list = add(row, 'ul', '', 'route-list');
      for (const route of decision.routes) {
        const assets = Object.entries(route.assets).map(([name, status]) => `${name} ${status.toLowerCase()}`).join(', ');
        add(list, 'li', `${route.entrance} · ${route.state.toLowerCase()} · ${assets}`);
      }
    }
    for (const [index, ref] of decision.evidence.entries()) {
      const line = add(row, 'p', '');
      if (trustedEvidence(ref.url, config.repository)) {
        const link = add(line, 'a', `Evidence ${index + 1} ↗`);
        Object.assign(link, {href:ref.url, target:'_blank', rel:'noopener'});
      } else line.textContent = `Evidence ${index + 1}`;
      line.append(' · ' + ref.validity.replaceAll('_', ' '));
      add(row, 'p', ref.sha256, 'fingerprint');
    }
    add(row, 'p', 'Decision SHA-256 ' + decision.hash, 'fingerprint');
  }
}

async function readCase() {
  const id = byId('case-id').value.trim();
  if (!idPattern.test(id)) return;
  const request = ++caseRequest;
  byId('case-output').replaceChildren();
  byId('case-status').textContent = 'Reading finalized Studionet state…';
  try {
    const raw = await client.readContract({
      address:config.address, functionName:'get_case', args:[id],
      transactionHashVariant:TransactionHashVariant.LATEST_FINAL,
    });
    if (request !== caseRequest) return;
    if (!raw) {
      byId('case-status').textContent = 'No finalized state for this case ID.';
      return;
    }
    const record = JSON.parse(raw);
    if (record.id !== id) throw new Error('Case ID mismatch');
    renderCase(record);
    byId('case-status').textContent = 'Read directly from finalized Studionet state.';
  } catch (error) {
    if (request === caseRequest) byId('case-status').textContent = 'Could not read the case. ' + (error.shortMessage ?? error.message);
  }
}

async function track() {
  const hash = byId('hash').value.trim();
  if (!hashPattern.test(hash)) return;
  const request = ++txRequest;
  const status = byId('tx-status');
  byId('tx-link').href = explorer + '/tx/' + hash;
  byId('tx-link').hidden = false;
  status.textContent = 'Looking up the transaction…';
  for (let attempt = 0; attempt < 36 && request === txRequest; attempt++) {
    try {
      const tx = await client.getTransaction({hash});
      if (request !== txRequest) return;
      const recipient = tx?.to_address ?? tx?.recipient;
      if (recipient && recipient.toLowerCase() !== config.address.toLowerCase() && hash.toLowerCase() !== config.transactions.Deploy) {
        status.textContent = 'This transaction targets a different contract.';
        return;
      }
      const state = receiptState(tx);
      status.textContent = state.label;
      if (state.terminal) {
        if (state.success && idPattern.test(byId('case-id').value)) void readCase();
        return;
      }
    } catch {
      if (request !== txRequest) return;
      status.textContent = 'Receipt temporarily unavailable. Retrying…';
    }
    await new Promise(resolve => setTimeout(resolve, 5000));
  }
  if (request === txRequest) status.textContent += ' Polling paused. Track again to resume.';
}

const initial = [
  ['Station ID', 'harbor-square'], ['Entrance ID or any', 'any'], ['Platform or direction ID', 'northbound'],
  ['Start UTC', '2026-10-20T08:15:00Z'], ['End UTC', '2026-10-20T08:45:00Z'],
  ['Evidence URL', config.initialUrl], ['Evidence SHA-256', config.initialSha], ['Unique reference', ''],
];

function writeFields() {
  const caseField = ['Case ID', byId('case-id').value];
  const method = byId('method').value;
  const fields = method === 'open_case' ? initial : method === 'challenge'
    ? [caseField, ['Evidence URL', config.challengeUrl], ['Evidence SHA-256', config.challengeSha]]
    : [caseField];
  const target = byId('write-inputs');
  target.replaceChildren();
  byId('write-status').textContent = '';
  fields.forEach(([name,value], index) => {
    const id = 'arg-' + index;
    add(target,'label',name).htmlFor = id;
    const input = add(target,'input');
    Object.assign(input,{id,value,spellcheck:false,autocomplete:'off'});
  });
}

byId('case-form').addEventListener('submit', event => {event.preventDefault(); void readCase();});
byId('tx-form').addEventListener('submit', event => {event.preventDefault(); void track();});
byId('demo').addEventListener('click', () => {
  byId('case-id').value = config.demoCase;
  writeFields();
  void readCase();
});
for (const [label, hash] of Object.entries(config.transactions)) {
  const button = add(byId('demo-transactions'), 'button', label);
  button.type = 'button';
  button.addEventListener('click', () => {byId('hash').value = hash; void track();});
}
byId('method').addEventListener('change', writeFields);
byId('copy').addEventListener('click', async () => {
  const args = Array.from(byId('write-inputs').querySelectorAll('input'), input => input.value.trim());
  const status = byId('write-status');
  if (args.some(value => !value)) {
    status.textContent = 'Complete every argument before copying.';
    return;
  }
  try {
    await navigator.clipboard.writeText(JSON.stringify(args));
    status.textContent = 'Copied as an ordered JSON array. Match these values to the method fields in Studio.';
  } catch {
    status.textContent = 'Clipboard unavailable. Copy each field into the matching Studio field.';
  }
});
writeFields();

let mtaRequest = 0;
byId('mta-form').addEventListener('submit', async event => {
  event.preventDefault();
  const request = ++mtaRequest;
  const query = byId('mta-query').value;
  const status = byId('mta-status');
  const results = byId('mta-results');
  status.textContent = 'Fetching the MTA feed…';
  results.replaceChildren();
  try {
    const response = await fetch(mtaFeed, {signal:AbortSignal.timeout(12000)});
    if (!response.ok) throw new Error('MTA feed unavailable');
    const matches = matchOutages(await response.json(), query);
    if (request !== mtaRequest) return;
    status.textContent = matches.length
      ? `Showing ${Math.min(12, matches.length)} of ${matches.length} reported outages. Retrieved ${new Date().toISOString()}.`
      : 'The current feed returned no matching outage reports.';
    for (const outage of matches.slice(0, 12)) {
      const route = typeof outage.serving === 'string' ? ' · ' + outage.serving : '';
      add(results, 'li', `${outage.station} · ${outage.equipment}${route}`);
    }
  } catch {
    if (request === mtaRequest) status.textContent = 'The live feed is unavailable. Use the official MTA status link.';
  }
});
