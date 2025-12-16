import json
import os
import io
import zipfile
from collections import defaultdict

import streamlit as st
from openai import OpenAI
from PIL import Image

from google import genai
from google.genai import types

# ================== CẤU HÌNH APP ==================
st.set_page_config(
    page_title="AI Comic Pipeline PRO",
    layout="wide"
)
st.title("📚 AI Comic Pipeline PRO – Kịch bản ➜ Ảnh Gemini ➜ ZIP tải về")

st.caption(
    "Flow: Dán ý tưởng/kịch bản ➜ AI tạo JSON truyện ➜ Gọi Gemini sinh ảnh từng panel ➜ "
    "Tự lưu và gom lại theo trang/panel cho bro tải về."
)

# ================== API KEY ==================
# OPENAI dùng để tạo JSON kịch bản
if "OPENAI_API_KEY" not in st.secrets:
    st.error(
        "❌ Thiếu OPENAI_API_KEY trong Secrets.\n"
        "Vào Manage app → Settings → Secrets và thêm:\n"
        "OPENAI_API_KEY = \"sk-...\""
    )
    st.stop()

openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# GEMINI (Imagen) dùng để tạo ảnh
if "GEMINI_API_KEY" not in st.secrets:
    st.warning(
        "⚠ Chưa có GEMINI_API_KEY trong Secrets.\n"
        "Nếu bro dùng Gemini / Imagen thì vào Secrets thêm:\n"
        "GEMINI_API_KEY = \"<YOUR_GEMINI_API_KEY>\""
    )
    gemini_client = None
else:
    gemini_client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

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


def generate_script_with_openai(idea: str, art_style: str, pages: int, panels: int) -> str:
    """Gọi OpenAI tạo JSON kịch bản truyện."""
    sys_prompt = (
        "You are a professional comic script writer. "
        "Your job is to output ONLY valid JSON (no markdown) for a comic script."
    )

    user_prompt = f"""
Hãy tạo kịch bản truyện tranh ở dạng JSON.

YÊU CẦU QUAN TRỌNG:
- Chỉ trả về JSON THUẦN, KHÔNG dùng ```json hay ```.
- Không ghi thêm giải thích, không có chữ nào ngoài JSON.
- JSON phải parse được bằng json.loads trong Python.

Phong cách tranh: {art_style}
Số trang mong muốn: {pages}
Số panel ước lượng trên mỗi trang: {panels}

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

    resp = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
    )

    raw = resp.choices[0].message.content
    cleaned = extract_clean_json(raw)
    # Confirm JSON hợp lệ
    json.loads(cleaned)
    return cleaned


def generate_panel_image_with_gemini(prompt: str, aspect_ratio: str = "3:4") -> Image.Image:
    """
    Gọi Gemini/Imagen tạo ảnh từ prompt.
    Dùng SDK google-genai (client.models.generate_images).
    Lưu ý: bro cần enable Imagen 3 / Gemini Image trong project Google Cloud.
    """
    if gemini_client is None:
        raise RuntimeError("Chưa cấu hình GEMINI_API_KEY trong Streamlit secrets.")

    # Tham khảo docs: generate_images với Imagen 3
    # model 'imagen-3.0-generate-002' có thể thay đổi tùy project.
    response = gemini_client.models.generate_images(
        model="imagen-3.0-generate-002",
        prompt=prompt,
        config=types.GenerateImagesConfig(
            number_of_images=1,
            aspect_ratio=aspect_ratio,
        ),
    )

    # response.generated_images[0].image là đối tượng PIL.Image (theo docs SDK)
    img = response.generated_images[0].image
    return img


def build_panel_prompt(art_style: str, desc: str, prompt_img: str) -> str:
    """
    Ghép description tiếng Việt + prompt_image tiếng Anh thành prompt final cho Gemini.
    """
    base = f"""
{art_style}, comic panel illustration.

Scene (Vietnamese): {desc}

