/* Shankha Amrit — motion layer: progress bar, hero depth, embers, mandala, 3D story wheel, reveals, card tilt */
(function () {
  var doc = document.documentElement;
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var hero = document.querySelector('.hero');
  var mobile = window.matchMedia ? matchMedia('(max-width: 860px), (hover: none)') : { matches: false };
  var NS = 'http://www.w3.org/2000/svg';

  function el(tag, attrs, parent) {
    var e = document.createElementNS(NS, tag);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }

  /* progress bar + scroll cue */
  var bar = document.createElement('div');
  bar.className = 'fx-progress';
  document.body.appendChild(bar);
  if (hero) {
    var cue = document.createElement('div');
    cue.className = 'scroll-cue';
    cue.textContent = 'स्क्रॉल करें';
    hero.appendChild(cue);
  }

  /* golden mandala, drawn from rings of petals */
  var mandalaBox = document.querySelector('.mandala');
  if (mandalaBox) {
    var svg = el('svg', { viewBox: '-100 -100 200 200' }, mandalaBox);
    var g = el('g', { fill: 'none', stroke: '#e8b54a', 'stroke-width': '0.45' }, svg);
    var rings = [[8, 16, 12], [12, 30, 20], [16, 48, 28], [24, 68, 34], [32, 88, 22]];
    rings.forEach(function (r, ri) {
      var n = r[0], rad = r[1], len = r[2];
      for (var i = 0; i < n; i++) {
        var a = (360 / n) * i + (ri % 2 ? 180 / n : 0);
        var w = len * (ri === 4 ? 0.22 : 0.42);
        var p = 'M0,' + (-rad + len) + ' C' + w + ',' + (-rad + len * 0.55) + ' ' + w * 0.6 + ',' + (-rad + len * 0.15) + ' 0,' + (-rad) +
                ' C' + (-w * 0.6) + ',' + (-rad + len * 0.15) + ' ' + (-w) + ',' + (-rad + len * 0.55) + ' 0,' + (-rad + len) + 'Z';
        el('path', { d: p, transform: 'rotate(' + a + ')' }, g);
      }
      el('circle', { r: rad - len, opacity: '0.6' }, g);
    });
    el('circle', { r: 92, 'stroke-dasharray': '1 3' }, g);
    el('circle', { r: 96 }, g);
    el('circle', { r: 5, fill: '#e8b54a', stroke: 'none' }, g);
  }

  /* rising embers / diya sparks */
  var canvas = document.getElementById('embers');
  var ctx = canvas && canvas.getContext && canvas.getContext('2d');
  var sparks = [], heroVisible = true;
  function sizeCanvas() {
    if (!ctx) return;
    var r = canvas.getBoundingClientRect(), dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = r.width * dpr; canvas.height = r.height * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    var want = Math.round(Math.min(70, r.width / 18));
    while (sparks.length < want) sparks.push(newSpark(r, true));
    sparks.length = want;
  }
  function newSpark(r, anywhere) {
    return { x: Math.random() * r.width, y: anywhere ? Math.random() * r.height : r.height + 10,
             s: 0.6 + Math.random() * 2.2, v: 0.25 + Math.random() * 0.7, w: Math.random() * 6.28, a: 0.25 + Math.random() * 0.6 };
  }
  function drawSparks() {
    if (!ctx || !heroVisible) return;
    var r = canvas.getBoundingClientRect();
    ctx.clearRect(0, 0, r.width, r.height);
    for (var i = 0; i < sparks.length; i++) {
      var s = sparks[i];
      s.y -= s.v; s.w += 0.02; s.x += Math.sin(s.w) * 0.3;
      if (s.y < -10) sparks[i] = s = newSpark(r, false);
      var fade = Math.min(1, s.y / (r.height * 0.6));
      ctx.beginPath();
      ctx.fillStyle = 'rgba(255,' + (190 + (s.s * 20 | 0)) + ',110,' + (s.a * fade) + ')';
      ctx.shadowColor = 'rgba(255,200,90,.9)'; ctx.shadowBlur = 8;
      ctx.arc(s.x, s.y, s.s, 0, 6.283);
      ctx.fill();
    }
  }
  if (ctx && !reduce) {
    sizeCanvas();
    window.addEventListener('resize', sizeCanvas);
    if ('IntersectionObserver' in window) new IntersectionObserver(function (e) { heroVisible = e[0].isIntersecting; }).observe(hero);
  }

  /* 3D story wheel */
  var journey = document.getElementById('journey');
  var ring = document.getElementById('ring');
  var dots = journey && journey.querySelector('.j-dots');
  var slides = [], R = 400, target = 0, angle = 0;
  function layoutRing() {
    if (!slides.length) return;
    var w = mobile.matches ? Math.max(150, Math.min(240, window.innerWidth * 0.5)) : Math.max(150, Math.min(250, window.innerWidth * 0.42));
    var n = slides.length, step = 360 / n;
    R = Math.round(w / 2 / Math.tan(Math.PI / n) + w * 0.25);
    ring.style.setProperty('--w', w + 'px');
    var rw = journey.querySelector('.ring-wrap');
    if (rw) rw.style.height = mobile.matches ? Math.round(w * 1.667 + 60) + 'px' : '';
    slides.forEach(function (s, i) { s.style.transform = 'rotateY(' + (i * step) + 'deg) translateZ(' + R + 'px)'; });
  }
  function buildRing(videos) {
    if (!ring) return;
    var STOP = { katha: 1, story: 1, malayalam: 1, hindi: 1, shorts: 1, short: 1, devotional: 1, kerala: 1, temple: 1, animation: 1 };
    function keys(t) { return (t.replace(/#\S+/g, '').match(/[A-Za-z]{4,}/g) || []).map(function (w) { return w.toLowerCase(); }).filter(function (w) { return !STOP[w]; }); }
    function same(a, b) {
      if (a.date === b.date && a.lang !== b.lang && a.short === b.short) return true;
      if (a.title.split(/[\s:|]/)[0] === b.title.split(/[\s:|]/)[0]) return true;
      var ka = keys(a.title); return keys(b.title).some(function (w) { return ka.indexOf(w) >= 0; });
    }
    var pick = [];
    var shorts = videos.filter(function (v) { return v.short && v.story != null; }).sort(function (a, b) { return a.rank - b.rank; });
    if (shorts.length >= 5) {
      /* latest 15 different stories, alternating Malayalam / Hindi */
      var byStory = {}, order = [];
      shorts.forEach(function (v) {
        if (!byStory[v.story]) { byStory[v.story] = {}; order.push(v.story); }
        if (!byStory[v.story][v.lang]) byStory[v.story][v.lang] = v;
      });
      order.slice(0, 15).forEach(function (s, i) {
        var want = i % 2 ? 'hi' : 'ml', other = i % 2 ? 'ml' : 'hi';
        var v = byStory[s][want] || byStory[s][other];
        if (v) pick.push(v);
      });
    } else {
      videos.forEach(function (v) {
        if (pick.length < 12 && !pick.some(function (p) { return same(p, v); })) pick.push(v);
      });
    }
    if (pick.length < 5) { journey.style.display = 'none'; return; }
    ring.textContent = '';
    slides = pick.map(function (v) {
      var a = document.createElement('a');
      a.className = 'slide';
      a.href = v.path ? '/story/' + v.path + '.html' : 'https://www.youtube.com/watch?v=' + v.id;
      var img = document.createElement('img');
      img.loading = 'lazy'; img.alt = ''; img.draggable = false;
      img.src = 'https://i.ytimg.com/vi/' + v.id + '/hqdefault.jpg';
      var b = document.createElement('b'); b.textContent = v.lang === 'ml' ? 'മലയാളം' : v.lang === 'hi' ? 'हिंदी' : 'English';
      var t = document.createElement('span'); t.textContent = v.title.replace(/#\S+/g, '').replace(/\s*\|.*$/, '').trim();
      a.appendChild(img); a.appendChild(b); a.appendChild(t);
      ring.appendChild(a);
      return a;
    });
    if (dots) { dots.textContent = ''; slides.forEach(function () { dots.appendChild(document.createElement('i')); }); }
    layoutRing();
    window.addEventListener('resize', layoutRing);
  }
  /* touch: swipe left/right turns the wheel, with a little fling, then settles on a card */
  var wrapEl = journey && journey.querySelector('.ring-wrap'), drag = null, dragged = false;
  if (wrapEl) {
    wrapEl.addEventListener('pointerdown', function (e) {
      if (!mobile.matches || !slides.length) return;
      drag = { id: e.pointerId, x: e.clientX, t0: target, last: e.clientX, lt: performance.now(), v: 0, moved: false };
    });
    wrapEl.addEventListener('pointermove', function (e) {
      if (!drag || e.pointerId !== drag.id) return;
      var dx = e.clientX - drag.x, now = performance.now();
      if (Math.abs(dx) > 6) drag.moved = true;
      drag.v = 0.7 * drag.v + 0.3 * (e.clientX - drag.last) / Math.max(1, now - drag.lt);
      drag.last = e.clientX; drag.lt = now;
      target = drag.t0 - dx * (360 / slides.length) / (slides[0].offsetWidth * 0.9);
    });
    var endDrag = function () {
      if (!drag) return;
      var step = 360 / slides.length, fling = -drag.v * step * 1.6;
      target = Math.round((target + Math.max(-2 * step, Math.min(2 * step, fling))) / step) * step;
      dragged = drag.moved; drag = null;
    };
    wrapEl.addEventListener('pointerup', endDrag);
    wrapEl.addEventListener('pointercancel', endDrag);
    wrapEl.addEventListener('click', function (e) { if (dragged) { e.preventDefault(); e.stopPropagation(); dragged = false; } }, true);
  }

  function updateRing() {
    if (!slides.length) return;
    var n = slides.length, step = 360 / n;
    angle += (target - angle) * (reduce ? 1 : 0.12);
    ring.style.transform = 'translateZ(' + (-R) + 'px) rotateX(' + (mobile.matches ? -1.5 : -6) + 'deg) rotateY(' + (-angle) + 'deg)';
    var front = ((Math.round(angle / step) % n) + n) % n;
    slides.forEach(function (s, i) {
      var d = ((i * step - angle) % 360 + 540) % 360 - 180; // -180..180, 0 = facing
      var f = Math.cos(d * Math.PI / 180);
      s.style.filter = 'brightness(' + (0.35 + 0.65 * Math.max(0, f)) + ')';
      s.style.zIndex = Math.round(f * 100) + 100;
    });
    if (dots) for (var k = 0; k < dots.children.length; k++) dots.children[k].className = k === front ? 'on' : '';
  }

  /* reveal on enter */
  function markReveal(nodes, stagger) {
    nodes.forEach(function (n, i) {
      if (n.hasAttribute('data-reveal')) return;
      n.setAttribute('data-reveal', '');
      if (stagger) n.style.setProperty('--d', (i % 8) * 0.06 + 's');
      io && io.observe(n);
      if (!io) n.classList.add('in');
    });
  }
  var io = ('IntersectionObserver' in window) && !reduce ? new IntersectionObserver(function (es) {
    es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
  }, { rootMargin: '0px 0px -8% 0px' }) : null;
  var q = function (s) { return Array.prototype.slice.call(document.querySelectorAll(s)); };
  markReveal(q('#stories .head, #about h2, #about .lead, .band h2, .band p, .band .btn, .more'), false);
  markReveal(q('.col'), true);
  var grid = document.getElementById('grid');
  if (grid) {
    markReveal(q('#grid .card'), true);
    new MutationObserver(function () { markReveal(q('#grid .card'), true); }).observe(grid, { childList: true });
  }

  /* card tilt (mouse only) */
  if (grid && !reduce && matchMedia('(hover: hover)').matches) {
    grid.addEventListener('pointermove', function (e) {
      var c = e.target.closest && e.target.closest('.card'); if (!c) return;
      var r = c.getBoundingClientRect(), x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
      c.style.setProperty('--ry', ((x - 0.5) * 14).toFixed(2) + 'deg');
      c.style.setProperty('--rx', ((0.5 - y) * 12).toFixed(2) + 'deg');
      c.style.setProperty('--mx', (x * 100).toFixed(1) + '%');
      c.style.setProperty('--my', (y * 100).toFixed(1) + '%');
    });
    grid.addEventListener('pointerout', function (e) {
      var c = e.target.closest && e.target.closest('.card');
      if (c && !c.contains(e.relatedTarget)) { c.style.setProperty('--rx', '0deg'); c.style.setProperty('--ry', '0deg'); }
    });
  }

  /* scroll-driven values */
  function onScroll() {
    var y = window.scrollY, h = doc.scrollHeight - window.innerHeight;
    doc.style.setProperty('--sp', h > 0 ? (y / h).toFixed(4) : 0);
    if (hero && !reduce && !mobile.matches) {
      var hp = Math.min(1, Math.max(0, y / hero.offsetHeight));
      hero.style.setProperty('--hp', hp.toFixed(4));
      hero.style.setProperty('--rot', (y * 0.06).toFixed(2) + 'deg');
    }
    if (journey && slides.length && !mobile.matches) {
      var top = journey.offsetTop, span = journey.offsetHeight - window.innerHeight;
      var p = Math.min(1, Math.max(0, (y - top) / span));
      target = p * 360 * (slides.length - 1) / slides.length;
    }
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll);

  function frame() {
    drawSparks();
    updateRing();
    requestAnimationFrame(frame);
  }

  fetch('/videos.json', { cache: 'no-cache' }).then(function (r) { return r.json(); }).then(function (d) {
    buildRing(d); onScroll(); angle = target;
  }).catch(function () { if (journey) journey.style.display = 'none'; });

  onScroll();
  requestAnimationFrame(frame);
})();
