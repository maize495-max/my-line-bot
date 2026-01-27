import os
import json
import gspread
from google.oauth2.service_account import Credentials
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage, StickerMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent

app = Flask(__name__)

# --- LINE設定 ---
conf = Configuration(access_token='yjobhTbQspZH6F/2Wq7xM7o23JbauiKXlrPNWI8Xm2grwm6i/jBriYvklRiywVMfpNrri9XrlkiAM9/cgzO+6V/PHR91sR+XNH4qx43Oo9VdKWheclWG7B85uiEoNPZhAzU3LXUa4xOLCk9tI0C2RQdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('bef8d0e0dfa3395715dead2aaecc450e')

# --- スプレッドシート設定 ---
def get_sheet():
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    json_str = os.environ.get('GOOGLE_SHEETS_JSON')
    if not json_str:
        raise ValueError("環境変数 GOOGLE_SHEETS_JSON が未設定です")
    json_data = json.loads(json_str)
    credentials = Credentials.from_service_account_info(json_data, scopes=scopes)
    gc = gspread.authorize(credentials)
    return gc.open('line_bot_memory').sheet1

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    raw_text = event.message.text
    # 【最強クリーニング】すべての空白を消し、記号を半角に統一
    norm = raw_text.replace(" ", "").replace("　", "").replace("：", ":").replace("，", ",").replace("、", ",")
    
    sheet = get_sheet()
    reply_messages = []

    if norm == "お疲れ様":
        reply_messages.append(StickerMessage(packageId="446", stickerId="1989"))
        reply_messages.append(TextMessage(text="今日もお疲れ様！ゆっくり休んでね。"))
    elif norm.startswith("教える:"):
        try:
            content = norm[4:]
            if "," in content:
                parts = content.split(",", 1)
                keyword = parts[0]
                response = parts[1]
                sheet.append_row([keyword, response])
                reply_messages.append(TextMessage(text=f"「{keyword}」の返し方を覚えたよ！"))
            else:
                reply_messages.append(TextMessage(text="教え方は「教える:言葉,返事」だよ！"))
        except:
            reply_messages.append(TextMessage(text="登録エラー。"))
    else:
        try:
            records = sheet.get_all_records()
            found_res = None
            for r in records:
                k = str(r.get('keyword')).replace(" ", "").replace("　", "")
                if k == norm:
                    found_res = r.get('response')
                    break
            if found_res:
                if found_res.startswith("STK:"):
                    stk = found_res.replace("STK:", "").replace("，", ",").split(",")
                    reply_messages.append(StickerMessage(packageId=stk[0].strip(), stickerId=stk[1].strip()))
                else:
                    reply_messages.append(TextMessage(text=found_res))
            else:
                reply_messages.append(TextMessage(text=f"「{raw_text}」はまだ知らないなぁ。"))
        except:
            reply_messages.append(TextMessage(text="読み込みエラー。"))

    if reply_messages:
        with ApiClient(conf) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=reply_messages[:5]))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
