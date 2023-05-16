registerFunction('$variable_id', async function({v}) {
  await refreshText('$element_id', '$data_uri', v);
});
refreshVariable('$variable_id');
