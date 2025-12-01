import base64
import json
from io import BytesIO

import streamlit as st
from openai import OpenAI
from PIL import Image

# ================== CONFIG CHUNG ==================
st.set_page_config(page_title="AI Comic Generator", layout="wide")
st.title("📚 AI Comic Generator – Tự tạo & chỉnh sửa truyện từ A → Z")

if "OPENAI_API_KEY" not in st.secrets:
    st.error("❌ Chưa có API KEY. Vào Settings → Secrets để thêm.")
    st.stop()

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Dùng session_state để giữ JSON kịch bản giữa các lần vẽ
if "json_text" not in st.session_state:
    st.session_state.json_text = ""


# ================== HÀM PHỤ ==================
def sanitize_json(text: str) -> str:
    """Gỡ ```json``` và ``` nếu GPT lỡ trả markdown code block."""
    return (
        text.replace("```json", "")
        .replace("```JSON", "")
        .replace("```", "")
        .strip()
    )


def render_comic_from_json(json_text: str):
    """Parse JSON và vẽ truyện. Cho phép dùng lại cho cả Generate & Edit."""

    json_text = sanitize_json(json_text)

    try:
        data = json.loads(json_text)
    except Exception as e:
        st.error(f"JSON lỗi, thử xem lại cấu trúc (Error: {e})")
        st.code(json_text, language="json")
        return

    # Hiện JSON để người dùng thấy lại
    st.subheader("📜 Kịch bản JSON (có thể copy về lưu)")
    st.code(json.dumps(data, ensure_ascii=False, indent=2), language="json")

    # ====== VẼ ẢNH ======
    st.subheader("🖼️ Vẽ từng khung truyện")
    final_pages = []

    pages = data.get("pages", [])
    if not pages:
        st.warning("JSON không có trường 'pages'. Kiểm tra lại bro.")
        return

    for page in pages:
        page_idx = page.get("page_index", 0)
        st.markdown(f"## Trang {page_idx}")
        cols = st.columns(2)
        page_images = []

        for panel in page.get("panels", []):
            prompt_img = panel.get("prompt_image", "")
            panel_idx = panel.get("panel_index", 0)
            dialogue = panel.get("dialogue", [])

            if not prompt_img:
                st.warning(f"Trang {page_idx} – Khung {panel_idx} thiếu 'prompt_image', bỏ qua.")
                continue

            with st.spinner(f"Vẽ khung {panel_idx} (Trang {page_idx})..."):
                try:
                    img_res = client.images.generate(
                        model="gpt-image-1",
                        prompt=f"Manga black & white, {prompt_img}",
                        size="1024x1024",
                        n=1,
                    )
                except Exception as e:
                    st.error(f"Lỗi khi vẽ ảnh (Trang {page_idx} – Khung {panel_idx}): {e}")
                    continue

                img_b64 = img_res.data[0].b64_json
                img_bytes = base64.b64decode(img_b64)
                img = Image.open(BytesIO(img_bytes))

                col = cols[(panel_idx - 1) % 2]
                col.image(img, caption=f"Trang {page_idx} – Khung {panel_idx}")
                if dialogue:
                    col.write("💬 " + " / ".join(dialogue))

                page_images.append(img)

        final_pages.append(page_images)

    st.success("🎉 Truyện đã vẽ xong!")

    # Cho tải ZIP nếu có ảnh
    if final_pages:
        import zipfile

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zipf:
            for i, page_imgs in enumerate(final_pages, start=1):
                for j, img in enumerate(page_imgs, start=1):
                    buf = BytesIO()
                    img.save(buf, format="PNG")
                    zipf.writestr(f"page{i}_panel{j}.png", buf.getvalue())

        zip_buffer.seek(0)
        st.download_button(
            "📥 Tải toàn bộ ảnh (.zip)",
            zip_buffer,
            file_name="comic_pages.zip",
            mime="application/zip",
        )


