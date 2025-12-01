import json

import streamlit as st
from openai import OpenAI

# ================== CẤU HÌNH APP ==================
st.set_page_config(
    page_title="AI Comic Prompt Studio",
    layout="wide"
)
st.title("📚 AI Comic Prompt Studio – Viết truyện & xuất prompt cho Gemini Canvas")

# ================== API KEY ==================
if "OPENAI_API_KEY" not in st.secrets:
    st.error(
        "❌ Chưa có OPENAI_API_KEY trong Secrets.\n"
        "Vào Manage app → Settings → Secrets và thêm:\n\n"
        "OPENAI_API_KEY = \"sk-...\""
    )
    st.stop()

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ================== SESSION STATE ==================
if "script_json" not in st.session_state:
    st.session_state.script_json = ""


# ================== HÀM PHỤ ==================
def extract_clean_json(text: str) -> str:
    """Bỏ ```json, ``` và cắt đoạn { ... } đầu–cuối."""
    if not text:
        return ""

    cleaned = (
        text.replace("```json", "")
        .replace("```JSON", "")
        .replace("```", "")
        .strip()
    )

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start : end + 1]

    return cleaned.strip()


def build_page_prompts_no_text(data: dict, art_style: str) -> str:
    """Prompt-level: từng TRANG, KHÔNG CHỮ (chỉ tranh + bóng thoại trống)."""
    title = data.get("title", "Untitled Comic")
    pages = data.get("pages", [])

    lines = []
    lines.append(
        f"GLOBAL INSTRUCTIONS:\n"
        f"- Create comic pages for a story titled '{title}'.\n"
        f"- Overall art style: {art_style}.\n"
        f"- Clean lineart, high detail, vibrant but soft colors.\n"
        f"- IMPORTANT: Do NOT draw any legible text, letters or numbers.\n"
        f"- You may draw speech bubbles, but keep them completely BLANK.\n"
        f"- No sound effects text (no 'BOOM', 'CLACK', etc.).\n"
        f"- No watermarks.\n"
        f"- High resolution, suitable for printing or HD screens.\n"
    )

    for page in pages:
        page_idx = page.get("page_index", 1)
        panels = page.get("panels", [])
        lines.append("")
        lines.append("=" * 60)
        lines.append(f"PAGE {page_idx} – COMIC LAYOUT PROMPT")
        lines.append(
            f"Create ONE comic page with {len(panels)} panels "
            f"in {art_style} style. Keep empty speech bubbles or empty areas for text."
        )

        for panel in panels:
            idx = panel.get("panel_index", 1)
            desc = panel.get("description", "")
            base_prompt = panel.get("prompt_image", "")
            lines.append("")
            lines.append(f"Panel {idx}:")
            if desc:
                lines.append(f"- Scene description (Vietnamese): {desc}")
            if base_prompt:
                lines.append(f"- Extra visual prompt (English): {base_prompt}")

        lines.append("")
        lines.append(
            "Camera: use varied cinematic angles (wide shot, medium, close-up) "
            "to make the page dynamic."
        )

    return "\n".join(lines)


def build_page_prompts_with_text(data: dict, art_style: str) -> str:
    """Prompt-level: từng TRANG, CÓ CHỮ TIẾNG VIỆT (cẩn thận font)."""
    title = data.get("title", "Untitled Comic")
    pages = data.get("pages", [])

    lines = []
    lines.append("GLOBAL INSTRUCTIONS FOR VIETNAMESE TEXT:")
    lines.append(
        "- Render all speech bubble text using a Vietnamese-safe font such as:\n"
        "  • Noto Sans\n"
        "  • Be Vietnam Pro\n"
        "  • Roboto\n"
    )
    lines.append(
        "- Do NOT change, normalize or remove diacritics in Vietnamese.\n"
        "- Keep all characters EXACTLY as written, including: "
        "ă â ê ô ơ ư đ Á Ắ Ứ ệ ố ờ ẵ ỹ.\n"
    )
    lines.append(
        "- If the system does not support these fonts by name, choose the closest "
        "modern sans-serif font that fully supports Vietnamese Unicode."
    )
    lines.append(
        f"- Art style: {art_style}. Clean lines, high detail, story-driven composition.\n"
    )

    for page in pages:
        page_idx = page.get("page_index", 1)
        panels = page.get("panels", [])
        lines.append("")
        lines.append("=" * 60)
        lines.append(f"PAGE {page_idx} – WITH VIETNAMESE DIALOGUE")

        for panel in panels:
            idx = panel.get("panel_index", 1)
            desc = panel.get("description", "")
            base_prompt = panel.get("prompt_image", "")
            dialogue = panel.get("dialogue", [])

            lines.append("")
            lines.append(f"Panel {idx}:")
            if desc:
                lines.append(f"- Scene description: {desc}")
            if base_prompt:
                lines.append(f"- Visual style prompt (English): {base_prompt}")
            if dialogue:
                lines.append("- Dialogue to show in speech bubbles (Vietnamese):")
                for d in dialogue:
                    lines.append(f"  • {d}")

    return "\n".join(lines)


