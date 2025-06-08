import streamlit as st
import pandas as pd
import os
import re
import base64

st.set_page_config(layout="wide")

EXCEL_PATH = "Qogita Analyse v3_check+JEWLWW(photo).xlsx"
IMAGE_DIR = "SellerampPhoto"

df = pd.read_excel(EXCEL_PATH)

if "filter_mode" not in st.session_state:
    st.session_state.filter_mode = False

col_filter, col_status = st.columns([1, 5])
with col_filter:
    if st.button("🔍 Lọc Mua Hay Ko"):
        st.session_state.filter_mode = not st.session_state.filter_mode
with col_status:
    if st.session_state.filter_mode:
        st.success("Đang lọc: chỉ các dòng chưa có quyết định Mua Hay Ko")
    else:
        st.info("Hiển thị toàn bộ sản phẩm")

if st.session_state.filter_mode:
    df = df[df["Mua Hay Ko"].isna()]

# Ưu tiên cột EAN đầu tiên
if "EAN" in df.columns:
    df = df[["EAN"] + [c for c in df.columns if c != "EAN"]]

# Sắp xếp theo Sale
df["__sale_order"] = df["Sale"].astype(str).apply(
    lambda s: float(re.search(r"(\d+(\.\d+)?)/mo", s).group(1)) if re.search(r"(\d+(\.\d+)?)/mo", s) else -1
)
df = df.sort_values("__sale_order", ascending=False).drop(columns=["__sale_order"])

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

selected_page = st.selectbox("Chọn trang", range(1, num_pages + 1), index=st.session_state.page - 1)
st.session_state.page = selected_page
start_idx = (selected_page - 1) * page_size
end_idx = start_idx + page_size

st.title("🔎 Qogita Visual Decision Tool")

for idx in range(start_idx, min(end_idx, len(df))):
    row = df.iloc[idx]
    row_id = row.name
    ean = str(row["EAN"])
    key_toggle = f"show_{row_id}"

    # Khởi tạo trạng thái nếu chưa có
    if key_toggle not in st.session_state:
        st.session_state[key_toggle] = False

    # Click vào tiêu đề để mở chi tiết
    if st.button(f"▶️ #{idx+1} | EAN: {ean} | Sale: {row.get('Sale','')} | BSR: {row.get('BSR','')} | Seller: {row.get('Seller','')}", key=f"title_{row_id}"):
        st.session_state[key_toggle] = True

    if st.session_state[key_toggle]:
        col1, col2 = st.columns([1, 5])
        with col1:
            # Mua hay không
            options = ["", "Y", "N"]
            mua_val = row.get("Mua Hay Ko", "")
            default_index = options.index(mua_val) if mua_val in options else 0
            decision = st.selectbox("📌 Mua Hay Ko", options, index=default_index, key=f"dec_{row_id}")

            if st.button("✅ Cập nhật", key=f"save_{row_id}"):
                df.at[row_id, "Mua Hay Ko"] = decision
                df.to_excel(EXCEL_PATH, index=False)
                st.success("Đã lưu!")

            # Links
            if row.get("Product Link"):
                st.markdown(f"[🔗 Link Qogita]({row['Product Link']})")
            st.markdown(f"[🔗 Link Selleramp](https://sas.selleramp.com/sas/lookup?search_term={ean})")
            if row.get("Link Amazon.fr"):
                st.markdown(f"[🔗 Link Amazon.fr]({row['Link Amazon.fr']})")

        with col2:
            fields = ["EAN", "Prix Qogita", "Prix amazon", "ASIN", "Coeff", "Profit"]
            for f in fields:
                if f in row:
                    st.markdown(f"**{f}**: {row[f]}")

            img_path = os.path.join(IMAGE_DIR, f"{ean}.png")
            if os.path.exists(img_path):
                with open(img_path, "rb") as img_file:
                    encoded = base64.b64encode(img_file.read()).decode()

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
                st.warning("❌ Không tìm thấy ảnh")

        # Checkbox để ẩn chi tiết
        if not st.checkbox("Ẩn chi tiết dòng này", key=f"hide_{row_id}"):
            pass
        else:
            st.session_state[key_toggle] = False



# python -m streamlit run "5-Check EAN to buy.py"

