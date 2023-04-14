// TODO: Add progress indicator
for (var l of document.getElementsByClassName('_$view_name')) {
  l.addEventListener('change', e => {
    const l = e.target, xhr = new XMLHttpRequest(), fd = new FormData();
    xhr.upload.addEventListener('progress', e => {
      if (e.lengthComputable) {
        console.log('uploaded ' + e.loaded + ' of ' + e.total);
      }
    });
    xhr.open('POST', '$files_uri');
    xhr.onreadystatechange = () => {
      if (xhr.readyState === 4 && xhr.status === 200) {
        l.dataset.json = xhr.responseText;
      }
    }
    for (const f of l.files) {
      fd.append('files', f);
    }
    xhr.send(fd);
  });
}
GET_DATA_BY_VIEW_NAME['$view_name'] = x => {
  const { json } = x.dataset;
  return json ? JSON.parse(json) : {};
};
