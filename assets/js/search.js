// 首頁搜尋：依卡片的 data-search（球員英文名、球隊縮寫、球隊中文名、位置）篩選。
// 新增球員時不需要修改這個檔案，只要卡片有 data-search 屬性即可。
(function () {
  var input = document.getElementById('search');
  var empty = document.getElementById('empty');
  if (!input) return;

  input.addEventListener('input', function () {
    var q = input.value.trim().toLowerCase();
    var shown = 0;
    document.querySelectorAll('.group').forEach(function (group) {
      var visible = 0;
      group.querySelectorAll('.mini').forEach(function (card) {
        var hit = !q || card.dataset.search.indexOf(q) !== -1;
        card.hidden = !hit;
        if (hit) visible++;
      });
      group.hidden = visible === 0;
      shown += visible;
    });
    empty.style.display = shown ? 'none' : 'block';
  });
})();
