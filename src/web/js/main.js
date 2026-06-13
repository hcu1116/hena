// ============================================
// HENA — 인터랙션 스크립트 v2
// ============================================

// ── ECG 파형 공유 함수 ──────────────────────
// Gaussian 5개 합산으로 P/Q/R/S/T 파 근사.
// t: 0~1 (한 박동), 반환: ~0(기준선) ~ 1.0(R 정점)
function ecgSample(t) {
  const g = (x, mu, s) => Math.exp(-((x - mu) ** 2) / (2 * s * s));
  return  0.13 * g(t, 0.18, 0.020)
         -0.08 * g(t, 0.33, 0.010)
         +1.00 * g(t, 0.38, 0.012)   // R파 (날카로운 주 스파이크)
         -0.14 * g(t, 0.43, 0.010)
         +0.22 * g(t, 0.57, 0.035);
}

// ── ECG 스트림 생성기 ────────────────────────
// 박동을 하나씩 실시간으로 생성해 순환 버퍼에 기록.
// 각 박동마다 간격(HRV)·진폭을 독립적으로 랜덤 결정 →
// 같은 모양이 반복되지 않는 살아있는 파형.
//
//   advance(targetPx) — targetPx CSS픽셀까지 버퍼 채우기
//   read(absPx)       — 절대 픽셀 위치의 정규화 y값 반환
function createECGStream({ basePPB, beatVar = 0.12, ampVar = 0.15, noiseAmp = 0.018 }) {
  const BUF = 8192;
  const buf = new Float32Array(BUF);

  let beatStartPx  = 0;
  let beatLengthPx = basePPB;
  let beatRamp     = 1.0;
  let writtenPx    = 0;

  function nextBeat() {
    beatStartPx  += beatLengthPx;
    beatLengthPx  = basePPB * (1 + (Math.random() * 2 - 1) * beatVar);
    beatRamp      = 1.0 + (Math.random() * 2 - 1) * ampVar;
  }

  return {
    get written() { return writtenPx; },

    advance(targetPx) {
      for (let px = writtenPx; px < targetPx; px++) {
        while (px >= beatStartPx + beatLengthPx) nextBeat();
        const phase = (px - beatStartPx) / beatLengthPx;
        const noise = Math.sin(px * 0.013) * noiseAmp
                    + Math.sin(px * 0.037) * (noiseAmp * 0.45);
        buf[px % BUF] = ecgSample(phase) * beatRamp + noise;
      }
      writtenPx = targetPx;
    },

    read(absPx) {
      return buf[Math.max(0, absPx) % BUF];
    },
  };
}

