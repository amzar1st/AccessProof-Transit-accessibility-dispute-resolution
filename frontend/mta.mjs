export const mtaFeed = 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fnyct_ene.json';

export function matchOutages(rows, search) {
  if (!Array.isArray(rows)) throw new Error('Unexpected MTA feed format');
  const query = search.trim().toLowerCase();
  return rows.filter(row => row?.equipmenttype === 'EL' && row.ADA === 'Y'
    && row.isupcomingoutage === 'N' && typeof row.station === 'string'
    && typeof row.equipment === 'string'
    && [row.station, row.equipment].some(value => value.toLowerCase().includes(query)));
}
