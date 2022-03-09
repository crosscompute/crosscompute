function refreshMarkdown_$element_id() {
  refreshMarkdownOutput('$element_id', '$data_uri');
}
registerElement('$variable_id', function () {
  refreshMarkdown_$element_id();
});
refreshMarkdown_$element_id();
