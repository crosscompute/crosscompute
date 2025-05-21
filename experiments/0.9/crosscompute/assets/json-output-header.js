async function refreshJson(variableId, dataUri, dataValue) {
  let x = dataValue;
  if (x === undefined) {
    try {
      const r = await fetch(dataUri);
      x = await r.json();
    } catch {
      return;
    }
  }
  variables[variableId] = x;
}
