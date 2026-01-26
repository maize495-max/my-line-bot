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
    # 【強化】すべての空白（全角・半角）を取り除き、記号を統一する
    raw_text = event.message.text.strip()
    # 判定用に、スペースを消してコロンを統一した文字列を作る
    normalized_text = raw_text.replace(" ", "").replace("　", "").replace(":", "：")
    
    sheet = get_sheet()
    reply_messages = []

    # 1. 特定の言葉へのスタンプ返信
    if raw_text == "お疲れ様":
        reply_messages.append(StickerMessage(packageId="446", stickerId="1989"))
        reply_messages.append(TextMessage(text="今日もお疲れ様！ゆっくり休んでね。"))

    # 2. 「教える：」で始まる場合の処理
    elif normalized_text.startswith("教える："):
        try:
            # 「教える：」を消して、残りを「,」で分割
            content = normalized_text.replace("教える：", "").replace("、", ",")
            parts = content.split(",")

            if len(parts) == 2:
                keyword = parts[0]
                response = parts[1]
                
                sheet.append_row([keyword, response])
                reply_messages.append(TextMessage(text=f"「{keyword}」って言われたら反応するように覚えたよ！"))
            else:
                reply_messages.append(TextMessage(text="教え方は「教える：言葉,返事」の形で送ってね！"))
        except Exception as e:
            reply_messages.append(TextMessage(text="登録エラーが発生したよ。"))

    # 3. 登録済みの言葉を検索
    else:
        try:
            records = sheet.get_all_records()
            found_response = None
            for record in records:
                # ユーザーが送ったそのままの文字で検索
                if str(record.get('keyword')) == raw_text:
                    found_response = record.get('response')
                    break
            
            if found_response:
                if found_response.startswith("STK:"):
                    stk_data = found_response.replace("STK:", "").split(",")
                    reply_messages.append(StickerMessage(packageId=stk_data[0].strip(), stickerId=stk_data[1].strip()))
                else:
                    reply_messages.append(TextMessage(text=found_response))
            else:
                reply_messages.append(TextMessage(text=f"「{raw_text}」はまだ知らないなぁ。教えてくれたら覚えるよ！\n\n教える：言葉,返答"))
        
        except Exception as e:
            reply_messages.append(TextMessage(text="読み込みエラーだよ。"))

    # 返信
    if reply_messages:
        with ApiClient(conf) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=reply_messages[:5]
                )
            )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
