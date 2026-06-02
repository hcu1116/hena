// ============================================
// HENA — 인터랙션 스크립트 v2
// ============================================

document.addEventListener('DOMContentLoaded', () => {

  // --- 1. 헤더: 스크롤하면 그림자 추가 ---
  const header = document.getElementById('site-header');
  if (header) {
    window.addEventListener('scroll', () => {
      header.classList.toggle('scrolled', window.scrollY > 20);
    }, { passive: true });
  }

  // --- 2. 스크롤 reveal 애니메이션 ---
  // IntersectionObserver: 요소가 화면에 들어왔는지 감지하는 브라우저 기능
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

  // .reveal, .reveal-left, .reveal-right, .reveal-stagger 모두 감지
  document.querySelectorAll('.reveal, .reveal-left, .reveal-right, .reveal-stagger')
    .forEach((el) => revealObserver.observe(el));

  // --- 3. 숫자 카운터 애니메이션 ---
  // 통계 섹션의 숫자가 0부터 목표값까지 올라가는 효과
  // easeOutQuart: 처음엔 빠르다가 끝에 가서 천천히 멈추는 느낌
  function easeOutQuart(t) {
    return 1 - Math.pow(1 - t, 4);
  }

  function animateCount(el, target, duration = 1800) {
    const start = performance.now();

    function tick(now) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const value = Math.round(easeOutQuart(progress) * target);

      // 1000 이상이면 쉼표 포맷 (예: 20,000)
      el.textContent = value >= 1000
        ? value.toLocaleString('ko-KR')
        : String(value);

      if (progress < 1) requestAnimationFrame(tick);
    }

    requestAnimationFrame(tick);
  }

  // 통계 숫자들을 화면에 들어올 때 카운터 시작
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
  // 스크롤 위치에 따라 목차의 현재 섹션 링크를 강조
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

});
