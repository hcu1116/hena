// ============================================
// HENA — 생체신호 시뮬레이션
// Canvas API로 HR 그래프, CSS로 수면 타임라인
// ============================================

// ─────────────────────────────────────────────
// 섹션 1: HR 그래프 (Canvas API)
// ─────────────────────────────────────────────

// Canvas 기본 원리:
// - <canvas> 태그는 픽셀 단위 그리기 공간
// - getContext('2d')로 2D 그리기 도구 꺼냄
// - requestAnimationFrame으로 매 프레임(초당 60번) 다시 그림
// - 매번 지우고(clearRect) → 새로 그림 → 물이 흐르는 듯한 효과

const CANVAS_W = 400;
const CANVAS_H = 80;
const GRAPH_COLOR_NORMAL = '#4dd9ac';
const GRAPH_COLOR_NARCO  = '#f0784b';

// 일반인 파형 설정
const normalConfig = {
  baseBPM: 68,          // 기준 심박수
  bpmVariance: 3,       // BPM 변동 범위 (작을수록 규칙적)
  noiseAmp: 1.5,        // 파형 노이즈 크기
  spikeInterval: 55,    // 심장 박동 간격 (픽셀 단위)
  spikeHeight: 28,      // QRS 스파이크 높이
  color: GRAPH_COLOR_NORMAL,
  bpmEl: null,
  canvas: null,
  ctx: null,
};

// 기면증 파형 설정 (더 높고, 더 불규칙)
const narcoConfig = {
  baseBPM: 82,
  bpmVariance: 12,      // BPM 변동이 큼 (교감신경 과활성)
  noiseAmp: 4,          // 노이즈도 큼
  spikeInterval: 45,    // 박동 간격 더 짧음 (HR 높음)
  spikeHeight: 32,
  color: GRAPH_COLOR_NARCO,
  bpmEl: null,
  canvas: null,
  ctx: null,
};

// 공유 상태
let isPlaying = true;
let animFrameId = null;

// 각 파형의 x축 오프셋 (그래프가 왼쪽으로 흘러가는 효과)
let normalOffset = 0;
let narcoOffset = 0;

// 시간에 따른 BPM 변동을 위한 위상
let timePhase = 0;

// ── 파형 데이터 생성 ──
// offset을 기준으로 CANVAS_W 픽셀만큼의 파형 포인트를 생성
// 결과: [{x, y}, ...] 배열
function generateWavePoints(config, offset, phase) {
  const points = [];
  const midY = CANVAS_H / 2;

  for (let px = 0; px < CANVAS_W; px++) {
    // 실제 위치 = 화면 픽셀 + 스크롤 오프셋
    const realX = px + offset;

    // 기본 베이스라인 (사인파로 느리게 흔들림)
    const baseline = Math.sin(realX * 0.008 + phase) * config.noiseAmp;

    // QRS 스파이크: spikeInterval마다 심장 박동 모양
    const posInCycle = realX % config.spikeInterval;
    let spike = 0;
    if (posInCycle < 3) {
      spike = (posInCycle / 3) * config.spikeHeight;
    } else if (posInCycle < 6) {
      spike = ((6 - posInCycle) / 3) * config.spikeHeight;
    } else if (posInCycle < 10) {
      spike = -((posInCycle - 6) / 4) * (config.spikeHeight * 0.3);
    } else if (posInCycle < 14) {
      spike = (-(config.spikeHeight * 0.3)) + ((posInCycle - 10) / 4) * (config.spikeHeight * 0.3);
    }

    // 기면증의 경우 불규칙 노이즈 추가
    const irregularity = config.bpmVariance > 5
      ? Math.sin(realX * 0.03 + phase * 2.3) * 3
      : 0;

    points.push({
      x: px,
      y: midY - spike - baseline - irregularity,
    });
  }

  return points;
}

// ── Canvas에 파형 그리기 ──
function drawWave(config, offset, phase) {
  const { ctx, color } = config;
  if (!ctx) return;

  const midY = CANVAS_H / 2;

  ctx.clearRect(0, 0, CANVAS_W, CANVAS_H);

  // 배경 그리드라인 (수평)
  ctx.strokeStyle = 'rgba(255,255,255,0.05)';
  ctx.lineWidth = 1;
  [midY - 20, midY, midY + 20].forEach((y) => {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(CANVAS_W, y);
    ctx.stroke();
  });

  // 파형
  const points = generateWavePoints(config, offset, phase);
  ctx.beginPath();
  ctx.strokeStyle = color;
  ctx.lineWidth = 1.8;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';

  // 파형 아래 그라데이션 fill
  const grad = ctx.createLinearGradient(0, 0, 0, CANVAS_H);
  grad.addColorStop(0, color.replace(')', ', 0.15)').replace('rgb', 'rgba'));
  grad.addColorStop(1, 'rgba(0,0,0,0)');

  points.forEach((p, i) => {
    if (i === 0) ctx.moveTo(p.x, p.y);
    else ctx.lineTo(p.x, p.y);
  });
  ctx.stroke();

  // 그라데이션 fill
  ctx.lineTo(CANVAS_W, CANVAS_H);
  ctx.lineTo(0, CANVAS_H);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();
}

