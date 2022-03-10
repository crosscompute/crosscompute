async function refreshString(
    elementId, elementAttribute, dataUri, formatText) {
  const response = await fetch(dataUri);
  const { status } = response;
  if (status != 200) {
    throw { status };
  }
  let text = await response.text();
  if (formatText) {
    text = formatText(text);
  }
  const element = document.getElementById(elementId);
  element[elementAttribute] = text;
  return element;
}
