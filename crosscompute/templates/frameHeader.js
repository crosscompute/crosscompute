async function refreshFrame(elementId, dataUri) {
  try {
    const r = await fetch(dataUri), e = document.getElementById(elementId);
    e.src = await r.text();
  } catch {
  }
}