// ── BPM 계산 (시간에 따라 변동) ──
function calcBPM(config, phase) {
  const variation = Math.sin(phase * 0.3) * config.bpmVariance;
  return Math.round(config.baseBPM + variation);
}

// ── 메인 애니메이션 루프 ──
// requestAnimationFrame: "다음 화면 깜빡임 때 이 함수 실행해줘"
// 초당 약 60번 호출됨 → 부드러운 애니메이션
function animate() {
  if (!isPlaying) return;

  // 오프셋 증가 → 파형이 왼쪽으로 흘러가는 효과
  normalOffset += 1.2;
  narcoOffset += 1.5;   // 기면증은 약간 빠름 (HR 높음)
  timePhase += 0.01;

  drawWave(normalConfig, normalOffset, timePhase);
  drawWave(narcoConfig, narcoOffset, timePhase * 1.3);

  // BPM 표시 업데이트
  if (normalConfig.bpmEl) {
    normalConfig.bpmEl.textContent = `${calcBPM(normalConfig, timePhase)} BPM`;
  }
  if (narcoConfig.bpmEl) {
    narcoConfig.bpmEl.textContent = `${calcBPM(narcoConfig, timePhase)} BPM`;
  }

  animFrameId = requestAnimationFrame(animate);
}

// ── HR 시뮬레이션 초기화 ──
function initHRSimulation() {
  const canvasNormal = document.getElementById('canvas-normal');
  const canvasNarco  = document.getElementById('canvas-narco');

  if (!canvasNormal || !canvasNarco) return;

  // Canvas 실제 픽셀 크기 = CSS 크기 × devicePixelRatio (레티나 대응)
  const dpr = window.devicePixelRatio || 1;

  [canvasNormal, canvasNarco].forEach((c) => {
    const rect = c.getBoundingClientRect();
    c.width  = rect.width  * dpr || CANVAS_W * dpr;
    c.height = CANVAS_H * dpr;
    c.getContext('2d').scale(dpr, dpr);
    c.style.height = `${CANVAS_H}px`;
  });

  normalConfig.canvas = canvasNormal;
  normalConfig.ctx    = canvasNormal.getContext('2d');
  normalConfig.bpmEl  = document.getElementById('bpm-normal');

  narcoConfig.canvas = canvasNarco;
  narcoConfig.ctx    = canvasNarco.getContext('2d');
  narcoConfig.bpmEl  = document.getElementById('bpm-narco');

  // 컨트롤 버튼
  const btnPlay  = document.getElementById('btn-play');
  const btnReset = document.getElementById('btn-reset');

  if (btnPlay) {
    btnPlay.addEventListener('click', () => {
      isPlaying = !isPlaying;
      btnPlay.textContent = isPlaying ? '⏸ 일시정지' : '▶ 재생';
      btnPlay.classList.toggle('active', isPlaying);
      if (isPlaying) animate();
    });
  }

  if (btnReset) {
    btnReset.addEventListener('click', () => {
      normalOffset = 0;
      narcoOffset  = 0;
      timePhase    = 0;
      if (!isPlaying) {
        drawWave(normalConfig, 0, 0);
        drawWave(narcoConfig, 0, 0);
      }
    });
  }

  // 시작
  animate();
}


// ─────────────────────────────────────────────
// 섹션 2: 수면 패턴 타임라인
// ─────────────────────────────────────────────

// 24시간을 세그먼트 배열로 표현
// 각 세그먼트: { type: 'awake'|'light'|'deep'|'rem'|'eds'|'cataplexy', duration: 시간(분 단위 비율) }
// 총합 = 1440분 (24시간)

// 일반인 수면 패턴: 규칙적. 밤에 집중 수면.
const NORMAL_SEGMENTS = [
  // 오전 6시~밤 11시: 각성 (17시간)
  { type: 'awake', duration: 17 * 60 },
  // 밤 11시~오전 7시: 수면 사이클 반복
  { type: 'light',  duration: 30  },
  { type: 'deep',   duration: 60  },
  { type: 'rem',    duration: 20  },
  { type: 'light',  duration: 30  },
  { type: 'deep',   duration: 50  },
  { type: 'rem',    duration: 25  },
  { type: 'light',  duration: 20  },
  { type: 'deep',   duration: 40  },
  { type: 'rem',    duration: 30  },
  { type: 'light',  duration: 20  },
  { type: 'rem',    duration: 35  },
];

