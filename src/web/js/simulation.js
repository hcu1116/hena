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
const CANVAS_H = 140;
const GRAPH_COLOR_NORMAL = '#4dd9ac';
const GRAPH_COLOR_NARCO  = '#f0784b';

// 일반인 파형 설정
const normalConfig = {
  baseBPM: 68,          // 기준 심박수
  bpmVariance: 3,       // BPM 변동 범위 (작을수록 규칙적)
  noiseAmp: 0.8,        // 파형 노이즈 크기
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
  noiseAmp: 2,          // 노이즈도 큼
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

// ── EDS 이벤트 상태 ──
// 기면증 환자에게 주기적으로 EDS(주간졸림) 에피소드가 발생:
// BPM이 급등하고 파형이 불안정해짐.
// interval마다 duration 동안 이벤트 활성화.
const EDS_INTERVAL_MS  = 9000;  // 9초마다 EDS 에피소드
const EDS_DURATION_MS  = 2500;  // 2.5초 동안 지속
let edsStartTime   = null;      // 현재 EDS 시작 시각 (null = 비활성)
let nextEdsTime    = EDS_INTERVAL_MS; // 다음 EDS까지 남은 ms
let edsCount       = 0;
let abnormalMs     = 0;         // 누적 비정상 심박 시간 (ms)
let lastFrameTime  = null;      // 프레임 간 시간 측정용

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
      ? Math.sin(realX * 0.03 + phase * 2.3) * 1.5
      : 0;

    points.push({
      x: px,
      y: midY - spike - baseline - irregularity,
    });
  }

  return points;
}

// ── Canvas에 파형 그리기 ──
// inEDS: 기면증 EDS 에피소드 진행 중이면 true → 빨간 하이라이트 오버레이
function drawWave(config, offset, phase, inEDS = false) {
  const { ctx, color } = config;
  if (!ctx) return;

  const W = config.canvas.width / (window.devicePixelRatio || 1);
  const midY = CANVAS_H / 2;

  ctx.clearRect(0, 0, W, CANVAS_H);

  // 배경 그리드라인 (수평)
  ctx.strokeStyle = 'rgba(255,255,255,0.05)';
  ctx.lineWidth = 1;
  [midY - 35, midY, midY + 35].forEach((y) => {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(W, y);
    ctx.stroke();
  });

  // EDS 에피소드 중: 우측에 빨간 경보 오버레이 (파형 위에 겹침)
  if (inEDS) {
    const alertWidth = W * 0.3;
    const alertGrad = ctx.createLinearGradient(W - alertWidth, 0, W, 0);
    alertGrad.addColorStop(0, 'rgba(229,62,62,0)');
    alertGrad.addColorStop(1, 'rgba(229,62,62,0.18)');
    ctx.fillStyle = alertGrad;
    ctx.fillRect(W - alertWidth, 0, alertWidth, CANVAS_H);

    // "EDS" 라벨
    ctx.fillStyle = 'rgba(252,129,129,0.9)';
    ctx.font = 'bold 11px monospace';
    ctx.textAlign = 'right';
    ctx.fillText('⚡ EDS', W - 8, 16);
  }

  // 파형 포인트 생성
  const tempCanvas = { ...config, canvas: { width: W * (window.devicePixelRatio || 1) } };
  const points = generateWavePoints(config, offset, phase);

  // EDS 중에는 파형 색상을 빨간색으로 전환
  const waveColor = inEDS ? '#fc8181' : color;

  // 파형 아래 그라데이션 fill
  const grad = ctx.createLinearGradient(0, 0, 0, CANVAS_H);
  grad.addColorStop(0, hexToRgba(waveColor, 0.18));
  grad.addColorStop(1, 'rgba(0,0,0,0)');

  ctx.beginPath();
  ctx.strokeStyle = waveColor;
  ctx.lineWidth = inEDS ? 2.2 : 1.8;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';

  points.forEach((p, i) => {
    // x 좌표를 실제 캔버스 너비에 맞게 스케일
    const scaledX = (p.x / CANVAS_W) * W;
    if (i === 0) ctx.moveTo(scaledX, p.y);
    else ctx.lineTo(scaledX, p.y);
  });
  ctx.stroke();

  // 그라데이션 fill
  const lastPt = points[points.length - 1];
  const lastX  = (lastPt.x / CANVAS_W) * W;
  ctx.lineTo(lastX, CANVAS_H);
  ctx.lineTo(0, CANVAS_H);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();
}

// hex 색상 → rgba 문자열 변환 헬퍼
function hexToRgba(hex, alpha) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

// ── BPM 계산 (시간에 따라 변동) ──
// inEDS: EDS 에피소드 중이면 BPM을 급등시킴
function calcBPM(config, phase, inEDS = false) {
  const variation = Math.sin(phase * 0.3) * config.bpmVariance;
  const base = Math.round(config.baseBPM + variation);
  return inEDS ? base + Math.round(15 + Math.abs(Math.sin(phase * 2)) * 10) : base;
}

