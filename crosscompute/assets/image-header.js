async function refreshImage(elementId, dataUri) {
  const l = document.getElementById(elementId);
  l.src = dataUri + '?' + Date.now();
}
