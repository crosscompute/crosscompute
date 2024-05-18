registerFunction('$variable_id', async function({v}) {
  await refreshJson('$variable_id', '$data_uri', v);
});
refreshVariable('$variable_id', $value);
