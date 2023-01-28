function refreshTable_$element_id() {
  refreshTable('$element_id', '$data_uri');
}
registerElement('$variable_id', function() {
  refreshTable_$element_id();
});
try {
  refreshTable_$element_id();
} catch {
}
