// 深色／淺色模式切換。
// - 放在每一頁的 <head> 裡（不加 defer），這樣頁面畫出來之前就套用主題，不會先閃一下白色。
// - 預設跟隨系統設定；使用者按過按鈕後，選擇會記在 localStorage，之後每一頁都沿用。
// - 按鈕由這支程式自動加到 .site-bar 右側，頁面 HTML 不需要另外寫按鈕。
(function () {
  var KEY = 'mlb-notes-theme';
  var root = document.documentElement;
  var media = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;

  function saved() {
    try { return localStorage.getItem(KEY); } catch (e) { return null; }
  }
  function preferred() {
    return saved() || (media && media.matches ? 'dark' : 'light');
  }
  function apply(theme) {
    root.setAttribute('data-theme', theme);
    var btn = document.getElementById('theme-toggle');
    if (btn) {
      var dark = theme === 'dark';
      btn.textContent = dark ? '☀ 淺色' : '☾ 深色';
      btn.setAttribute('aria-label', dark ? '切換為淺色模式' : '切換為深色模式');
      btn.setAttribute('aria-pressed', String(dark));
    }
  }

  apply(preferred());

  // 使用者沒有手動選過時，系統切換深淺色也跟著變
  if (media && media.addEventListener) {
    media.addEventListener('change', function () { if (!saved()) apply(preferred()); });
  }

  document.addEventListener('DOMContentLoaded', function () {
    var bar = document.querySelector('.site-bar');
    if (!bar || document.getElementById('theme-toggle')) return;
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.id = 'theme-toggle';
    btn.className = 'theme-toggle';
    btn.addEventListener('click', function () {
      var next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      try { localStorage.setItem(KEY, next); } catch (e) { /* 無痕模式可能不能存，仍可切換 */ }
      apply(next);
    });
    bar.appendChild(btn);
    apply(root.getAttribute('data-theme') || preferred());
  });
})();
