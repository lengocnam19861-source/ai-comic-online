import streamlit as st
import json
from openai import OpenAI
import os

# ====== SETUP ======
st.set_page_config(page_title="AI Comic Generator", layout="wide")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ====== SESSION STATE ======
if "json_data" not in st.session_state:
    st.session_state.json_data = ""

if "mode" not in st.session_state:
    st.session_state.mode = "create"   # create / edit


# ====== SIDEBAR ======
st.sidebar.header("⚙️ Chế độ làm việc")

mode = st.sidebar.radio(
    "Chọn chế độ:",
    ["Tạo kịch bản từ ý tưởng", "Vẽ lại từ JSON đã chỉnh sửa"],
)

if mode == "Tạo kịch bản từ ý tưởng":
    st.session_state.mode = "create"
else:
    st.session_state.mode = "edit"

style = st.sidebar.selectbox(
    "Phong cách:",
    ["Manga Trinh Thám", "Anime Trẻ Em", "Chibi Dễ Thương", "Phong Cách Siêu Anh Hùng"]
)

num_pages = st.sidebar.slider("Số trang (khi tạo mới):", 1, 10, 4)


# ====== HEADER ======
st.title("📚 AI Comic Generator – Tự tạo & chỉnh sửa truyện từ A → Z")


# ====== MODE: TẠO KỊCH BẢN ======
if st.session_state.mode == "create":
    st.subheader("📝 Nhập ý tưởng truyện:")

    idea = st.text_area(
        "Nhập ý tưởng truyện (có thể viết dài, mô tả từng cảnh, thoại…):",
        height=120
    )

    if st.button("🚀 TẠO KỊCH BẢN"):
        with st.spinner("⏳ Đang tạo kịch bản…"):

            prompt = f"""
            Viết JSON cho truyện tranh phong cách: {style}.
            Số trang: {num_pages}.
            Nội dung: {idea}

            Format JSON:
            {{
                "title": "...",
                "pages": [
                    {{
                        "page_index": 1,
                        "panels": [
                            {{
                                "panel_index": 1,
                                "description": "...",
                                "dialogue": ["..."],
                                "prompt_image": "mô tả để vẽ hình"
                            }}
                        ]
                    }}
                ]
            }}
            """

            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )

            result = resp.choices[0].message.content

            try:
                cleaned = result.replace("```json", "").replace("```", "").strip()
                json.loads(cleaned)  # kiểm tra hợp lệ
                st.session_state.json_data = cleaned
                st.success("✅ Tạo kịch bản xong! Kéo xuống để chỉnh sửa hoặc vẽ.")
            except:
                st.error("❌ JSON lỗi!")
                st.write(result)


# ====== SHOW JSON EDITOR ======
if st.session_state.json_data:
    st.subheader("📝 JSON kịch bản (bro có thể sửa lời thoại, mô tả, prompt ảnh…)")

    st.session_state.json_data = st.text_area(
        "Chỉnh sửa JSON tại đây:", 
        value=st.session_state.json_data,
        height=450
    )

    if st.button("🎨 VẼ TRUYỆN TỪ JSON Ở TRÊN"):
        try:
            data = json.loads(st.session_state.json_data)

            st.success("🎉 Bắt đầu vẽ tranh từng panel…")

            for page in data["pages"]:
                st.markdown(f"## 📄 Trang {page['page_index']}")

                for panel in page["panels"]:
                    st.markdown(f"### 🔲 Panel {panel['panel_index']}")
                    st.write(panel["description"])
                    st.write("💬 " + ", ".join(panel["dialogue"]))

                    prompt_img = panel["prompt_image"]

                    img = client.images.generate(
                        model="gpt-image-1",
                        prompt=prompt_img,
                        size="512x512"
                    )

                    st.image(img.data[0].url)

        except Exception as e:
            st.error("❌ Lỗi khi vẽ! Kiểm tra JSON hoặc prompt.")
            st.write(e)
