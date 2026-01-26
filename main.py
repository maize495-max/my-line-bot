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

# LINE設定
# 415.jpgに写っていたあなたの正しいトークンとシークレットです
conf = Configuration(access_token='yjobhTbQspZH6F/2Wq7xM7o23JbauiKXlrPNWI8Xm2grwm6i/jBriYvklRiywVMfpNrri9XrlkiAM9/cgzO+6V/PHR91sR+XNH4qx43Oo9VdKWheclWG7B85uiEoNPZhAzU3LXUa4xOLCk9tI0C2RQdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('bef8d0e0dfa3395715dead2aaecc450e')

# スプレッドシート設定
def get_sheet():
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    # Renderの環境変数から鍵(JSON)を読み込みます
    json_str = os.environ.get('GOOGLE_SHEETS_JSON')
    if not json_str:
        raise ValueError("環境変数 GOOGLE_SHEETS_JSON が設定されていません")
    
    json_data = json.loads(json_str)
    credentials = Credentials.from_service_account_info(json_data, scopes=scopes)
    gc = gspread.authorize(credentials)
    # スプレッドシート名「line_bot_memory」を開きます
    return gc.open('line_bot_memory').sheet1

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    text = event.message.text
    sheet = get_sheet()
    reply_text = ""

    # 「教える：」で始まる場合の処理
    if text.startswith("教える："):
        try:
            # 「教える：」を消して、カンマか全角カンマで分割
            content = text.replace("教える：", "")
            if "," in content:
                parts = content.split(",")
            elif "、" in content:
                parts = content.split("、")
            else:
                parts = []

            if len(parts) == 2:
                keyword = parts[0].strip()
                response = parts[1].strip()
                # シートの最後に行を追加
                sheet.append_row([keyword, response])
                reply_text = f"「{keyword}」って言われたら「{response}」って答えるように覚えたよ！"
            else:
                reply_text = "教え方は「教える：言葉,返事」って送ってね！"
        except Exception as e:
            reply_text = f"エラー：{str(e)}\nスプレッドシートの共有設定を確認してね！"
    
    else:
        # スプレッドシートから言葉を検索
        records = sheet.get_all_records()
        for record in records:
            if record.get('keyword') == text:
                reply_text = record.get('response')
                break
        
        # 見つからなかった場合
        if not reply_text:
            reply_text = f"「{text}」はまだ知らないなぁ。「教える：{text},（返事）」って送ってくれたら覚えるよ！"

    with ApiClient(conf) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )

if __name__ == "__main__":
    app.run(port=5000)
