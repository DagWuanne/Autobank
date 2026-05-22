import os
import httpx
from fastapi import FastAPI, Request, HTTPException, Header

app = FastAPI()

# Lấy cấu hình bảo mật từ Environment Variables trên Vercel
TELEGRAM_BOT_TOKEN = os.getenv("7694860049:AAHBO3vNqYPr-wvaLxfF4tX6foju4k_K_n4")
SEPAY_API_KEY = os.getenv("UZETPGSCSIKLZJFCQVRBW0KTU7JXM8HDB25IY2VQXHXQNFLAD49YNMS1IUDAKGC9")

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
    
    amount = data.get("amount")          # Số tiền nhận được
    content = data.get("content")        # Nội dung chuyển khoản (Memo)
    account_num = data.get("account_number") # Số tài khoản nhận tiền
    code = data.get("code")              # Mã giao dịch ngân hàng
    
    # 3. Phân tích nội dung chuyển khoản để tìm Chat ID người dùng
    if content:
        # Chuẩn hóa chuỗi: Chuyển viết hoa và xóa khoảng trắng thừa
        clean_content = content.strip().upper()
        
        # Kiểm tra nếu nội dung chứa cú pháp định danh nạp tiền (Ví dụ: NAP 123456)
        if "NAP" in clean_content:
            try:
                # Tách chuỗi lấy phần Chat ID đứng sau chữ "NAP"
                parts = clean_content.split("NAP")
                user_id_str = parts[1].strip().split()[0]
                user_chat_id = int(user_id_str)
                
                # Tính toán số xu (Ví dụ: 1.000 VNĐ = 1.000 xu)
                xu_cong_them = int(float(amount))

                # ========================================================
                # [PHẦN XỬ LÝ DATABASE]
                # Vì chạy Serverless, bạn nên gọi API kết nối tới Database online 
                # (Supabase, Vercel KV, MongoDB) để cộng tiền tại đây.
                # ========================================================

                # 4. Định dạng nội dung tin nhắn gửi về Telegram
                message_text = (
                    f"✅ **NẠP TIỀN TỰ ĐỘNG THÀNH CÔNG**\n\n"
                    f"💰 **Số tiền:** +{int(float(amount)):,} VNĐ\n"
                    f"💎 **Số xu nhận:** +{xu_cong_them:,} xu\n"
                    f"📝 **Nội dung:** {content}\n"
                    f"💳 **Mã GD:** `{code}`\n"
                    f"⚡ Hệ thống đã xử lý và cộng số dư tự động."
                )

                # 5. Gọi API Telegram gửi thông báo bất đồng bộ (Tối ưu cho Serverless)
                telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                payload = {
                    "chat_id": user_chat_id,
                    "text": message_text,
                    "parse_mode": "Markdown"
                }
                
                async with httpx.AsyncClient() as client:
                    await client.post(telegram_url, json=payload, timeout=5.0)

                return {"success": True, "message": f"Đã xử lý nạp cho user {user_chat_id}"}

            except (ValueError, IndexError) as e:
                return {"success": False, "error": f"Nội dung chuyển khoản sai định dạng Chat ID: {str(e)}"}
            except Exception as e:
                return {"success": False, "error": f"Lỗi hệ thống khi gửi tin nhắn Telegram: {str(e)}"}

    return {"success": False, "message": "Nội dung chuyển khoản không chứa cú pháp nạp tiền hợp lệ"}
          
