async function refreshString(
    elementId, elementAttribute, dataUri, formatText) {
  const r = await fetch(dataUri), { status } = r;
  if (status != 200) {
    throw { status };
  }
  let x = await r.text();
  if (formatText) {
    x = formatText(x);
  }
  const e = document.getElementById(elementId);
  e[elementAttribute] = x;
  return e;
}
