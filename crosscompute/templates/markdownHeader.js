function formatMarkdown(text) {
  let html = marked.parse(text).trim();
  if (!html.includes('</p>\n<p>')) {
    html = html.replace(/^<p>/, '').replace(/<\/p>$/, '');
  }
  return html;
}
function refreshMarkdownOutput(elementId, dataUri) {
  try {
    refreshString(elementId, 'innerHTML', dataUri, formatMarkdown);
  } catch {
  }
}
