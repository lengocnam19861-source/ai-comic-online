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

    # Bỏ code block markdown nếu có
    cleaned = (
        text.replace("```json", "")
        .replace("```JSON", "")
        .replace("```", "")
        .strip()
    )

    # Cắt từ dấu { đầu tiên tới dấu } cuối cùng
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

    # Hiện lại JSON đẹp đẽ
    st.subheader("📜 Kịch bản JSON (đã dùng để vẽ)")
    st.code(json.dumps(data, ensure_ascii=False, indent=2), language="json")

    pages = data.get("pages", [])
    if not pages:
        st.warning("JSON không có trường 'pages'. Kiểm tra lại cấu trúc bro.")
        return

    st.subheader("🖼️ Kết quả vẽ truyện")

    final_images = []

    for page in pages:
        page_index = page.get("page_index", 0)
        st.markdown(f"## 📄 Trang {page_index}")
        cols = st.columns(2)
        page_imgs = []

        for panel in page.get("panels", []):
            panel_index = panel.get("panel_index", 0)
            desc = panel.get("description", "")
            dialogue = panel.get("dialogue", [])
            prompt_img = panel.get("prompt_image", "")

            if not prompt_img:
                st.warning(f"Trang {page_index} – Panel {panel_index} thiếu 'prompt_image', bỏ qua.")
                continue

            with st.spinner(f"Đang vẽ Trang {page_index} – Panel {panel_index}…"):
                try:
                    img_res = client.images.generate(
                        model="gpt-image-1",
                        prompt=f"Manga black & white, {prompt_img}",
                        size="1024x1024",
                        n=1,
                    )
                    img_b64 = img_res.data[0].b64_json
                    img_bytes = base64.b64decode(img_b64)
                    img = Image.open(BytesIO(img_bytes))
                except Exception as e:
                    st.error(f"Lỗi khi vẽ ảnh (Trang {page_index}, Panel {panel_index}): {e}")
                    continue

            col = cols[(panel_index - 1) % 2]
            col.image(img, caption=f"Trang {page_index} – Panel {panel_index}")
            if desc:
                col.write(f"📝 {desc}")
            if dialogue:
                col.write("💬 " + " / ".join(dialogue))

            page_imgs.append(img)

        final_images.append(page_imgs)

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

# ================== MODE 1: TẠO KỊCH BẢN TỪ Ý TƯỞNG ==================
if mode == "Tạo kịch bản từ ý tưởng":
    idea = st.text_area(
        "💡 Nhập ý tưởng truyện (có thể mô tả từng cảnh, lời thoại…):",
        height=150,
    )

    if st.button("🚀 TẠO KỊCH BẢN"):
        if not idea.strip():
            st.warning("Nhập ý tưởng trước đã bro 😅")
        else:
            prompt = f"""
Bạn là AI chuyên tạo JSON truyện tranh.

QUY ĐỊNH RẤT QUAN TRỌNG:
- Chỉ trả về JSON THUẦN, KHÔNG dùng ```json hoặc bất kỳ markdown nào.
- KHÔNG viết thêm câu giải thích.
- KHÔNG có chữ nào nằm ngoài JSON.
- JSON phải parse được bằng json.loads trong Python.

Hãy tạo truyện tranh phong cách: {style}
Số trang: {pages}
Ý tưởng truyện (tiếng Việt): {idea}

Cấu trúc JSON bắt buộc:

{{
  "title": "Tên truyện",
  "pages": [
    {{
      "page_index": 1,
      "panels": [
        {{
          "panel_index": 1,
          "description": "Mô tả cảnh vẽ chi tiết (nhân vật, bối cảnh, cảm xúc, góc máy…)",
          "dialogue": ["Thoại 1", "Thoại 2"],
          "prompt_image": "Mô tả tiếng Anh ngắn gọn để AI vẽ, phong cách manga black & white"
        }}
      ]
    }}
  ]
}}

YÊU CẦU:
- Mỗi trang 2–4 panel.
- dialogue viết tiếng Việt, ngắn, tự nhiên.
- prompt_image viết tiếng Anh, mô tả rõ cảnh + mood + góc máy.
Trả về NGAY JSON theo đúng cấu trúc trên.
"""

            with st.spinner("⏳ Đang tạo kịch bản…"):
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.4,
                )

            raw = resp.choices[0].message.content
            cleaned = extract_clean_json(raw)

            try:
                json.loads(cleaned)  # kiểm tra hợp lệ
                st.session_state.json_text = cleaned
                st.success("✅ Tạo kịch bản xong! Kéo xuống để chỉnh sửa hoặc vẽ.")
            except Exception as e:
                st.error(f"❌ JSON lỗi (chi tiết: {e})")
                st.subheader("Nội dung GPT trả về (để debug):")
                st.code(raw, language="text")

# ================== MODE 2: VẼ LẠI TỪ JSON ==================
st.markdown("---")

if mode == "Vẽ lại từ JSON đã chỉnh sửa":
    st.info("Dán JSON kịch bản vào dưới đây, chỉnh sửa thoại / mô tả / panel xong rồi bấm vẽ.")
    st.session_state.json_text = st.text_area(
        "JSON kịch bản:",
        value=st.session_state.json_text,
        height=400,
    )
else:
    # Đang ở mode tạo script, nếu đã có JSON thì cho sửa luôn
    if st.session_state.json_text:
        st.subheader("✏️ JSON kịch bản (bro có thể sửa rồi vẽ)")
        st.session_state.json_text = st.text_area(
            "Chỉnh sửa JSON tại đây:",
            value=st.session_state.json_text,
            height=400,
        )

# Nút vẽ (dùng chung cho cả 2 mode, miễn là có JSON)
if st.session_state.json_text:
    if st.button("🎨 VẼ TRUYỆN TỪ JSON Ở TRÊN"):
        render_comic_from_json(st.session_state.json_text)
