async function refreshString(
    elementId, elementAttribute, dataUri, formatText) {
  const response = await fetch(dataUri);
  let text = await response.text();
  if (formatText) {
    text = formatText(text);
  }
  const element = document.getElementById(elementId);
  element[elementAttribute] = text;
  return element;
}
