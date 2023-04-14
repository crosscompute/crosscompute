async function refreshMarkdown(elementId, dataUri) {
  await refreshString(elementId, 'innerHTML', dataUri, formatMarkdown);
}
function formatMarkdown(text) {
  let h = marked.parse(text).trim();
  if (!h.includes('</p>\n<p>')) {
    h = h.replace(/^<p>/, '').replace(/<\/p>$/, '');
  }
  return h;
}