// 기면증 환자 수면 패턴: 낮에 EDS 에피소드, 밤 수면 분절, 탈력발작
const NARCO_SEGMENTS = [
  // 오전 6~8시: 각성
  { type: 'awake',     duration: 60  },
  // EDS 에피소드: 오전 8시경
  { type: 'eds',       duration: 20  },
  { type: 'awake',     duration: 70  },
  // 탈력발작
  { type: 'cataplexy', duration: 5   },
  { type: 'awake',     duration: 55  },
  // 낮 졸음 에피소드
  { type: 'eds',       duration: 30  },
  { type: 'awake',     duration: 45  },
  { type: 'eds',       duration: 15  },
  { type: 'awake',     duration: 60  },
  // 오후 EDS
  { type: 'eds',       duration: 25  },
  { type: 'awake',     duration: 55  },
  { type: 'cataplexy', duration: 5   },
  { type: 'awake',     duration: 90  },
  // EDS
  { type: 'eds',       duration: 20  },
  { type: 'awake',     duration: 60  },
  // 밤 수면: 분절됨
  { type: 'light',     duration: 20  },
  { type: 'rem',       duration: 15  }, // 비정상적으로 이른 REM
  { type: 'awake',     duration: 15  }, // 중간에 깸
  { type: 'light',     duration: 25  },
  { type: 'deep',      duration: 30  },
  { type: 'awake',     duration: 20  }, // 또 깸
  { type: 'rem',       duration: 20  },
  { type: 'light',     duration: 20  },
  { type: 'deep',      duration: 25  },
  { type: 'rem',       duration: 15  },
  { type: 'light',     duration: 15  },
];

let timelineAnimating = false;
let timelineProgress = 0; // 0 ~ 1
let timelineFrameId = null;

// 세그먼트를 HTML div 요소로 변환 + 진행도 마스킹
function renderTimeline(containerId, segments, progress) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const totalDuration = segments.reduce((sum, s) => sum + s.duration, 0);
  const visibleDuration = totalDuration * progress;

  container.innerHTML = '';

  let accumulated = 0;
  for (const seg of segments) {
    const segStart = accumulated;
    const segEnd   = accumulated + seg.duration;

    // 이 세그먼트가 progress 범위 안에 있는지
    if (segStart >= visibleDuration) break;

    // 부분적으로 보이는 경우 잘라냄
    const visibleWidth = Math.min(segEnd, visibleDuration) - segStart;
    const widthPct = (visibleWidth / totalDuration) * 100;

    const div = document.createElement('div');
    div.className = `t-seg ${seg.type}`;
    div.style.width = `${widthPct}%`;
    div.title = seg.type;
    container.appendChild(div);

    accumulated += seg.duration;
  }
}

function startTimelineAnimation() {
  if (timelineAnimating) return;
  timelineAnimating = true;
  timelineProgress  = 0;

  const btn = document.getElementById('btn-timeline');
  if (btn) btn.textContent = '⏹ 초기화';

  const DURATION_MS = 4000; // 4초에 걸쳐 24시간 채움
  const start = performance.now();

  function tick(now) {
    const elapsed  = now - start;
    timelineProgress = Math.min(elapsed / DURATION_MS, 1);

    renderTimeline('timeline-normal', NORMAL_SEGMENTS, timelineProgress);
    renderTimeline('timeline-narco',  NARCO_SEGMENTS,  timelineProgress);

    if (timelineProgress < 1) {
      timelineFrameId = requestAnimationFrame(tick);
    } else {
      timelineAnimating = false;
      if (btn) btn.textContent = '↺ 다시 재생';
    }
  }

  timelineFrameId = requestAnimationFrame(tick);
}

function resetTimeline() {
  cancelAnimationFrame(timelineFrameId);
  timelineAnimating = false;
  timelineProgress  = 0;
  renderTimeline('timeline-normal', NORMAL_SEGMENTS, 0);
  renderTimeline('timeline-narco',  NARCO_SEGMENTS,  0);
  const btn = document.getElementById('btn-timeline');
  if (btn) btn.textContent = '▶ 재생';
}

function initTimeline() {
  // 초기 빈 상태로 렌더
  renderTimeline('timeline-normal', NORMAL_SEGMENTS, 0);
  renderTimeline('timeline-narco',  NARCO_SEGMENTS,  0);

  const btn = document.getElementById('btn-timeline');
  if (!btn) return;

  btn.addEventListener('click', () => {
    if (timelineAnimating) {
      resetTimeline();
    } else if (timelineProgress >= 1) {
      resetTimeline();
      setTimeout(startTimelineAnimation, 50);
    } else {
      startTimelineAnimation();
    }
  });
}


// ─────────────────────────────────────────────
// 섹션 3: 진입점
// ─────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  initHRSimulation();
  initTimeline();
});
