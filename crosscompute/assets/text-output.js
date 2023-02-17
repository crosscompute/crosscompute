async function refreshText_$element_id() {
  await refreshText('$element_id', '$data_uri');
}
registerFunction('$variable_id', refreshText_$element_id);
refreshText_$element_id();
