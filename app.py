# -*- coding: utf-8 -*-
"""
TRỢ LÝ ẢO DU LỊCH PHIÊNG KHOÀI – Hợp phần 4, mô hình "Du lịch số Phiêng Khoài"
Chủ quản: UBND xã Phiêng Khoài. Chỉ trả lời dựa trên tài liệu đã kiểm duyệt trong thư mục du_lieu/.
"""
import csv
import glob
import os
from datetime import datetime

import streamlit as st

# ---------- 1. CẤU HÌNH ----------
# Bộ não AI: nếu có GEMINI_API_KEY thì dùng Google Gemini (gói miễn phí),
# nếu có ANTHROPIC_API_KEY thì dùng Claude (trả phí, chất lượng cao hơn).
NHA_CUNG_CAP = "gemini" if "GEMINI_API_KEY" in st.secrets else "claude"
MODEL_CLAUDE = "claude-haiku-5-5"
MODEL_GEMINI = st.secrets.get("GEMINI_MODEL", "gemini-4-hydrogen")
MODEL_GEMINI_DU_PHONG = ["gemini-4-hydrogen", "gemini-3-flash", "gemini-2.5-flash", "gemini-2.5-flash-lite"]
MAX_TOKENS = 700                     # độ dài tối đa mỗi câu trả lời
SO_LUOT_NHO = 6                      # số lượt hội thoại gần nhất gửi kèm
HOTLINE = st.secrets.get("HOTLINE", "[số điện thoại UBND xã]")
NHAT_KY = "nhat_ky_cau_hoi.csv"      # minh chứng: số câu hỏi đã trả lời

st.set_page_config(page_title="Trợ lý du lịch Phiêng Khoài", page_icon="🌸")


# ---------- 2. NẠP TÀI LIỆU ĐÃ KIỂM DUYỆT ----------
@st.cache_data
def nap_du_lieu():
    phan = []
    # Đọc dữ liệu trong thư mục du_lieu/ và cả các file .md đặt ngay ở thư mục gốc
    ds = glob.glob("du_lieu/*.md") + [
        f for f in glob.glob("*.md")
        if not f.lower().startswith(("readme", "huong_dan"))
    ]
    for duong_dan in sorted(set(ds), key=os.path.basename):
        with open(duong_dan, encoding="utf-8") as f:
            ten = os.path.basename(duong_dan)
            phan.append(f'<tai_lieu ten="{ten}">\n{f.read()}\n</tai_lieu>')
    return "\n\n".join(phan)


# ---------- 3. CHỈ DẪN HỆ THỐNG (quy tắc trả lời) ----------
CHI_DAN = f"""Bạn là Trợ lý ảo du lịch của Ủy ban nhân dân xã Phiêng Khoài, tỉnh Sơn La.

QUY TẮC BẮT BUỘC:
1. Chỉ trả lời dựa trên nội dung trong các thẻ <tai_lieu> bên dưới. Không dùng hiểu biết bên ngoài để nêu số liệu, giá, giờ mở cửa, ngày lễ hội, tên người.
2. Nội dung ghi "[cần bổ sung]", "[cần xác minh]" hoặc nằm trong ngoặc vuông là CHƯA CÓ thông tin chính thức: không được nêu ra như sự thật. Nếu tài liệu không có thông tin, nói rõ là chưa có thông tin chính thức và đề nghị du khách liên hệ UBND xã Phiêng Khoài theo số {HOTLINE}. Không đoán.
3. Trả lời bằng đúng ngôn ngữ của câu hỏi: tiếng Việt, tiếng Lào (ພາສາລາວ) hoặc tiếng Anh.
4. Ngắn gọn, lịch sự, thân thiện; tối đa khoảng 150 từ; dùng gạch đầu dòng khi liệt kê.
5. Không hỏi, không ghi nhận thông tin cá nhân của du khách (số định danh, địa chỉ, số tài khoản…).
6. Tôn trọng văn hóa các dân tộc; khi nói về Di tích Lao Khô, trình bày đúng nội dung tài liệu, trang trọng.
7. Về hang Tà Ẻn: luôn nhắc du khách không tự ý vào hang, phải đi cùng người dẫn đường địa phương.
8. Không trả lời nội dung ngoài phạm vi du lịch, văn hóa, dịch vụ tại xã; lịch sự từ chối và gợi ý câu hỏi phù hợp.

TÀI LIỆU:
{nap_du_lieu()}
"""


