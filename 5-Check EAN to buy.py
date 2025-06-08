import streamlit as st
import pandas as pd
import os
from PIL import Image
import re
import base64
import numpy as np

# Cấu hình Streamlit phải nằm đầu tiên
st.set_page_config(layout="wide")

# Đường dẫn đến file Excel và thư mục chứa ảnh
EXCEL_PATH = "Qogita Analyse v3_check+JEWLWW(photo).xlsx"
IMAGE_DIR = "SellerampPhoto"

# Load dữ liệu Excel
df = pd.read_excel(EXCEL_PATH)

# Nút lọc theo cột "Mua Hay Ko"
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

# Đưa cột EAN về vị trí đầu tiên
if "EAN" in df.columns:
    cols = ["EAN"] + [col for col in df.columns if col != "EAN"]
    df = df[cols]

# Xử lý sắp xếp cột Sale
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

# Tạo tiêu đề ứng dụng
st.title("🔎 Qogita Visual Decision Tool")
st.markdown("Duyệt toàn bộ sản phẩm để xem ảnh và điền 'Mua Hay Ko'.")

# ✅ Nút tải file Excel đã cập nhật
with open(EXCEL_PATH, "rb") as f:
    st.download_button("📥 Tải file Excel đã cập nhật", f, file_name=os.path.basename(EXCEL_PATH))

# Phân trang
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

# Hiển thị sản phẩm theo trang
st.subheader(f"📋 Danh sách sản phẩm - Trang {selected_page}/{num_pages}")
with st.container():
    for idx in range(start_idx, min(end_idx, len(df))):
        selected_row = df.iloc[idx]
        raw_ean = str(selected_row["EAN"])
        ean = re.sub(r"[^0-9]", "", raw_ean)

        # Xử lý giá trị Mua Hay Ko để không hiển thị nan
        mua_value = selected_row.get("Mua Hay Ko", "")
        if pd.isna(mua_value):
            mua_value = ""

        product_link = selected_row.get("Product Link", "")
        amazon_link = selected_row.get("Link Amazon.fr", "")
        selleramp_link = f"https://sas.selleramp.com/sas/lookup?src=&ver=&SasLookup%5Bsearch_term%5D=%27{ean}&search_term={ean}&force_old_search"
        image_path = os.path.join(IMAGE_DIR, f"{ean}.png")
        sale = selected_row.get("Sale", "")
        seller = selected_row.get("Seller", "")
        bsr = selected_row.get("BSR", "")

        header_info = f"#{idx+1} | EAN: {raw_ean} | Mua: {mua_value} | Sale: {sale} | BSR: {bsr} | Seller: {seller}"

        with st.expander(header_info):
            col1, col2 = st.columns([1, 5])

            with col1:
                options = ["", "Y", "N"]
                default_index = 0
                if isinstance(mua_value, str) and mua_value in options:
                    default_index = options.index(mua_value)
                decision = st.selectbox(f"📌 Mua Hay Ko (#{idx+1})", options,
                                        index=default_index,
                                        key=f"decision_{idx}")

                if st.button(f"✅ Cập nhật dòng {selected_row.name+1}", key=f"btn_{idx}"):
                    df.at[selected_row.name, "Mua Hay Ko"] = decision
                    df.to_excel(EXCEL_PATH, index=False)
                    st.success(f"Đã cập nhật dòng {selected_row.name+1}!")

                if product_link:
                    st.markdown(f"[🔗 Link Qogita]({product_link})")
                st.markdown(f"[🔗 Link Selleramp]({selleramp_link})")
                if amazon_link:
                    st.markdown(f"[🔗 Link Amazon.fr]({amazon_link})")

            with col2:
                # Hiển thị các trường cụ thể
                fields_to_show = ["EAN", "Prix Qogita", "Prix amazon", "ASIN", "Coeff", "Profit"]
                for field in fields_to_show:
                    if field in selected_row:
                        st.markdown(f"**{field}**: {selected_row[field]}")

                # Hiển thị ảnh nếu có
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

# python -m streamlit run "5-Check EAN to buy.py"

