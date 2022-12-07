GET_DATA_BY_VIEW_NAME['$view_name'] = x => {
  const values = [], selections = x.querySelectorAll('input:checked');
  for (const selection of selections) {
    values.push(selection.value);
  }
  return values.join('\n');
};
