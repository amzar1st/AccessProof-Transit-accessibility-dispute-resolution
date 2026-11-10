import assert from 'node:assert/strict';
import test from 'node:test';
import {receiptState, trustedEvidence, idPattern, hashPattern} from '../frontend/chain.mjs';

test('keeps accepted and unindexed transactions pending', () => {
  assert.equal(receiptState(null).terminal, false);
  assert.equal(receiptState({statusName:'ACCEPTED'}).terminal, false);
  assert.match(receiptState({statusName:'COMMITTING'}).label, /COMMITTING/);
});

test('separates finalized execution success from execution errors', () => {
  const result = execution_result => receiptState({
    statusName:'FINALIZED', consensus_data:{leader_receipt:[{execution_result}]},
  });
  assert.equal(result('FINISHED_WITH_RETURN').success, true);
  assert.equal(result('FINISHED_WITH_ERROR').success, false);
  assert.equal(result('UNKNOWN').success, undefined);
  assert.equal(receiptState({statusName:'UNDETERMINED'}).terminal, true);
});

test('checks transaction and case identifier format', () => {
  const digest = 'a'.repeat(64);
  assert.ok(idPattern.test(digest));
  assert.ok(hashPattern.test('0x' + digest));
  assert.ok(!idPattern.test('0x' + digest));
});

test('links only to pinned evidence under the configured publisher', () => {
  const repo = 'owner/repo';
  const root = 'https://raw.githubusercontent.com/owner/repo/' + 'a'.repeat(40) + '/';
  assert.ok(trustedEvidence(root + 'evidence/station.json', repo));
  for (const suffix of ['../station.json', 'station.json?bad=1', '//station.json', 'station.html']) {
    assert.ok(!trustedEvidence(root + suffix, repo));
  }
  assert.ok(!trustedEvidence(root + 'station.json', 'other/repo'));
});

test('shows only active accessibility elevator reports from the agency feed', async () => {
  const {matchOutages} = await import('../frontend/mta.mjs');
  const current = {station:'175 St',equipment:'EL124',equipmenttype:'EL',ADA:'Y',isupcomingoutage:'N'};
  const input = [current, {...current, isupcomingoutage:'Y'}, {...current, ADA:'N'}, {...current,equipmenttype:'ES'}, null];
  assert.deepEqual(matchOutages(input, ' el124 '), [current]);
  assert.deepEqual(matchOutages(input, '175 ST'), [current]);
  assert.deepEqual(matchOutages(input, 'other'), []);
  assert.throws(() => matchOutages({}, ''), /Unexpected MTA feed/);
});
