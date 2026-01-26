import os
import json
import gspread
from google.oauth2.service_account import Credentials
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent

app = Flask(__name__)

# --- LINE設定 ---
# アクセストークンとシークレット
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
    # スプレッドシート名「line_bot_memory」を開く
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
    # 【改善】入力された文字の半角「:」を全角「：」に統一して、判定ミスを防ぐ
    original_text = event.message.text.strip()
    normalized_text = original_text.replace(":", "：")
    
    sheet = get_sheet()
    reply_text = ""

    # 1. 「教える：」で始まる場合の処理
    if normalized_text.startswith("教える："):
        try:
            # 「教える：」を除去
            content = normalized_text.replace("教える：", "")
            
            # 【改善】「、」と「,」の両方に対応
            content = content.replace("、", ",")
            parts = content.split(",")

            if len(parts) == 2:
                keyword = parts[0].strip()
                response = parts[1].strip()
                
                if keyword and response:
                    # スプレッドシートに保存
                    sheet.append_row([keyword, response])
                    reply_text = f"「{keyword}」って言われたら「{response}」って答えるように覚えたよ！"
                else:
                    reply_text = "言葉と返事を両方入力してね。"
            else:
                reply_text = "教え方は「教える：言葉,返事」の形で送ってね！"
        except Exception as e:
            print(f"Error in append_row: {e}")
            reply_text = "ごめん、スプレッドシートに書き込めなかったよ。共有設定を確認してね。"

    # 2. 登録済みの言葉を検索する処理
    else:
        try:
            records = sheet.get_all_records()
            found_response = None
            
            for record in records:
                # スプレッドシートのkeyword列と一致するか（全角半角の差を無視するため正規化後の文字で比較）
                if str(record.get('keyword')) == original_text:
                    found_response = record.get('response')
                    break
            
            if found_response:
                reply_text = found_response
            else:
                # 【改善】ループ防止のため、返信に「教える：」という文字を入れない
                reply_text = f"「{original_text}」はまだ知らないなぁ。下の形式で送ってくれたら覚えるよ！\n\n教える：言葉,返答"
        
        except Exception as e:
            print(f"Error in get_records: {e}")
            reply_text = "スプレッドシートがうまく読み込めないみたい。"

    # LINEへ返信
    with ApiClient(conf) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )

if __name__ == "__main__":
    # Renderのポート番号に対応
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