// ── 상태 텍스트 결정 ──
function getStatusText(isNarco, bpm, inEDS) {
  if (!isNarco) {
    if (bpm < 65) return '부교감신경 우위 · 안정적 서맥';
    if (bpm > 75) return '약간의 심박 상승 · 정상 범위';
    return '부교감신경 우위 · 규칙적 정상 리듬';
  }
  if (inEDS) return '⚡ EDS 에피소드 — 갑작스러운 졸음 발작 · 심박 급등';
  if (bpm > 88) return '교감신경 과활성 · 심박 상승 · LF/HF↑';
  if (bpm > 82) return '불안정한 기저 심박 · 교감신경 우위';
  return '안정 시에도 교감신경 과활성 상태 지속';
}

// ── 메인 애니메이션 루프 ──
// requestAnimationFrame: "다음 화면 깜빡임 때 이 함수 실행해줘"
// 초당 약 60번 호출됨 → 부드러운 애니메이션
function animate(timestamp) {
  if (!isPlaying) return;

  // 프레임 간 경과 시간 계산 (ms)
  const delta = lastFrameTime ? timestamp - lastFrameTime : 16;
  lastFrameTime = timestamp;

  // ── EDS 이벤트 타이머 ──
  nextEdsTime -= delta;
  let inEDS = false;

  if (edsStartTime !== null) {
    // EDS 에피소드 진행 중
    const elapsed = timestamp - edsStartTime;
    if (elapsed < EDS_DURATION_MS) {
      inEDS = true;
      abnormalMs += delta;
    } else {
      // EDS 종료
      edsStartTime = null;
      nextEdsTime = EDS_INTERVAL_MS;
      // 상태 텍스트 alert 클래스 제거
      const statusEl = document.getElementById('status-narco');
      if (statusEl) statusEl.classList.remove('alert');
    }
  } else if (nextEdsTime <= 0) {
    // EDS 새로 시작
    edsStartTime = timestamp;
    edsCount += 1;
    inEDS = true;
    const statusEl = document.getElementById('status-narco');
    if (statusEl) statusEl.classList.add('alert');
  }

  // 오프셋 증가 → 파형이 왼쪽으로 흘러가는 효과
  // 느리게 해야 패턴 차이가 눈에 들어옴
  normalOffset += 0.4;
  narcoOffset += 0.5;   // 기면증은 약간 빠름 (HR 높음 → spikeInterval 짧음)
  timePhase += 0.001;

  drawWave(normalConfig, normalOffset, timePhase, false);
  drawWave(narcoConfig,  narcoOffset,  timePhase * 1.3, inEDS);

  // BPM 계산
  const bpmNormal = calcBPM(normalConfig, timePhase, false);
  const bpmNarco  = calcBPM(narcoConfig,  timePhase * 1.3, inEDS);

  // BPM 표시 업데이트
  if (normalConfig.bpmEl) normalConfig.bpmEl.textContent = `${bpmNormal} BPM`;
  if (narcoConfig.bpmEl)  narcoConfig.bpmEl.textContent  = `${bpmNarco} BPM`;

  // 상태 텍스트 업데이트
  const statusNormal = document.getElementById('status-normal');
  const statusNarco  = document.getElementById('status-narco');
  if (statusNormal) statusNormal.textContent = getStatusText(false, bpmNormal, false);
  if (statusNarco)  statusNarco.textContent  = getStatusText(true,  bpmNarco,  inEDS);

  // 카운터 업데이트
  const bpmDiff = Math.abs(bpmNarco - bpmNormal);
  const cntDiff     = document.getElementById('cnt-bpm-diff');
  const cntEds      = document.getElementById('cnt-eds');
  const cntAbnormal = document.getElementById('cnt-abnormal');

  if (cntDiff)     cntDiff.textContent     = `+${bpmDiff}`;
  if (cntEds)      cntEds.textContent      = edsCount;
  if (cntAbnormal) cntAbnormal.textContent = Math.round(abnormalMs / 1000);

  // EDS 중에 카운터 색상 강조
  if (cntDiff) {
    cntDiff.className = `sim-counter-value ${inEDS ? 'alert-val' : 'normal-val'}`;
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
      if (isPlaying) {
        lastFrameTime = null;
        requestAnimationFrame(animate);
      }
    });
  }

  if (btnReset) {
    btnReset.addEventListener('click', () => {
      normalOffset = 0;
      narcoOffset  = 0;
      timePhase    = 0;
      edsStartTime = null;
      nextEdsTime  = EDS_INTERVAL_MS;
      edsCount     = 0;
      abnormalMs   = 0;
      lastFrameTime = null;
      const cntDiff     = document.getElementById('cnt-bpm-diff');
      const cntEds      = document.getElementById('cnt-eds');
      const cntAbnormal = document.getElementById('cnt-abnormal');
      if (cntDiff)     { cntDiff.textContent = '0'; cntDiff.className = 'sim-counter-value normal-val'; }
      if (cntEds)      cntEds.textContent      = '0';
      if (cntAbnormal) cntAbnormal.textContent = '0';
      const statusNarco = document.getElementById('status-narco');
      if (statusNarco) statusNarco.classList.remove('alert');
      if (!isPlaying) {
        drawWave(normalConfig, 0, 0, false);
        drawWave(narcoConfig,  0, 0, false);
      }
    });
  }

  // 시작
  requestAnimationFrame(animate);
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
