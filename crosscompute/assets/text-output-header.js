async function refreshText(elementId, dataUri) {
  await refreshString(elementId, 'textContent', dataUri);
}
