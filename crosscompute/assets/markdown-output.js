function refreshMarkdown_$element_id() {
  refreshMarkdown('$element_id', '$data_uri');
}
registerFunction('$variable_id', refreshMarkdown_$element_id);
refreshMarkdown_$element_id();