# ---------- 4. GHI NHẬT KÝ (phục vụ minh chứng sáng kiến) ----------
def ghi_nhat_ky(cau_hoi, thanh_cong):
    moi = not os.path.exists(NHAT_KY)
    with open(NHAT_KY, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if moi:
            w.writerow(["thoi_gian", "do_dai_cau_hoi", "thanh_cong"])
        # chỉ lưu thời gian và độ dài, KHÔNG lưu nội dung để bảo vệ dữ liệu cá nhân
        w.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), len(cau_hoi), thanh_cong])


# ---------- 5. GỌI BỘ NÃO AI ----------
def hoi_ai(tin_nhan):
    if NHA_CUNG_CAP == "gemini":
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
        noi_dung = [{"role": "user" if t["role"] == "user" else "model",
                     "parts": [{"text": t["content"]}]} for t in tin_nhan]
        # Thử lần lượt các mô hình: mô hình khai báo trong Secrets trước, rồi các mô hình dự phòng
        loi_cuoi = None
        for model in dict.fromkeys([MODEL_GEMINI] + MODEL_GEMINI_DU_PHONG):
            try:
                kq = client.models.generate_content(
                    model=model,
                    contents=noi_dung,
                    config=types.GenerateContentConfig(system_instruction=CHI_DAN,
                                                       max_output_tokens=MAX_TOKENS),
                )
                if kq.text:
                    return kq.text
            except Exception as loi:
                loi_cuoi = loi
                print(f"LỖI mô hình {model}:", repr(loi), flush=True)
                # Lỗi khóa API hoặc hết hạn mức thì không cần thử mô hình khác
                if any(x in str(loi) for x in ("API key", "API_KEY", "PERMISSION_DENIED", "429", "RESOURCE_EXHAUSTED")):
                    break
        raise loi_cuoi or RuntimeError("Không nhận được câu trả lời từ Gemini")
    import anthropic
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    kq = client.messages.create(model=MODEL_CLAUDE, max_tokens=MAX_TOKENS,
                                system=CHI_DAN, messages=tin_nhan)
    return kq.content[0].text


# ---------- 6. GIAO DIỆN ----------
st.title("🌸 Trợ lý du lịch Phiêng Khoài")
st.caption("Phiên bản áp dụng thử · Mô hình “Du lịch số Phiêng Khoài” · UBND xã Phiêng Khoài, tỉnh Sơn La")
st.caption("Xin chào · ສະບາຍດີ · Hello — Hỏi bằng tiếng Việt, tiếng Lào hoặc tiếng Anh.")
st.info("Bạn đang trò chuyện với trợ lý ảo sử dụng trí tuệ nhân tạo (AI) do UBND xã Phiêng Khoài vận hành. "
        "Vui lòng không nhập thông tin cá nhân. Thông tin quan trọng xin liên hệ: " + HOTLINE)

if "lich_su" not in st.session_state:
    st.session_state.lich_su = []

for tin in st.session_state.lich_su:
    with st.chat_message(tin["role"]):
        st.markdown(tin["content"])

cau_hoi = st.chat_input("Nhập câu hỏi… / ພິມຄຳຖາມ… / Ask a question…")

if cau_hoi:
    st.session_state.lich_su.append({"role": "user", "content": cau_hoi})
    with st.chat_message("user"):
        st.markdown(cau_hoi)

    with st.chat_message("assistant"):
        try:
            tra_loi = hoi_ai(st.session_state.lich_su[-SO_LUOT_NHO:])
            ghi_nhat_ky(cau_hoi, True)
        except Exception as loi:
            tra_loi = ("Xin lỗi, hệ thống đang bận. Vui lòng thử lại sau hoặc liên hệ " + HOTLINE)
            ghi_nhat_ky(cau_hoi, False)
            print("LỖI:", repr(loi), flush=True)
            if str(st.secrets.get("SHOW_ERRORS", "0")) == "1":
                # Chỉ hiện khi quản trị bật SHOW_ERRORS = "1" trong Secrets; che khóa API nếu có
                chi_tiet = str(loi)
                for k in ("GEMINI_API_KEY", "ANTHROPIC_API_KEY"):
                    if k in st.secrets:
                        chi_tiet = chi_tiet.replace(str(st.secrets[k]), "***")
                st.error(f"[Chi tiết lỗi cho quản trị] {type(loi).__name__}: {chi_tiet[:600]}")
        st.markdown(tra_loi)

    st.session_state.lich_su.append({"role": "assistant", "content": tra_loi})
