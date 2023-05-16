async function refreshText(elementId, dataUri, dataValue) {
  await refreshString(elementId, 'textContent', dataUri, dataValue);
}
