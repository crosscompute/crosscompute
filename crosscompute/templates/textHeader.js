async function refreshTextInput(elementId, dataUri) {
  try {
    const element = await refreshString(elementId, 'value', dataUri);
    element.disabled = false;
  } catch {
  }
}
