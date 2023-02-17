async function refreshJson(elementId, dataUri) {
  try {
    const r = await fetch(dataUri);
    variables[elementId] = await r.json();
  } catch {
  }
}
