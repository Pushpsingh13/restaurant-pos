import streamlit as st
import pandas as pd
from datetime import datetime
import os
import webbrowser
import threading
from io import BytesIO

# Try importing reportlab
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
except ImportError:
    canvas = None

# --- CONFIG ---
MENU_EXCEL = "DhalisMenu.xlsx"
ADMIN_PASSWORD = "admin123"  # change after first run

# --- SESSION STATE INIT ---
if "bill" not in st.session_state:
    st.session_state.bill = []
if "total" not in st.session_state:
    st.session_state.total = 0.0
if "cust_name" not in st.session_state:
    st.session_state.cust_name = ""
if "cust_phone" not in st.session_state:
    st.session_state.cust_phone = ""
if "cust_addr" not in st.session_state:
    st.session_state.cust_addr = ""
if "browser_opened" not in st.session_state:
    st.session_state.browser_opened = False

# --- PAGE CONFIG ---
st.set_page_config(page_title="Dhaliwal's Food Court POS", layout="wide")

# --- PAGE STYLING ---
st.markdown("""
<style>
.main {
    background: #fffaf0;
    padding: 20px;
}
.title {
    font-size: 34px;
    font-weight: bold;
    color: #2c2c2c;
}
.menu-card {
    padding: 15px;
    border-radius: 12px;
    background: white;
    text-align: center;
    margin-bottom: 12px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.15);
}
.touch-btn button {
    background-color: #ff7f50 !important;
    color: white !important;
    font-size: 18px !important;
    padding: 14px 10px !important;
    border-radius: 12px !important;
    width: 100%;
    margin-bottom: 10px;
}
.touch-btn button:hover {
    background-color: #ff5722 !important;
}
</style>
""", unsafe_allow_html=True)

# --- MENU FUNCTIONS ---
def load_menu():
    try:
        df = pd.read_excel(MENU_EXCEL, engine="openpyxl")
        if not set(["Item", "Half", "Full"]).issubset(df.columns):
            raise ValueError("Excel must have 'Item', 'Half', and 'Full' columns")
        df["Half"] = pd.to_numeric(df["Half"], errors='coerce').fillna(0)
        df["Full"] = pd.to_numeric(df["Full"], errors='coerce').fillna(0)
        return df
    except FileNotFoundError:
        st.error(f"Menu file '{MENU_EXCEL}' not found. Please create it.")
        return pd.DataFrame(columns=["Item", "Half", "Full"])
    except Exception as e:
        st.error(f"Error loading menu: {e}")
        return pd.DataFrame(columns=["Item", "Half", "Full"])

def save_menu(df):
    try:
        df.to_excel(MENU_EXCEL, index=False, engine="openpyxl")
        return True
    except Exception as e:
        st.error(f"Failed to save menu: {e}")
        return False

# --- TEXT CLEANER ---
def clean_text(txt):
    if not txt:
        return "-"
    return str(txt).replace("\n", " ").replace("\r", " ").encode("ascii", "ignore").decode()

# --- BILL FUNCTIONS ---
def add_to_bill(item, price, size):
    st.session_state.bill.append({"item": item, "price": price, "size": size})
    st.session_state.total += price

def clear_bill():
    st.session_state.bill = []
    st.session_state.total = 0.0
    st.session_state.cust_name = ""
    st.session_state.cust_phone = ""
    st.session_state.cust_addr = ""