Image style (English): {prompt_img}

IMPORTANT:
- Do NOT draw any text, letters, or numbers.
- Do NOT draw speech bubble text.
- Có thể vẽ bóng thoại nhưng để trống bên trong, hoặc chừa khoảng trống để sau này thêm chữ.
- Clean line art, high detail, consistent characters, story-driven composition.
"""
    return base.strip()


def generate_all_images_from_json(
    data: dict,
    art_style: str,
    aspect_ratio: str = "3:4",
) -> tuple[list[dict], bytes]:
    """
    Vẽ TẤT CẢ panels theo JSON data bằng Gemini.
    Trả về:
    - danh sách {page_index, panel_index, filename, image_bytes}
    - zip_bytes: file zip chứa toàn bộ ảnh.
    """

    pages = data.get("pages", [])
    results = []

    # Dùng buffer zip trong RAM, không cần ghi file thật ra disk
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for page in pages:
            page_idx = page.get("page_index", 1)
            for panel in page.get("panels", []):
                panel_idx = panel.get("panel_index", 1)
                desc = panel.get("description", "")
                prompt_img = panel.get("prompt_image", "")

                final_prompt = build_panel_prompt(art_style, desc, prompt_img)
                filename = f"page{page_idx:02d}_panel{panel_idx:02d}.png"

                try:
                    img = generate_panel_image_with_gemini(final_prompt, aspect_ratio=aspect_ratio)
                except Exception as e:
                    # Nếu lỗi tạo ảnh, lưu log nhưng vẫn cho app chạy tiếp
                    results.append(
                        {
                            "page_index": page_idx,
                            "panel_index": panel_idx,
                            "filename": filename,
                            "error": str(e),
                            "image_bytes": None,
                        }
                    )
                    continue

                # Lưu ảnh vào bytes
                img_bytes_io = io.BytesIO()
                img.save(img_bytes_io, format="PNG")
                img_bytes = img_bytes_io.getvalue()

                # Ghi vào zip
                zf.writestr(filename, img_bytes)

                results.append(
                    {
                        "page_index": page_idx,
                            "panel_index": panel_idx,
                            "filename": filename,
                            "error": None,
                            "image_bytes": img_bytes,
                    }
                )

    zip_buffer.seek(0)
    zip_bytes = zip_buffer.getvalue()
    return results, zip_bytes


# ================== SIDEBAR ==================
with st.sidebar:
    st.header("⚙️ Cài đặt")

    mode = st.radio(
        "Chế độ:",
        ["Tạo kịch bản mới từ ý tưởng", "Dán/Chỉnh JSON có sẵn"],
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

    default_pages = st.slider("Số trang mong muốn (OpenAI dùng để gợi ý):", 1, 10, 1)
    default_panels = st.slider("Số panel / trang (ước lượng):", 1, 8, 4)

    aspect_ratio = st.selectbox(
        "Tỉ lệ ảnh Gemini:",
        ["1:1", "3:4", "4:3", "9:16", "16:9"],
        index=1,
    )

st.markdown("---")

# ================== MODE 1: TẠO KỊCH BẢN MỚI ==================
if mode == "Tạo kịch bản mới từ ý tưởng":
    st.subheader("🧠 Nhập ý tưởng / kịch bản thô")

    idea = st.text_area(
        "Bro mô tả cốt truyện, nhân vật, từng cảnh… (tiếng Việt):",
        height=160,
        placeholder="Ví dụ: Một chú mèo đen tò mò khám phá căn nhà cổ, phát hiện cánh cửa bí mật, mở ra và tìm thấy một bức ảnh gia đình...",
    )

    if st.button("🚀 Tạo JSON kịch bản bằng OpenAI"):
        if not idea.strip():
            st.warning("Nhập ý tưởng đã rồi mình mới chiến tiếp được bro 😅")
        else:
            try:
                with st.spinner("⏳ Đang nhờ OpenAI viết kịch bản JSON…"):
                    script = generate_script_with_openai(
                        idea=idea,
                        art_style=art_style,
                        pages=default_pages,
                        panels=default_panels,
                    )
                st.session_state.script_json = script
                st.success("✅ Đã tạo xong JSON kịch bản! Kéo xuống để chỉnh/sử dụng.")
            except Exception as e:
                st.error(f"❌ Lỗi khi tạo JSON: {e}")

# ================== CHỈNH JSON ==================
st.markdown("---")
st.subheader("✏️ JSON kịch bản (bro có thể sửa trực tiếp)")
st.caption("Mọi thao tác vẽ ảnh sẽ dùng JSON ở ô này.")

st.session_state.script_json = st.text_area(
    "Dán hoặc chỉnh JSON tại đây:",
    value=st.session_state.script_json,
    height=320,
    placeholder='{"title": "...", "pages": [...]}',
)

# Parse JSON
if not st.session_state.script_json.strip():
    st.info("Chưa có JSON. Bro hãy tạo bằng OpenAI hoặc dán JSON có sẵn vào.")
    st.stop()

try:
    data = json.loads(extract_clean_json(st.session_state.script_json))
    st.success("✅ JSON hợp lệ.")
except Exception as e:
    st.error(f"❌ JSON hiện tại bị lỗi: {e}")
    st.stop()

title = data.get("title", "Untitled Comic")
st.write(f"📖 **Tiêu đề truyện:** {title}")

# ================== VẼ ẢNH VỚI GEMINI ==================
st.markdown("---")
st.subheader("🎨 Bước 2 – Gọi Gemini vẽ TẤT CẢ panels và gom vào ZIP")

if gemini_client is None:
    st.error(
        "❌ Chưa cấu hình GEMINI_API_KEY nên không gọi Gemini vẽ ảnh được.\n"
        "Nếu bro muốn full pipeline, vào Secrets thêm GEMINI_API_KEY trước."
    )
else:
    if st.button("🖼️ VẼ TẤT CẢ PANEL BẰNG GEMINI & TẠO ZIP"):
        with st.spinner("⏳ Đang gọi Gemini vẽ từng panel… tuỳ số lượng nên có thể hơi lâu một chút."):
            try:
                results, zip_bytes = generate_all_images_from_json(
                    data,
                    art_style=art_style,
                    aspect_ratio=aspect_ratio,
                )
            except Exception as e:
                st.error(f"❌ Lỗi khi gọi Gemini tạo ảnh: {e}")
            else:
                st.success(f"✅ Đã xử lý xong {len(results)} panel.")

                # Hiển thị vài ảnh minh hoạ
                st.markdown("### 👀 Xem thử một vài panel đã vẽ:")

                show_count = 0
                for item in results:
                    if item["image_bytes"] is None:
                        st.warning(
                            f"Trang {item['page_index']} – Panel {item['panel_index']} lỗi: {item['error']}"
                        )
                        continue
                    img = Image.open(io.BytesIO(item["image_bytes"]))
                    st.image(
                        img,
                        caption=f"Trang {item['page_index']} – Panel {item['panel_index']} ({item['filename']})",
                        use_column_width=True,
                    )
                    show_count += 1
                    if show_count >= 4:
                        break

                # Nút tải ZIP
                st.markdown("### 📦 Tải toàn bộ ảnh (đã đánh số trang/panel)")
                st.download_button(
                    "📥 Tải file comic_panels.zip",
                    data=zip_bytes,
                    file_name="comic_panels.zip",
                    mime="application/zip",
                )

                st.info(
                    "Trong ZIP, mỗi file được đặt tên dạng:\n"
                    "`page01_panel01.png`, `page01_panel02.png`, …\n"
                    "Bro có thể import thẳng vào Canva / Premiere / CapCut / v.v. để làm video hoặc bố cục lại."
                )

