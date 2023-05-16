async function refreshString(elementId, elementAttribute, dataUri, dataValue, formatText) {
  let x = dataValue;
  if (dataValue === undefined) {
    try {
      const r = await fetch(dataUri), { status } = r;
      if (status != 200) return;
      x = await r.text();
    } catch {
      return;
    }
  }
  if (formatText) {
    x = formatText(x);
  }
  const l = document.getElementById(elementId);
  l[elementAttribute] = x;
  return l;
}
