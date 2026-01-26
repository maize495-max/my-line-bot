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
# アクセストークンとチャンネルシークレットは以前のものを維持しています
conf = Configuration(access_token='yjobhTbQspZH6F/2Wq7xM7o23JbauiKXlrPNWI8Xm2grwm6i/jBriYvklRiywVMfpNrri9XrlkiAM9/cgzO+6V/PHR91sR+XNH4qx43Oo9VdKWheclWG7B85uiEoNPZhAzU3LXUa4xOLCk9tI0C2RQdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('bef8d0e0dfa3395715dead2aaecc450e')

# スプレッドシート設定
def get_sheet():
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    # Renderの環境変数(GOOGLE_SHEETS_JSON)から鍵を読み込みます
    json_str = os.environ.get('GOOGLE_SHEETS_JSON')
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

    # 学習コマンドの判定：「教える：キーワード,返事」
    if text.startswith("教える："):
        try:
            # 「教える：」を取り除いて、カンマで分割
            content = text.replace("教える：", "")
            if "," in content:
                parts = content.split(",")
            elif "、" in content: # 全角カンマにも対応
                parts = content.split("、")
            else:
                parts = []

            if len(parts) == 2:
                keyword = parts[0].strip()
                response = parts[1].strip()
                # スプレッドシートの末尾に行を追加
                sheet.append_row([keyword, response])
                reply_text = f"「{keyword}」って言われたら「{response}」って答えるように覚えたよ！"
            else:
                reply_text = "教え方は「教える：言葉,返事」って送ってね！"
        except Exception as e:
            reply_text = "覚えるのに失敗しちゃった。スプレッドシートの共有設定を確認してみて！"
    
    else:
        # スプレッドシートからすべてのデータを取得して言葉を検索
        records = sheet.get_all_records()
        for record in records:
            if record['keyword'] == text:
                reply_text = record['response']
                break
        
        # 見つからない場合のデフォルト返答
        if not reply_text:
            reply_text = f"「{text}」はまだ知らないなぁ。「教える：{text},（返答）」って送って教えてくれたら覚えるよ！"

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
