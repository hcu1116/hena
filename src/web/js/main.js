// ============================================
// HENA — 인터랙션 스크립트
// ============================================

// 스크롤 시 .reveal 요소가 화면에 들어오면 나타나게 하기
document.addEventListener('DOMContentLoaded', () => {
  const reveals = document.querySelectorAll('.reveal');

  // IntersectionObserver: 요소가 화면에 보이는지 감지하는 브라우저 기능
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target); // 한 번 나타나면 관찰 중단
      }
    });
  }, {
    threshold: 0.1,          // 10% 보이면 발동
    rootMargin: '0px 0px -50px 0px'
  });

  reveals.forEach((el) => observer.observe(el));
});
