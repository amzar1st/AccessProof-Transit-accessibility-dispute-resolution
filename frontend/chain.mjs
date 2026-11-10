export const hashPattern = /^0x[0-9a-f]{64}$/i;
export const idPattern = /^[0-9a-f]{64}$/;
export const explorer = 'https://explorer-studio.genlayer.com';

export function receiptState(tx) {
  const status = tx?.statusName ?? (typeof tx?.status === 'string' ? tx.status : '');
  if (!status) return {label: 'Waiting for Studionet to index this transaction.', terminal: false};
  if (status === 'FINALIZED') {
    const leader = tx.consensus_data?.leader_receipt;
    const execution = tx.txExecutionResultName ?? (Array.isArray(leader) ? leader[0] : leader)?.execution_result;
    if (['FINISHED_WITH_RETURN', 'SUCCESS'].includes(execution)) return {label: 'Finalized · execution succeeded', terminal: true, success: true};
    if (['FINISHED_WITH_ERROR', 'ERROR'].includes(execution)) return {label: 'Finalized · execution failed', terminal: true, success: false};
    return {label: 'Finalized · execution result unavailable', terminal: true};
  }
  if (['CANCELED', 'CANCELLED', 'UNDETERMINED'].includes(status)) return {label: status, terminal: true, success: false};
  return {label: `Pending finalization · ${status.replaceAll('_', ' ')}`, terminal: false};
}

export function trustedEvidence(url, repository) {
  const prefix = 'https://raw.githubusercontent.com/' + repository + '/';
  if (typeof url !== 'string' || url.length > 320 || !url.startsWith(prefix)) return false;
  const suffix = url.slice(prefix.length);
  return /^[a-f0-9]{40}\/[A-Za-z0-9_./-]+\.json$/.test(suffix)
    && suffix.split('/').every(part => part && part !== '.' && part !== '..');
}
