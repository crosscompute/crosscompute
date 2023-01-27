async function refreshString(elementId, elementAttribute, dataUri, formatText) {
  let x;
  try {
    const r = await fetch(dataUri);
    x = await r.text();
  } catch {
    return;
  }
  if (formatText) {
    x = formatText(x);
  }
  const l = document.getElementById(elementId);
  l[elementAttribute] = x;
}
