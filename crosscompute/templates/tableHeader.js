async function refreshTableOutput(elementId, dataUri) {
  const response = await fetch(dataUri);
  const d = await response.json();
  const index = d.index;
  const columns = d.columns, columnCount = columns.length;
  const rows = d.data, rowCount = rows.length;
  const nodes = document.getElementById(elementId).children;
  const thead = nodes[0], tbody = nodes[1];
  thead.textContent = '';
  tbody.textContent = '';
  let tr = document.createElement('tr');
  if (index) {
    const th = document.createElement('th');
    tr.append(th);
  }
  for (let i = 0; i < columnCount; i++) {
    const column = columns[i];
    const th = document.createElement('th');
    th.innerText = column;
    tr.append(th);
  }
  thead.append(tr);
  for (let i = 0; i < rowCount; i++) {
    const row = rows[i];
    tr = document.createElement('tr');
    if (index) {
      const th = document.createElement('th');
      th.innerText = index[i];
      tr.append(th);
    }
    for (let j = 0; j < columnCount; j++) {
      const td = document.createElement('td');
      td.innerText = row[j];
      tr.append(td);
    }
    tbody.append(tr);
  }
}
