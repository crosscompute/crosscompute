function refreshLink(id, text) {
  const element = document.getElementById(id);
  element.text = `${text} updated ${new Date().toString()}`;
  return element;
}
