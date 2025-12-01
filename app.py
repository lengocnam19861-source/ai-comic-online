import base64
import json
from io import BytesIO

import streamlit as st
from openai import OpenAI
from PIL import Image

st.set_page_config(page_title="AI Comic Generator", layout="wide")

st.title("📚 AI Comic Generator – Tự tạo truyện từ A → Z")

if "OPENAI_API_KEY" not in st.secrets:
    st.error("❌ Chưa có API KEY. Vào Settings → Secrets để thêm.")
    st.stop()

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# FORM INPUT
style = st.sidebar.selectbox(
    "Phong cách:",
    ["Manga Trinh Thám", "Shounen", "Anime Trẻ Em"]
)

pages = st.sidebar.slider("Số trang:", 2, 10, 4)
idea = st.text_area("Nhập ý tưởng truyện:", height=150)

if st.button("🚀 TẠO TRUYỆN"):
    if not idea.strip():
        st.warning("Nhập ý tưởng trước bro 😅")
        st.stop()

    # Tạo JSON kịch bản
    prompt = f"""
    Hãy tạo truyện tranh phong cách {style}.
    Trả về JSON:
    {{
      "title": "...",
      "pages": [
        {{
          "page_index": 1,
          "panels": [
            {{
              "panel_index": 1,
              "description": "mô tả cảnh",
              "dialogue": ["..."],
              "prompt_image": "prompt để vẽ ảnh manga"
            }}
          ]
        }}
      ]
    }}
    Số trang: {pages}
    Ý tưởng: {idea}
    Chỉ trả về JSON hợp lệ, không thêm giải thích.
    """

    st.info("⏳ Đang tạo kịch bản…")

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    json_raw = resp.choices[0].message.content

    try:
        data = json.loads(json_raw)
    except:
        st.error("JSON lỗi, thử lại bro.")
        st.code(json_raw)
        st.stop()

    st.subheader("📜 Kịch bản JSON")
    st.code(json_raw, language="json")

    st.subheader("🎨 Đang vẽ các khung…")
    final_pages = []

    for page in data["pages"]:
        st.markdown(f"## Trang {page['page_index']}")
        cols = st.columns(2)
        imgs = []

        for panel in page["panels"]:
            with st.spinner(f"Vẽ khung {panel['panel_index']}..."):
                img = client.images.generate(
                    model="gpt-image-1",
                    prompt=f"Manga black & white, {panel['prompt_image']}",
                    size="1024x1024"
                )

                img_b64 = img.data[0].b64_json
                img_bytes = base64.b64decode(img_b64)
                img_pil = Image.open(BytesIO(img_bytes))

                col = cols[(panel['panel_index'] - 1) % 2]
                col.image(img_pil, caption=f"Khung {panel['panel_index']}")
                imgs.append(img_pil)

        final_pages.append(imgs)

    st.success("🎉 Hoàn tất!")
