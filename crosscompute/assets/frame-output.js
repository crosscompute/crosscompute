registerFunction('$variable_id', async function({v}) {
  await refreshFrame('$element_id', v);
});
