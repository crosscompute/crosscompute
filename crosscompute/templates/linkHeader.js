function refreshLink(elementId, text) {
  const element = document.getElementById(elementId);
  element.text = `${text} updated ${new Date().toString()}`;
  return element;
}
