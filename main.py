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
    original_text = event.message.text.strip()
    normalized_text = original_text.replace(":", "：")
    sheet = get_sheet()
    
    # 返信メッセージを格納するリスト
    reply_messages = []

    # 1. 【固定設定】特定の言葉へのスタンプ返信
    if original_text == "お疲れ様":
        # ブラウンの「お疲れ」スタンプ
        reply_messages.append(StickerMessage(packageId="446", stickerId="1989"))
        reply_messages.append(TextMessage(text="今日もお疲れ様！ゆっくり休んでね。"))

    # 2. 「教える：」で始まる場合の処理
    elif normalized_text.startswith("教える："):
        try:
            content = normalized_text.replace("教える：", "").replace("、", ",")
            parts = content.split(",")

            if len(parts) == 2:
                keyword = parts[0].strip()
                response = parts[1].strip()
                
                if keyword and response:
                    sheet.append_row([keyword, response])
                    reply_messages.append(TextMessage(text=f"「{keyword}」の返し方を覚えたよ！"))
                else:
                    reply_messages.append(TextMessage(text="言葉と返事を両方入力してね。"))
            else:
                reply_messages.append(TextMessage(text="教え方は「教える：言葉,返事」の形で送ってね！\nスタンプなら「教える：言葉,STK:パッケージID,スタンプID」だよ。"))
        except Exception as e:
            reply_messages.append(TextMessage(text="登録中にエラーが起きたよ。"))

    # 3. 登録済みの言葉を検索する処理
    else:
        try:
            records = sheet.get_all_records()
            found_response = None
            for record in records:
                if str(record.get('keyword')) == original_text:
                    found_response = record.get('response')
                    break
            
            if found_response:
                # 【新機能】スタンプ形式（STK:pkg,id）かチェック
                if found_response.startswith("STK:"):
                    try:
                        # "STK:446,1988" のような形式を分解
                        stk_data = found_response.replace("STK:", "").split(",")
                        pkg_id = stk_data[0].strip()
                        stk_id = stk_data[1].strip()
                        reply_messages.append(StickerMessage(packageId=pkg_id, stickerId=stk_id))
                    except:
                        reply_messages.append(TextMessage(text=found_response))
                else:
                    reply_messages.append(TextMessage(text=found_response))
            else:
                # 知らない言葉の場合
                reply_messages.append(TextMessage(text=f"「{original_text}」はまだ知らないなぁ。教えてくれたら覚えるよ！\n\n【教え方の例】\n教える：テスト,成功\n教える：合格,STK:446,2001"))
        
        except Exception as e:
            reply_messages.append(TextMessage(text="読み込みエラーが発生したよ。"))

    # LINEへ返信
    if reply_messages:
        with ApiClient(conf) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=reply_messages[:5] # 最大5件まで
                )
            )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
