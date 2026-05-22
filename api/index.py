import os
import httpx
from fastapi import FastAPI, Request, HTTPException, Header

app = FastAPI()

# Cấu hình cứng Token trực tiếp (Vì bạn không dùng biến môi trường Environment Variables)
TELEGRAM_BOT_TOKEN = "7694860049:AAHBO3vNqYPr-wvaLxfF4tX6foju4k_K_n4"
SEPAY_API_KEY = "UZETPGSCSIKLZJFCQVRBW0KTU7JXM8HDB25IY2VQXHXQNFLAD49YNMS1IUDAKGC9"

@app.get("/")
def home():
    return {"status": "Webhook SePay cho Telegram Bot đang online trên Vercel!"}

@app.post("/sepay-webhook")
async def receive_sepay_webhook(request: Request, authorization: str = Header(None)):
    # 1. Xác thực gói tin bảo mật từ SePay gửi tới
    if not authorization or f"Bearer {SEPAY_API_KEY}" != authorization:
        raise HTTPException(status_code=401, detail="Xác thực Webhook thất bại!")

    # 2. Đọc gói dữ liệu JSON từ SePay
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Dữ liệu JSON không hợp lệ")
    
    # Lấy đúng trường dữ liệu theo định dạng chuẩn của SePay gửi qua Webhook
    amount = data.get("transferAmount", 0)  # SePay dùng 'transferAmount' chứ không phải 'amount'
    content = data.get("content", "")       # Nội dung chuyển khoản (Memo)
    code = data.get("code", "")             # Mã giao dịch ngân hàng
    transfer_type = data.get("transferType", "in")

    # Chỉ xử lý các giao dịch tiền vào
    if transfer_type != "in" or int(float(amount)) <= 0:
        return {"success": True, "message": "Không phải giao dịch tiền vào"}
    
    # 3. Phân tích nội dung chuyển khoản để tìm Chat ID người dùng
    if content:
        # Chuẩn hóa chuỗi: Chuyển viết hoa và xóa khoảng trắng thừa
        clean_content = content.strip().upper()
        
        # Kiểm tra nếu nội dung chứa cú pháp định danh nạp tiền (Hỗ trợ cả NAP và NAP_)
        if "NAP" in clean_content:
            try:
                # Tách chuỗi lấy phần Chat ID đứng sau chữ "NAP"
                # Ví dụ: "NAP 7694860049" hoặc "NAP_7694860049" -> lấy được "7694860049"
                import re
                match = re.search(r'NAP_?(\d+)', clean_content)
                if not match:
                    return {"success": False, "message": "Nội dung chuyển khoản sai định dạng số Chat ID"}
                
                user_chat_id = int(match.group(1))
                xu_cong_them = int(float(amount))

                # 4. Định dạng nội dung tin nhắn gửi về Telegram
                message_text = (
                    f"✅ **NẠP TIỀN TỰ ĐỘNG THÀNH CÔNG**\n\n"
                    f"💰 **Số tiền:** +{int(float(amount)):?} VNĐ\n"
                    f"💎 **Số xu nhận:** +{xu_cong_them:,} xu\n"
                    f"📝 **Nội dung:** {content}\n"
                    f"💳 **Mã GD:** `{code}`\n\n"
                    f"⚡ Hệ thống đã xử lý và cộng số dư tự động thành công!"
                )

                # 5. Gọi API Telegram gửi thông báo
                telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                payload = {
                    "chat_id": user_chat_id,
                    "text": message_text,
                    "parse_mode": "Markdown"
                }
                
                async with httpx.AsyncClient() as client:
                    await client.post(telegram_url, json=payload, timeout=5.0)

                return {"success": True, "message": f"Đã xử lý nạp cho user {user_chat_id}"}

            except Exception as e:
                return {"success": False, "error": f"Lỗi hệ thống: {str(e)}"}

    return {"success": False, "message": "Nội dung chuyển khoản không hợp lệ"}
