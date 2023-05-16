async function refreshMarkdown(elementId, dataUri, dataValue) {
  await refreshString(elementId, 'innerHTML', dataUri, dataValue, formatMarkdown);
}
function formatMarkdown(text) {
  let h = marked.parse(text).trim();
  if (!h.includes('</p>\n<p>')) {
    h = h.replace(/^<p>/, '').replace(/<\/p>$/, '');
  }
  return h;
}
