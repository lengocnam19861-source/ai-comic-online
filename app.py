import base64
import json
from io import BytesIO

import streamlit as st
from openai import OpenAI
from PIL import Image

# ================== CẤU HÌNH APP ==================
st.set_page_config(page_title="AI Comic Generator", layout="wide")
st.title("📚 AI Comic Generator – Tự tạo & chỉnh sửa truyện từ A → Z")

# Lấy API key từ Streamlit secrets
if "OPENAI_API_KEY" not in st.secrets:
    st.error("❌ Chưa có API KEY. Vào Manage app → Secrets để thêm OPENAI_API_KEY.")
    st.stop()

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ================== SESSION STATE ==================
if "json_text" not in st.session_state:
    st.session_state.json_text = ""


# ================== HÀM PHỤ ==================
def extract_clean_json(text: str) -> str:
    """Bỏ ```json / ``` và cắt đoạn JSON từ { ... } đầu–cuối."""
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


def render_comic_from_json(json_text: str):
    """Parse JSON và vẽ truyện từ đó."""
    if not json_text.strip():
        st.warning("Chưa có JSON kịch bản bro 😅")
        return

    cleaned = extract_clean_json(json_text)

    try:
        data = json.loads(cleaned)
    except Exception as e:
        st.error(f"JSON lỗi, không parse được (chi tiết: {e})")
        st.code(cleaned, language="json")
        return

    st.subheader("📜 Kịch bản JSON đã dùng:")
    st.code(json.dumps(data, ensure_ascii=False, indent=2), language="json")

    pages = data.get("pages", [])
    if not pages:
        st.warning("JSON không có trường 'pages'.")
        return

    st.subheader("🖼️ Kết quả vẽ truyện")

    for page in pages:
        page_index = page.get("page_index", 0)
        st.markdown(f"## 📄 Trang {page_index}")
        cols = st.columns(2)

        for panel in page.get("panels", []):
            panel_index = panel.get("panel_index", 0)
            desc = panel.get("description", "")
            dialogue = panel.get("dialogue", [])
            prompt_img = panel.get("prompt_image", "")

            if not prompt_img:
                st.warning(f"Panel {panel_index} thiếu prompt_image, bỏ qua.")
                continue

            with st.spinner(f"Đang vẽ Panel {panel_index}…"):
                try:
                    img_res = client.images.generate(
                        model="gpt-image-1-mini",   # <<<<< MODEL KHÔNG CẦN VERIFY
                        prompt=f"Manga black & white, detailed line art, {prompt_img}",
                        size="1024x1024",
                        n=1,
                    )
                    img_b64 = img_res.data[0].b64_json
                    img_bytes = base64.b64decode(img_b64)
                    img = Image.open(BytesIO(img_bytes))
                except Exception as e:
                    st.error(f"Lỗi khi vẽ ảnh (Panel {panel_index}): {e}")
                    continue

            c = cols[(panel_index - 1) % 2]
            c.image(img, caption=f"Trang {page_index} – Panel {panel_index}")
            if desc:
                c.write(f"📝 {desc}")
            if dialogue:
                c.write("💬 " + " / ".join(dialogue))

    st.success("🎉 Vẽ xong truyện rồi bro!")


# ================== SIDEBAR ==================
with st.sidebar:
    st.header("⚙️ Chế độ làm việc")

    mode = st.radio(
        "Chọn chế độ:",
        ["Tạo kịch bản từ ý tưởng", "Vẽ lại từ JSON đã chỉnh sửa"],
    )

    style = st.selectbox(
        "Phong cách:",
        ["Manga Trinh Thám", "Anime Trẻ Em", "Chibi Dễ Thương", "Shounen"],
    )

    pages = st.slider("Số trang (khi tạo mới):", 1, 10, 4)
    st.caption("Sau khi tạo kịch bản, bro có thể sửa JSON rồi vẽ lại nhiều lần.")


st.markdown("---")

# ================== TẠO KỊCH BẢN ==================
if mode == "Tạo kịch bản từ ý tưởng":
    idea = st.text_area(
        "💡 Nhập ý tưởng truyện:",
        height=150,
    )

    if st.button("🚀 TẠO KỊCH BẢN"):
        if not idea.strip():
            st.warning("Nhập ý tưởng trước đã bro 😅")
        else:
            prompt = f"""
Bạn là AI chuyên tạo JSON truyện tranh.
TRẢ VỀ JSON THUẦN — KHÔNG GIẢI THÍCH.

Phong cách: {style}
Số trang: {pages}
Ý tưởng: {idea}

Cấu trúc JSON mẫu:
{{
  "title": "Tên truyện",
  "pages": [
    {{
      "page_index": 1,
      "panels": [
        {{
          "panel_index": 1,
          "description": "Mô tả cảnh tiếng Việt",
          "dialogue": ["Thoại 1", "Thoại 2"],
          "prompt_image": "Mô tả vẽ bằng tiếng Anh"
        }}
      ]
    }}
  ]
}}

Trả đúng JSON trên, không thêm chữ khác.
"""

            with st.spinner("⏳ Đang tạo kịch bản…"):
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                )

            raw = resp.choices[0].message.content
            cleaned = extract_clean_json(raw)

            try:
                json.loads(cleaned)
                st.session_state.json_text = cleaned
                st.success("✅ Tạo kịch bản xong! Kéo xuống để chỉnh sửa hoặc vẽ.")
            except Exception as e:
                st.error(f"❌ JSON lỗi: {e}")
                st.code(raw)

# ================== SỬA JSON ==================
st.markdown("---")

if mode == "Vẽ lại từ JSON đã chỉnh sửa":
    st.info("Dán JSON vào đây để vẽ lại.")
    st.session_state.json_text = st.text_area(
        "JSON kịch bản:",
        value=st.session_state.json_text,
        height=400,
    )
else:
    if st.session_state.json_text:
        st.subheader("✏️ JSON kịch bản (có thể sửa):")
        st.session_state.json_text = st.text_area(
            "Sửa JSON tại đây:",
            value=st.session_state.json_text,
            height=400,
        )

# ================== NÚT VẼ ==================
if st.session_state.json_text:
    if st.button("🎨 VẼ TRUYỆN TỪ JSON Ở TRÊN"):
        render_comic_from_json(st.session_state.json_text)
