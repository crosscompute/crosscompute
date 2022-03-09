async function refreshTextInput(elementId, dataUri) {
  const element = await refreshString(elementId, 'value', dataUri);
  element.disabled = false;
}
