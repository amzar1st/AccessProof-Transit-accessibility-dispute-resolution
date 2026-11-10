import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {createClient} from 'genlayer-js';
import {studionet} from 'genlayer-js/chains';
import {TransactionHashVariant} from 'genlayer-js/types';
import {receiptState} from '../frontend/chain.mjs';

const file = path => new URL(path, import.meta.url);
const config = JSON.parse(await readFile(file('../frontend/config.json')));
const client = createClient({chain:studionet});
const digest = data => createHash('sha256').update(data).digest('hex');
const positional = (method, params) => client.request({method, params});
assert.equal(studionet.id, 61999);

const [source, code, schema, raw, policy, ...receipts] = await Promise.all([
  readFile(file('../contracts/access_proof.py')),
  positional('gen_getContractCode', [config.address]),
  positional('gen_getContractSchema', [config.address]),
  client.readContract({address:config.address, functionName:'get_case', args:[config.demoCase],
    transactionHashVariant:TransactionHashVariant.LATEST_FINAL}),
  client.readContract({address:config.address, functionName:'get_policy', args:[],
    transactionHashVariant:TransactionHashVariant.LATEST_FINAL}),
  ...Object.values(config.transactions).map(hash => client.getTransaction({hash})),
]);
assert.equal(digest(Buffer.from(code,'base64')), digest(source));
for (const name of ['open_case','review','challenge','finalize','get_case','get_policy']) {
  assert.ok(Object.hasOwn(schema.methods, name), 'Schema missing ' + name);
}
assert.equal(JSON.parse(policy).synthetic, true);
const state = JSON.parse(raw);
assert.equal(state.id, config.demoCase);
assert.equal(state.phase, 'FINALIZED');
assert.deepEqual(state.history.map(round => round.verdict), ['INCONCLUSIVE', 'ACCESSIBLE']);
assert.equal(state.history[1].previous, state.history[0].hash);
assert.ok(state.history[1].routes.some(route => route.entrance === 'west' && route.state === 'USABLE'));
assert.ok(state.history[1].routes.some(route => route.entrance === 'main' && route.state === 'BLOCKED'));
assert.ok(state.history.every(round => round.evidence.every(ref => ref.validity === 'VERIFIED')));
assert.deepEqual(state.evidence.map(ref => ref.sha256), [config.initialSha, config.challengeSha]);

for (const [index, label] of Object.keys(config.transactions).entries()) {
  const receipt = receipts[index];
  const outcome = receiptState(receipt);
  assert.ok(outcome.terminal, label + ' receipt is pending');
  assert.equal(outcome.success, label !== 'Rejected replay', label + ' execution outcome');
  if (label !== 'Deploy') assert.equal(receipt.to_address.toLowerCase(), config.address.toLowerCase());
  console.log(label, outcome.label, config.transactions[label]);
}
console.log('Source SHA-256', digest(source));
console.log('Finalized case', state.id, state.history.map(round => [round.verdict, round.hash]));
