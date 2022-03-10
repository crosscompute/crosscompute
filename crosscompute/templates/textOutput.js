function refreshText_$element_id() {
  try {
    refreshString('$element_id', 'textContent', '$data_uri');
  } catch {
  }
}
registerElement('$variable_id', function () {
  refreshText_$element_id();
});
refreshText_$element_id();