# ================== GIAO DIỆN CHÍNH ==================

with st.sidebar:
    st.header("⚙️ Chế độ làm việc")
    mode = st.radio(
        "Chọn chế độ:",
        ["Tạo kịch bản từ ý tưởng", "Vẽ lại từ JSON đã chỉnh sửa"],
    )

    style = st.selectbox(
        "Phong cách:",
        ["Manga Trinh Thám", "Shounen", "Anime Trẻ Em"],
    )
    pages = st.slider("Số trang (khi tạo mới):", 1, 10, 4)
    st.caption("Sau khi tạo, bro có thể sửa JSON rồi vẽ lại nhiều lần.")

st.markdown("---")

# ========== MODE 1: TẠO SCRIPT TỪ Ý TƯỞNG ==========
if mode == "Tạo kịch bản từ ý tưởng":
    idea = st.text_area(
        "💡 Nhập ý tưởng truyện (có thể viết dài, mô tả từng cảnh, thoại…):",
        height=160,
    )

    if st.button("🚀 TẠO KỊCH BẢN"):
        if not idea.strip():
            st.warning("Nhập ý tưởng trước bro 😅")
            st.stop()

        prompt = f"""
Bạn là AI chuyên tạo JSON truyện tranh.

QUY ĐỊNH RẤT QUAN TRỌNG:
- Chỉ trả về JSON THUẦN, KHÔNG dùng ```json hoặc bất kỳ markdown nào.
- KHÔNG viết thêm giải thích.
- KHÔNG có text nào ngoài JSON.
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
          "description": "Mô tả cảnh vẽ chi tiết (nhân vật, bối cảnh, cảm xúc)",
          "dialogue": ["Thoại 1", "Thoại 2"],
          "prompt_image": "Mô tả tiếng Anh ngắn gọn để AI vẽ, phong cách manga đen trắng"
        }}
      ]
    }}
  ]
}}

YÊU CẦU:
- Mỗi trang 2–4 panel.
- dialogue viết tiếng Việt, ngắn, tự nhiên.
- prompt_image viết tiếng Anh, mô tả rõ cảnh + góc máy + mood, phong cách manga B/W.
- Trả về ngay JSON theo đúng cấu trúc trên.
"""

        with st.spinner("⏳ Đang tạo kịch bản…"):
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
            )

        raw = resp.choices[0].message.content
        clean = sanitize_json(raw)

        # Lưu vào session để tab "Vẽ lại từ JSON" dùng
        st.session_state.json_text = clean

        st.success("✅ Tạo kịch bản xong! Bro kéo xuống để chỉnh sửa nếu muốn rồi vẽ.")
        st.subheader("✏️ JSON kịch bản (có thể sửa lời thoại, thêm bớt khung)")
        st.session_state.json_text = st.text_area(
            "Chỉnh sửa JSON tại đây rồi bấm nút VẼ LẠI phía dưới:",
            value=st.session_state.json_text,
            height=350,
        )

        if st.button("🎨 VẼ TRUYỆN TỪ JSON Ở TRÊN"):
            render_comic_from_json(st.session_state.json_text)

# ========== MODE 2: VẼ LẠI TỪ JSON ĐÃ CHỈNH ==========
else:
    st.info(
        "Dán JSON kịch bản vào ô dưới (hoặc dùng JSON đã tạo ở chế độ 1), "
        "chỉnh sửa lời thoại / thêm panel… rồi bấm vẽ."
    )

    st.session_state.json_text = st.text_area(
        "JSON kịch bản (bro có thể sửa thoải mái):",
        value=st.session_state.json_text,
        height=400,
    )

    if st.button("🎨 VẼ LẠI TRUYỆN TỪ JSON ĐÃ SỬA"):
        if not st.session_state.json_text.strip():
            st.warning("Chưa có JSON kịch bản kìa bro 😅")
        else:
            render_comic_from_json(st.session_state.json_text)