def build_panel_prompt_list(data: dict, art_style: str) -> str:
    """Danh sách prompt cho TỪNG PANEL (vẽ lẻ từng cảnh)."""
    title = data.get("title", "Untitled Comic")
    pages = data.get("pages", [])

    lines = []
    lines.append(
        f"Single-panel prompts for the comic '{title}'. "
        f"Art style: {art_style}. High-res, detailed, no text unless explicitly mentioned."
    )
    lines.append("-" * 60)

    for page in pages:
        page_idx = page.get("page_index", 1)
        panels = page.get("panels", [])
        for panel in panels:
            idx = panel.get("panel_index", 1)
            desc = panel.get("description", "")
            base_prompt = panel.get("prompt_image", "")
            dialogue = panel.get("dialogue", [])

            lines.append("")
            lines.append(f"PAGE {page_idx} – PANEL {idx}")
            final_prompt = f"{art_style}, highly detailed illustration."

            if base_prompt:
                final_prompt += f" {base_prompt}"
            if desc:
                final_prompt += f" | Scene hint (VN): {desc}"

            lines.append(f"Image prompt: {final_prompt}")

            if dialogue:
                lines.append("Dialogue (Vietnamese, for reference only):")
                for d in dialogue:
                    lines.append(f"- {d}")

            lines.append("-" * 40)

    return "\n".join(lines)


# ================== SIDEBAR ==================
with st.sidebar:
    st.header("⚙️ Chế độ làm việc")

    mode = st.radio(
        "Chọn chế độ:",
        ["Tạo kịch bản mới từ ý tưởng", "Dán / chỉnh JSON có sẵn"],
    )

    art_style = st.selectbox(
        "Phong cách tranh:",
        [
            "Manga trinh thám đen trắng",
            "Anime trẻ em nhiều màu",
            "Phong cách Ghibli mềm mại",
            "Comic phương Tây màu sắc",
            "Chibi dễ thương",
        ],
    )

    default_pages = st.slider("Số trang mong muốn (khi tạo mới):", 1, 6, 1)
    default_panels = st.slider("Số panel / trang (ước lượng):", 1, 8, 4)


st.markdown("---")

# ================== MODE 1: TẠO KỊCH BẢN MỚI ==================
if mode == "Tạo kịch bản mới từ ý tưởng":
    st.subheader("🧠 Nhập ý tưởng truyện")

    idea = st.text_area(
        "Bro mô tả ý tưởng (cốt truyện, nhân vật, từng cảnh… càng chi tiết càng tốt):",
        height=160,
        placeholder="Ví dụ: Một chú mèo tò mò khám phá căn nhà cũ, phát hiện ra cánh cửa bí mật...",
    )

    if st.button("🚀 Tạo kịch bản JSON"):
        if not idea.strip():
            st.warning("Nhập ý tưởng đã rồi mình mới chiến chứ bro 😅")
        else:
            sys_prompt = (
                "You are a professional comic script writer. "
                "Your job is to output ONLY valid JSON (no markdown) "
                "for a comic book script."
            )

            user_prompt = f"""
Hãy tạo kịch bản truyện tranh ở dạng JSON.

YÊU CẦU QUAN TRỌNG:
- Chỉ trả về JSON THUẦN, KHÔNG dùng ```json hay ```.
- Không ghi thêm giải thích, không có chữ nào ngoài JSON.
- JSON phải parse được bằng json.loads trong Python.

Phong cách tranh: {art_style}
Số trang mong muốn: {default_pages}
Số panel ước lượng trên mỗi trang: {default_panels}

Nội dung (tiếng Việt):
{idea}

Cấu trúc JSON bắt buộc:

{{
  "title": "Tên truyện",
  "pages": [
    {{
      "page_index": 1,
      "panels": [
        {{
          "panel_index": 1,
          "description": "Mô tả cảnh bằng tiếng Việt (nhân vật, bối cảnh, hành động, cảm xúc)",
          "dialogue": ["Thoại 1", "Thoại 2"],
          "prompt_image": "Mô tả tiếng Anh ngắn gọn, dùng để vẽ ảnh (art style, lighting, camera, mood)"
        }}
      ]
    }}
  ]
}}

Quy tắc:
- description ngắn gọn nhưng rõ ràng.
- dialogue là mảng, mỗi phần tử là 1 câu thoại tiếng Việt.
- prompt_image viết tiếng Anh, có thể thêm thông tin: shot type (wide shot, close-up), lighting, mood, background.
"""

            with st.spinner("⏳ Đang nhờ AI viết kịch bản cho bro…"):
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.4,
                )

            raw = resp.choices[0].message.content
            cleaned = extract_clean_json(raw)

            try:
                json.loads(cleaned)  # kiểm tra hợp lệ
                st.session_state.script_json = cleaned
                st.success("✅ Đã tạo xong kịch bản JSON! Kéo xuống để chỉnh sửa & xuất prompt.")
            except Exception as e:
                st.error(f"❌ JSON lỗi, không parse được: {e}")
                st.subheader("Nội dung AI trả về (để bro tự chỉnh tay nếu cần):")
                st.code(raw, language="text")

