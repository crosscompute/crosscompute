GET_DATA_BY_VIEW_NAME['$view_name'] = x => {
  const vs = [];
  for (const l of x.querySelectorAll('input:checked')) {
    vs.push(l.value);
  }
  return { value: vs.join('\n') };
};
