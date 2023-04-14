async function refreshFrame(elementId, dataUri) {
  try {
    const r = await fetch(dataUri), l = document.getElementById(elementId);
    l.src = await r.text();
  } catch {
  }
}
