function refreshMarkdown_$element_id() {
  refreshMarkdown('$element_id', '$data_uri');
}
registerElement('$variable_id', function() {
  refreshMarkdown_$element_id();
});
try {
  refreshMarkdown_$element_id();
} catch {
}
