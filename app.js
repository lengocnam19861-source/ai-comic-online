const content = document.getElementById("content");
const menuButtons = document.querySelectorAll(".menu-btn");

const kanjiLevels = ["N5", "N4", "N3", "N2", "N1"];
const lessons = Array.from({ length: 50 }, (_, i) => i + 1);

function renderKanji() {
  content.innerHTML = `
    <section class="card">
      <h2 class="section-title">Kanji theo cấp độ</h2>
      <div class="grid">
        ${kanjiLevels.map((lv) => `<button class="chip">${lv}</button>`).join("")}
      </div>
    </section>
    <section class="card">
      <h3>Mẫu dữ liệu Kanji (demo)</h3>
      <div class="item"><strong>日</strong> (nhật) · nghĩa: mặt trời / ngày</div>
      <div class="item"><strong>学</strong> (học) · nghĩa: học tập</div>
      <div class="item"><strong>生</strong> (sinh) · nghĩa: sống / học sinh</div>
    </section>
  `;
}

function renderGrammar() {
  content.innerHTML = `
    <section class="card">
      <h2 class="section-title">Ngữ pháp bài 1–50</h2>
      <div class="list">
        ${lessons.map((n) => `<div class="item">Bài ${n}</div>`).join("")}
      </div>
    </section>
  `;
}

function renderTest() {
  content.innerHTML = `
    <section class="card">
      <h2 class="section-title">Test bài 1–50</h2>
      <p>Chọn bài test để luyện tập.</p>
      <div class="list">
        ${lessons.map((n) => `<div class="item">Test bài ${n}</div>`).join("")}
      </div>
    </section>
  `;
}

function setSection(section) {
  menuButtons.forEach((btn) => btn.classList.toggle("active", btn.dataset.section === section));
  if (section === "kanji") return renderKanji();
  if (section === "grammar") return renderGrammar();
  renderTest();
}

menuButtons.forEach((btn) => {
  btn.addEventListener("click", () => setSection(btn.dataset.section));
});

setSection("kanji");