# ================== MODE 2: DÁN / CHỈNH JSON ==================
if mode == "Dán / chỉnh JSON có sẵn" and not st.session_state.script_json:
    st.info("Bro có thể dán JSON kịch bản vào ô dưới (khi chưa có kịch bản nào).")

st.markdown("---")

# ================== KHU VỰC CHỈNH JSON ==================
st.subheader("✏️ JSON kịch bản (có thể sửa trực tiếp)")
st.caption("Khi sửa xong, tất cả prompt xuất ra bên dưới sẽ dùng bản JSON này.")

st.session_state.script_json = st.text_area(
    "Dán hoặc chỉnh JSON tại đây:",
    value=st.session_state.script_json,
    height=340,
    placeholder='{"title": "...", "pages": [...]}',
)

# Kiểm tra JSON
valid_data = None
if st.session_state.script_json.strip():
    try:
        valid_data = json.loads(extract_clean_json(st.session_state.script_json))
        st.success("✅ JSON hợp lệ.")
    except Exception as e:
        st.error(f"❌ JSON hiện tại bị lỗi: {e}")
        st.stop()
else:
    st.info("Chưa có JSON để làm prompt bro.")
    st.stop()

# ================== XUẤT PROMPT CHO GEMINI CANVAS ==================
st.markdown("---")
st.subheader("🎨 Bộ Prompt PRO cho Gemini Canvas / Canva / DALL·E …")

# 1) Prompt trang – không chữ
no_text_prompts = build_page_prompts_no_text(valid_data, art_style)
st.markdown("#### 1️⃣ Prompt vẽ TRANG – KHÔNG CHỮ (chỉ tranh + bóng thoại trống)")
st.caption("Dùng khi bro muốn tự thêm chữ trong Canva / Canvas.")
st.text_area(
    "Copy prompt này để dán vào Gemini Canvas (có thể chỉnh thêm nếu muốn):",
    value=no_text_prompts,
    height=260,
)
st.download_button(
    "📥 Tải file prompt_trang_khong_chu.txt",
    data=no_text_prompts.encode("utf-8"),
    file_name="prompt_trang_khong_chu.txt",
    mime="text/plain",
)

st.markdown("---")

# 2) Prompt trang – có chữ tiếng Việt
with_text_prompts = build_page_prompts_with_text(valid_data, art_style)
st.markdown("#### 2️⃣ Prompt vẽ TRANG CÓ CHỮ TIẾNG VIỆT (font an toàn)")
st.caption(
    "Dùng khi bro muốn Gemini vẽ luôn chữ tiếng Việt (đã kèm hướng dẫn dùng font Noto Sans / Be Vietnam Pro / Roboto)."
)
st.text_area(
    "Prompt có chữ TV (có thể hơi dài, bro copy phần cần thiết):",
    value=with_text_prompts,
    height=280,
)
st.download_button(
    "📥 Tải file prompt_trang_co_chu_viet.txt",
    data=with_text_prompts.encode("utf-8"),
    file_name="prompt_trang_co_chu_viet.txt",
    mime="text/plain",
)

st.markdown("---")

# 3) Prompt từng panel
panel_prompts = build_panel_prompt_list(valid_data, art_style)
st.markdown("#### 3️⃣ Prompt TỪNG PANEL (vẽ lẻ từng cảnh)")
st.caption("Dùng nếu bro muốn vẽ từng cảnh riêng rồi tự sắp vào layout.")
st.text_area(
    "Danh sách prompt cho từng panel:",
    value=panel_prompts,
    height=260,
)
st.download_button(
    "📥 Tải file prompt_tung_panel.txt",
    data=panel_prompts.encode("utf-8"),
    file_name="prompt_tung_panel.txt",
    mime="text/plain",
)

st.success("🔥 Xong! Bro chỉ việc copy hoặc tải file prompt và dán qua Gemini Canvas thôi.")
