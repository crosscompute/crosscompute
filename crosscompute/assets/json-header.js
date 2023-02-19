async function refreshJson(variableId, dataUri) {
  try {
    const r = await fetch(dataUri);
    variables[variableId] = await r.json();
  } catch {
  }
}
