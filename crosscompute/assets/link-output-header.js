async function refreshLink(id, text) {
  const l = document.getElementById(id);
  l.text = `${text} updated ${new Date().toString()}`;
  return l;
}
