function refreshTable_$element_id() {
  refreshTableOutput('$element_id', '$data_uri');
}
registerElement('$variable_id', function () {
  refreshTable_$element_id();
});
refreshTable_$element_id();