// ── 히어로 HENA Monitor 카드 실시간 ECG ─────
//
// Sweep 방식: 커서가 왼→오른쪽으로 이동하며 한 점씩 그림.
// 오른쪽 끝 도달 시 왼쪽부터 덮어씀 (진짜 병원 모니터 방식).
//
// 화면 레이아웃:
//   [새로 그린 구간 — 밝게] [GAP — 커서 위치] [이전 순환 — 흐리게]
//
function initHeroECG() {
  const canvas = document.getElementById('hcard-ecg-canvas');
  if (!canvas) return;

  const ctx   = canvas.getContext('2d');
  const dpr   = window.devicePixelRatio || 1;
  const CSS_H = 44;
  const SCROLL = 80;    // 커서 이동 속도 (CSS px/s)
  const GAP    = 6;     // 커서 앞 빈 구간 (CSS px)

  // 새 구간: 선명한 Electric Blue / 이전 구간: 40% 흐리게
  const C_NEW = 'rgba(77,158,255,1.00)';
  const C_OLD = 'rgba(77,158,255,0.38)';

  const stream = createECGStream({
    basePPB: 120, beatVar: 0.12, ampVar: 0.15, noiseAmp: 0.018,
  });

  let cssW = 0, fillGrad = null, amp = 0;

  function rebuild() {
    cssW = canvas.offsetWidth;
    if (!cssW) return;
    canvas.width  = cssW * dpr;
    canvas.height = CSS_H * dpr;
    const H = CSS_H * dpr, midY = H / 2;
    amp = midY * 0.85;
    const fg = ctx.createLinearGradient(0, midY - amp * 0.5, 0, H);
    fg.addColorStop(0, 'rgba(77,158,255,0.13)');
    fg.addColorStop(1, 'rgba(77,158,255,0)');
    fillGrad = fg;
  }
  rebuild();
  window.addEventListener('resize', rebuild, { passive: true });

  let writePos = 0, lastTime = null, rafId = null, visible = true;

  function draw(ts) {
    if (!visible) { rafId = null; return; }

    const dt = lastTime ? Math.min((ts - lastTime) / 1000, 0.05) : 0;
    lastTime  = ts;
    writePos += SCROLL * dt;

    const newPx   = Math.floor(writePos);
    const cursorX = newPx % cssW;       // 화면 위 커서 X 위치 (0 ~ cssW-1)
    stream.advance(newPx + 1);          // 현재 픽셀까지 버퍼 확보

    const W = cssW * dpr, H = CSS_H * dpr, midY = H / 2;
    ctx.clearRect(0, 0, W, H);
    if (!fillGrad || !W) { rafId = requestAnimationFrame(draw); return; }

    // 버퍼 인덱스 기준점
    // 새 구간: screen[0..cursorX] → buf[baseNew .. baseNew+cursorX]
    // 이전 구간: screen[cursorX+GAP .. cssW-1] → buf[baseOld+cursorX+GAP .. baseOld+cssW-1]
    const baseNew = newPx - cursorX;
    const baseOld = baseNew - cssW;

    ctx.lineWidth = 1.8 * dpr;
    ctx.lineCap   = 'round';
    ctx.lineJoin  = 'round';

    // ─ 이전 순환 구간: 커서 오른쪽, 흐리게 ─
    if (newPx >= cssW && cursorX + GAP < cssW) {
      ctx.beginPath();
      let first = true;
      for (let i = cursorX + GAP; i < cssW; i++) {
        const y = midY - stream.read(Math.max(0, baseOld + i)) * amp;
        const cx = i * dpr;
        if (first) { ctx.moveTo(cx, y); first = false; }
        else ctx.lineTo(cx, y);
      }
      ctx.strokeStyle = C_OLD;
      ctx.stroke();
    }

    // ─ 현재 순환 구간: 커서 왼쪽, 밝게 ─
    if (cursorX > 0) {
      ctx.beginPath();
      for (let i = 0; i <= cursorX; i++) {
        const y = midY - stream.read(Math.max(0, baseNew + i)) * amp;
        const cx = i * dpr;
        i === 0 ? ctx.moveTo(cx, y) : ctx.lineTo(cx, y);
      }
      ctx.strokeStyle = C_NEW;
      ctx.stroke();

      // 새 구간 아래 글로우 fill
      ctx.lineTo(cursorX * dpr, H);
      ctx.lineTo(0, H);
      ctx.closePath();
      ctx.fillStyle = fillGrad;
      ctx.fill();
    }

    rafId = requestAnimationFrame(draw);
  }

  new IntersectionObserver((entries) => {
    visible = entries[0].isIntersecting;
    if (visible && !rafId) { lastTime = null; rafId = requestAnimationFrame(draw); }
  }, { threshold: 0.1 }).observe(canvas);

  rafId = requestAnimationFrame(draw);
}

// ── 히어로 배경 ECG (전폭 캔버스) ────────────
// Sweep 방식. 배경이므로 색은 은은하게, 크기·속도는 잘 보이게.
function initBgECG() {
  const canvas = document.getElementById('hero-ecg-canvas');
  if (!canvas) return;

  const ctx   = canvas.getContext('2d');
  const dpr   = window.devicePixelRatio || 1;
  const CSS_H = 180;
  const SCROLL = 150;
  const GAP    = 6;

  const C_NEW = 'rgba(255,255,255,0.18)';
  const C_OLD = 'rgba(255,255,255,0.07)';

  const stream = createECGStream({
    basePPB: 300,
    beatVar: 0.10, ampVar: 0.12, noiseAmp: 0.010,
  });

  let cssW = 0, amp = 0;

  function rebuild() {
    cssW = canvas.offsetWidth;
    if (!cssW) return;
    canvas.width  = cssW * dpr;
    canvas.height = CSS_H * dpr;
    amp = (CSS_H * dpr / 2) * 0.82;
  }
  rebuild();
  window.addEventListener('resize', rebuild, { passive: true });

  let writePos = 0, lastTime = null, rafId = null, visible = true;

  // 초기 버퍼 미리 채우기: 커서를 화면 중간에서 시작
  // → 첫 프레임부터 전체 화면에 파형이 채워진 상태로 보임
  if (cssW > 0) {
    writePos = cssW * 1.5;
    stream.advance(Math.ceil(writePos) + 1);
  }

  function draw(ts) {
    if (!visible) { rafId = null; return; }

    const dt = lastTime ? Math.min((ts - lastTime) / 1000, 0.05) : 0;
    lastTime  = ts;
    writePos += SCROLL * dt;

    const newPx   = Math.floor(writePos);
    const cursorX = newPx % cssW;
    stream.advance(newPx + 1);

    const W = cssW * dpr, H = CSS_H * dpr, midY = H / 2;
    ctx.clearRect(0, 0, W, H);
    if (!W) { rafId = requestAnimationFrame(draw); return; }

    const baseNew = newPx - cursorX;
    const baseOld = baseNew - cssW;

    ctx.lineWidth = 1.5 * dpr;
    ctx.lineCap   = 'round';
    ctx.lineJoin  = 'round';

    // ─ 이전 순환 구간 ─
    if (newPx >= cssW && cursorX + GAP < cssW) {
      ctx.beginPath();
      let first = true;
      for (let i = cursorX + GAP; i < cssW; i++) {
        const y = midY - stream.read(Math.max(0, baseOld + i)) * amp;
        const cx = i * dpr;
        if (first) { ctx.moveTo(cx, y); first = false; }
        else ctx.lineTo(cx, y);
      }
      ctx.strokeStyle = C_OLD;
      ctx.stroke();
    }

    // ─ 현재 순환 구간 ─
    if (cursorX > 0) {
      ctx.beginPath();
      for (let i = 0; i <= cursorX; i++) {
        const y = midY - stream.read(Math.max(0, baseNew + i)) * amp;
        const cx = i * dpr;
        i === 0 ? ctx.moveTo(cx, y) : ctx.lineTo(cx, y);
      }
      ctx.strokeStyle = C_NEW;
      ctx.stroke();
    }

    rafId = requestAnimationFrame(draw);
  }

  new IntersectionObserver((entries) => {
    visible = entries[0].isIntersecting;
    if (visible && !rafId) { lastTime = null; rafId = requestAnimationFrame(draw); }
  }, { threshold: 0.01 }).observe(canvas);

  rafId = requestAnimationFrame(draw);
}

