function refreshTable_$element_id() {
  refreshTable('$element_id', '$data_uri');
}
registerFunction('$variable_id', refreshTable_$element_id);
refreshTable_$element_id();
