async function refreshLink(id, dataConfiguration) {
  const l = document.getElementById(id);
  const fileName = dataConfiguration?.['file-name'];
  if (fileName !== undefined) {
    l.download = fileName;
  }
  const linkText = dataConfiguration?.['link-text'];
  if (linkText !== undefined) {
    l.dataset.text = linkText;
  }
  l.text = l.dataset.text + ' updated ' + new Date().toString();
  return l;
}