// ═══════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {

  // --- 1. 헤더: 스크롤하면 그림자 추가 ---
  const header = document.getElementById('site-header');
  if (header) {
    window.addEventListener('scroll', () => {
      header.classList.toggle('scrolled', window.scrollY > 20);
    }, { passive: true });
  }

  // --- 2. 스크롤 reveal 애니메이션 ---
  const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        revealObserver.unobserve(entry.target);
      }
    });
  }, {
    threshold: 0.1,
    rootMargin: '0px 0px -60px 0px'
  });

  document.querySelectorAll('.reveal, .reveal-left, .reveal-right, .reveal-stagger')
    .forEach((el) => revealObserver.observe(el));

  // --- 3. 숫자 카운터 애니메이션 ---
  function easeOutQuart(t) {
    return 1 - Math.pow(1 - t, 4);
  }

  function animateCount(el, target, duration = 1800) {
    const divisor = parseFloat(el.dataset.divisor) || 1;
    const start = performance.now();

    function tick(now) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const raw = easeOutQuart(progress) * target;

      let display;
      if (divisor !== 1) {
        display = (raw / divisor).toFixed(1);
      } else {
        const value = Math.round(raw);
        display = value >= 1000 ? value.toLocaleString('ko-KR') : String(value);
      }

      el.textContent = display;
      if (progress < 1) requestAnimationFrame(tick);
    }

    requestAnimationFrame(tick);
  }

  const counterObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        const el = entry.target;
        const target = parseInt(el.dataset.target, 10);
        animateCount(el, target);
        counterObserver.unobserve(el);
      }
    });
  }, { threshold: 0.5 });

  document.querySelectorAll('.stat-count')
    .forEach((el) => counterObserver.observe(el));

  // --- 4. 목차 활성화 (상세 페이지용) ---
  const tocLinks = document.querySelectorAll('.toc a[href^="#"]');
  if (tocLinks.length > 0) {
    const sectionIds = [...tocLinks].map((a) => a.getAttribute('href').slice(1));
    const sections = sectionIds
      .map((id) => document.getElementById(id))
      .filter(Boolean);

    const tocObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const id = entry.target.id;
          tocLinks.forEach((a) => {
            a.classList.toggle('active', a.getAttribute('href') === `#${id}`);
          });
        }
      });
    }, {
      threshold: 0.3,
      rootMargin: '-80px 0px -60% 0px'
    });

    sections.forEach((s) => tocObserver.observe(s));
  }

  // --- 5. 질환 정보 드롭다운 ---
  const dropdowns = document.querySelectorAll('.nav-dropdown');
  dropdowns.forEach((dropdown) => {
    const trigger = dropdown.querySelector('.nav-dropdown-trigger');

    trigger.addEventListener('click', (e) => {
      e.stopPropagation();
      const isOpen = dropdown.classList.contains('open');
      dropdowns.forEach((d) => {
        d.classList.remove('open');
        d.querySelector('.nav-dropdown-trigger').setAttribute('aria-expanded', 'false');
      });
      if (!isOpen) {
        dropdown.classList.add('open');
        trigger.setAttribute('aria-expanded', 'true');
      }
    });
  });

  document.addEventListener('click', () => {
    dropdowns.forEach((d) => {
      d.classList.remove('open');
      const t = d.querySelector('.nav-dropdown-trigger');
      if (t) t.setAttribute('aria-expanded', 'false');
    });
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      dropdowns.forEach((d) => {
        d.classList.remove('open');
        const t = d.querySelector('.nav-dropdown-trigger');
        if (t) t.setAttribute('aria-expanded', 'false');
      });
    }
  });

  // --- 6. ECG 파형 초기화 ---
  initHeroECG();  // HENA Monitor 카드 파형
  initBgECG();    // 히어로 배경 선

});
