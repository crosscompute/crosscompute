async function refreshTable(elementId, dataUri) {
  let d;
  try {
    const r = await fetch(dataUri);
    d = await r.json();
  } catch {
    return;
  }
  const { index, columns, data: rows } = d;
  const columnCount = columns.length, rowCount = rows.length;
  const [thead, tbody] = document.getElementById(elementId).children;
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
