import streamlit as st
import pandas as pd
import os
from PIL import Image
import re
import base64
import numpy as np

st.set_page_config(layout="wide")

EXCEL_PATH = "Qogita Analyse v3_check+JEWLWW(photo).xlsx"
IMAGE_DIR = "SellerampPhoto"

df = pd.read_excel(EXCEL_PATH)

if "filter_mode" not in st.session_state:
    st.session_state.filter_mode = False

col_filter, col_status = st.columns([1, 5])
with col_filter:
    if st.button("🔍 Lọc Mua Hay Ko", key="btn_filter_toggle"):
        st.session_state.filter_mode = not st.session_state.filter_mode
with col_status:
    if st.session_state.filter_mode:
        st.success("Đang lọc: chỉ hiển thị các dòng chưa có quyết định Mua Hay Ko")
    else:
        st.info("Đang hiển thị toàn bộ sản phẩm")

if st.session_state.filter_mode:
    df = df[df["Mua Hay Ko"].isna()]

if "EAN" in df.columns:
    cols = ["EAN"] + [col for col in df.columns if col != "EAN"]
    df = df[cols]

sale_order = []
for s in df["Sale"].astype(str):
    match = re.search(r"(\d+(\.\d+)?)/mo", s)
    if match:
        sale_order.append(float(match.group(1)))
    elif s.lower() == "unknown":
        sale_order.append(-1)
    else:
        sale_order.append(0)
df["__sale_order"] = sale_order
df = df.sort_values("__sale_order", ascending=False).drop(columns=["__sale_order"])

st.title("🔎 Qogita Visual Decision Tool")
st.markdown("Duyệt toàn bộ sản phẩm để xem ảnh và điền 'Mua Hay Ko'.")

with open(EXCEL_PATH, "rb") as f:
    st.download_button("📥 Tải file Excel đã cập nhật", f, file_name=os.path.basename(EXCEL_PATH))

page_size = 25
num_pages = (len(df) - 1) // page_size + 1

if "page" not in st.session_state:
    st.session_state.page = 1

col_prev, col_next = st.columns([1, 9])
with col_prev:
    if st.button("◀️ Trang trước") and st.session_state.page > 1:
        st.session_state.page -= 1
with col_next:
    if st.button("▶️ Trang sau") and st.session_state.page < num_pages:
        st.session_state.page += 1

selected_page = st.selectbox(
    "Chọn trang",
    options=list(range(1, num_pages + 1)),
    index=st.session_state.page - 1,
    format_func=lambda x: f"Trang {x}"
)
st.session_state.page = selected_page

start_idx = (selected_page - 1) * page_size
end_idx = start_idx + page_size

st.subheader(f"📋 Danh sách sản phẩm - Trang {selected_page}/{num_pages}")

for idx in range(start_idx, min(end_idx, len(df))):
    selected_row = df.iloc[idx]
    row_id = selected_row.name
    raw_ean = str(selected_row["EAN"])
    ean = re.sub(r"[^0-9]", "", raw_ean)

    header_info = f"#{idx+1} | EAN: {raw_ean} | Sale: {selected_row.get('Sale', '')} | BSR: {selected_row.get('BSR', '')} | Seller: {selected_row.get('Seller', '')}"
    show_key = f"show_{row_id}"

    # Nếu chưa có trạng thái thì đặt mặc định là False
    if show_key not in st.session_state:
        st.session_state[show_key] = False

    with st.expander(header_info, expanded=st.session_state[show_key]):
        # Khi mở expander, tự bật trạng thái checkbox
        st.session_state[show_key] = True

        col1, col2 = st.columns([1, 5])
        with col1:
            options = ["", "Y", "N"]
            mua_value = selected_row.get("Mua Hay Ko", "")
            if pd.isna(mua_value):
                mua_value = ""
            default_index = options.index(mua_value) if mua_value in options else 0

            decision = st.selectbox(f"📌 Mua Hay Ko (#{idx+1})", options,
                                    index=default_index,
                                    key=f"decision_{row_id}")

            if st.button(f"✅ Cập nhật dòng {row_id+1}", key=f"btn_{row_id}"):
                df.at[row_id, "Mua Hay Ko"] = decision
                df.to_excel(EXCEL_PATH, index=False)
                st.success(f"Đã cập nhật dòng {row_id+1}!")

            if selected_row.get("Product Link"):
                st.markdown(f"[🔗 Link Qogita]({selected_row['Product Link']})")
            st.markdown(f"[🔗 Link Selleramp](https://sas.selleramp.com/sas/lookup?search_term={ean})")
            if selected_row.get("Link Amazon.fr"):
                st.markdown(f"[🔗 Link Amazon.fr]({selected_row['Link Amazon.fr']})")

        with col2:
            fields_to_show = ["EAN", "Prix Qogita", "Prix amazon", "ASIN", "Coeff", "Profit"]
            for field in fields_to_show:
                if field in selected_row:
                    st.markdown(f"**{field}**: {selected_row[field]}")

            image_path = os.path.join(IMAGE_DIR, f"{ean}.png")
            if os.path.exists(image_path):
                with open(image_path, "rb") as img_file:
                    img_bytes = img_file.read()
                    encoded = base64.b64encode(img_bytes).decode()

                st.components.v1.html(
                    f"""
                    <html>
                    <head>
                    <style>
                    html, body, #zoom-container-{idx} {{
                        height: 100%;
                        margin: 0;
                    }}
                    #zoom-container-{idx} {{
                        overflow: auto;
                        border: 1px solid #ddd;
                    }}
                    #zoom-image-{idx} {{
                        width: 100%;
                        transform-origin: 0 0;
                    }}
                    </style>
                    </head>
                    <body>
                        <div id='zoom-container-{idx}'>
                            <img id='zoom-image-{idx}' src='data:image/png;base64,{encoded}' draggable='true' />
                        </div>
                        <script>
                        const img = document.getElementById('zoom-image-{idx}');
                        img.scale = 1;
                        img.addEventListener('wheel', function(event) {{
                            event.preventDefault();
                            let scale = img.scale || 1;
                            scale += event.deltaY < 0 ? 0.1 : -0.1;
                            scale = Math.min(Math.max(0.5, scale), 3);
                            img.scale = scale;
                            img.style.transform = `scale(${{scale}})`;
                        }});
                        </script>
                    </body>
                    </html>
                    """,
                    height=600,
                    scrolling=True
                )
            else:
                st.warning(f"Không tìm thấy ảnh cho EAN {ean}")

    # Checkbox ở cuối – chỉ hiển thị trạng thái mở
    if st.checkbox("📌 Hiện/ẩn chi tiết (bấm để ẩn)", value=st.session_state[show_key], key=f"{show_key}_check"):
        pass
    else:
        st.warning("👉 Hãy bấm lại vào tiêu đề phía trên để thu gọn phần này.")



# python -m streamlit run "5-Check EAN to buy.py"