# --- PDF RECEIPT ---
def build_pdf_receipt():
    if canvas is None:
        st.error("ReportLab is not installed. Please run: pip install reportlab")
        return None

    buffer = BytesIO()
    thermal_width = 80 * mm
    thermal_height = 200 * mm
    c = canvas.Canvas(buffer, pagesize=(thermal_width, thermal_height))

    y = thermal_height - 10
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(thermal_width / 2, y, "Dhaliwal's Food Court")
    y -= 12
    c.setFont("Helvetica", 8)
    c.drawCentredString(thermal_width / 2, y, "Meerut, UP | Ph: +91-9259317713")
    y -= 10
    c.line(0, y, thermal_width, y)
    y -= 12
    c.setFont("Helvetica", 8)
    c.drawString(2, y, f"Bill Time: {datetime.now().strftime('%d %b %Y %H:%M:%S')}")
    y -= 10
    c.drawString(2, y, f"Customer: {clean_text(st.session_state.cust_name)}")
    y -= 10
    c.drawString(2, y, f"Phone: {clean_text(st.session_state.cust_phone)}")
    y -= 10
    c.drawString(2, y, f"Address: {clean_text(st.session_state.cust_addr)}")
    y -= 10
    c.line(0, y, thermal_width, y)
    y -= 12
    c.setFont("Helvetica-Bold", 8)
    c.drawString(2, y, "Item")
    c.drawRightString(thermal_width - 2, y, "Price")
    y -= 10
    c.setFont("Helvetica", 8)

    subtotal = 0
    for row in st.session_state.bill:
        c.drawString(2, y, clean_text(f"{row['item']} ({row['size']})"))
        c.drawRightString(thermal_width - 2, y, f"₹{row['price']:.2f}")
        subtotal += row["price"]
        y -= 10

    tax_rate = 5.0
    tax = subtotal * (tax_rate / 100)
    discount = 0.0
    grand_total = subtotal + tax - discount

    c.line(0, y, thermal_width, y)
    y -= 12
    c.setFont("Helvetica-Bold", 8)
    c.drawString(2, y, "Subtotal")
    c.drawRightString(thermal_width - 2, y, f"₹{subtotal:.2f}")
    y -= 10
    c.drawString(2, y, f"Tax ({tax_rate:.1f}%)")
    c.drawRightString(thermal_width - 2, y, f"₹{tax:.2f}")
    y -= 10
    c.drawString(2, y, "Discount")
    c.drawRightString(thermal_width - 2, y, f"-₹{discount:.2f}")
    y -= 10
    c.drawString(2, y, "Grand Total")
    c.drawRightString(thermal_width - 2, y, f"₹{grand_total:.2f}")
    y -= 14
    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(thermal_width / 2, y, "Thank you for visiting!")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# --- MAIN APP ---
menu_df = load_menu()
st.markdown('<p class="title">Dhaliwal\'s Food Court POS</p>', unsafe_allow_html=True)
st.markdown("*Date:* " + datetime.now().strftime("%d %b %Y %H:%M"))

# --- ADMIN PANEL ---
with st.sidebar:
    st.header("Admin Panel")
    password = st.text_input("Enter Admin Password", type="password")
    if password == ADMIN_PASSWORD:
        st.success("Logged in as Admin")
        st.subheader("Edit Menu")
        edited_df = st.data_editor(menu_df, num_rows="dynamic")
        if st.button("Save Menu Changes"):
            if save_menu(edited_df):
                st.success("Menu saved successfully!")
                st.rerun()
        st.divider()
        st.subheader("Delete Menu Item")
        if not menu_df.empty:
            delete_item = st.selectbox("Select item to delete", menu_df["Item"])
            if st.button("Delete Selected Item"):
                menu_df = menu_df[menu_df["Item"] != delete_item]
                if save_menu(menu_df):
                    st.success(f"'{delete_item}' removed from menu.")
                    st.rerun()
        else:
            st.info("Menu is empty.")
    elif password:
        st.error("Incorrect password")

# --- POS INTERFACE ---
col1, col2 = st.columns([2, 1])

with col1:
    st.header("Menu")
    if not menu_df.empty:
        num_columns = 3
        cols = st.columns(num_columns)
        for index, row in menu_df.iterrows():
            with cols[index % num_columns]:
                st.markdown(f'<div class="menu-card"><h4>{row["Item"]}</h4></div>', unsafe_allow_html=True)
                if row["Half"] > 0:
                    if st.button(f"Half - ₹{row['Half']:.2f}", key=f"half_{index}"):
                        add_to_bill(row["Item"], row["Half"], "Half")
                if row["Full"] > 0:
                    if st.button(f"Full - ₹{row['Full']:.2f}", key=f"full_{index}"):
                        add_to_bill(row["Item"], row["Full"], "Full")
    else:
        st.warning("Menu is empty. Please add items via Admin Panel.")

with col2:
    st.header("Current Bill")
    if st.session_state.bill:
        bill_df = pd.DataFrame(st.session_state.bill)
        st.dataframe(bill_df, use_container_width=True)
        st.markdown(f"<h3>Total: ₹{st.session_state.total:.2f}</h3>", unsafe_allow_html=True)

        st.session_state.cust_name = st.text_input("Customer Name", value=st.session_state.cust_name)
        st.session_state.cust_phone = st.text_input("Customer Phone", value=st.session_state.cust_phone)
        st.session_state.cust_addr = st.text_area("Customer Address", value=st.session_state.cust_addr)

        pdf_buffer = build_pdf_receipt()
        if pdf_buffer:
            st.download_button(
                label="Print Thermal Receipt PDF",
                data=pdf_buffer,
                file_name="receipt.pdf",
                mime="application/pdf"
            )

        if st.button("Clear Bill"):
            clear_bill()
            st.rerun()
    else:
        st.info("No items added yet.")

# --- AUTO OPEN BROWSER (Only once) ---
def open_browser():
    webbrowser.open_new("http://localhost:8501")

if __name__ == "__main__" and not st.session_state.browser_opened:
    threading.Timer(1, open_browser).start()
    st.session_state.browser_opened = True