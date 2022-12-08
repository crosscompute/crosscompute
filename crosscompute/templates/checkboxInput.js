GET_DATA_BY_VIEW_NAME['$view_name'] = x => {
  const vs = [];
  for (const e of x.querySelectorAll('input:checked')) {
    vs.push(e.value);
  }
  return { value: vs.join('\n') };
};
