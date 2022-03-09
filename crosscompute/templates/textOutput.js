function refreshText_$element_id() {
  refreshString('$element_id', 'textContent', '$data_uri');
}
registerElement('$variable_id', function () {
  refreshText_$element_id();
});
refreshText_$element_id();
