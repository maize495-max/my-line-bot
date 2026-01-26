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
# セキュリティのため、本来はこれらも環境変数（os.environ）にするのがベストです
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
    # スプレッドシート名「line_bot_memory」の最初のシートを開く
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
    # ユーザーからのメッセージ（前後の空白を削除）
    user_text = event.message.text.strip()
    sheet = get_sheet()
    reply_text = ""

    # 1. 「教える：」で始まる場合の処理
    if user_text.startswith("教える："):
        try:
            # 「教える：」を消して中身を取り出す
            content = user_text.replace("教える：", "")
            
            # 全角「、」を半角「,」に統一してから分割
            parts = content.replace("、", ",").split(",")

            if len(parts) == 2:
                keyword = parts[0].strip()
                response = parts[1].strip()
                
                if keyword and response:
                    sheet.append_row([keyword, response])
                    reply_text = f"「{keyword}」って言われたら「{response}」って答えるように覚えたよ！"
                else:
                    reply_text = "言葉と返事を両方入力してね。"
            else:
                # 形式エラー時の返信（ループを防ぐため、ここには「教える：」を含めない）
                reply_text = "教え方は「教える：言葉,返事」の形で送ってね！"
        except Exception as e:
            reply_text = "登録中にエラーが起きたよ。時間を置いて試してね。"

    # 2. 登録済みの言葉を検索する処理
    else:
        try:
            records = sheet.get_all_records()
            found_response = None
            
            for record in records:
                # keyword列の値とユーザーの入力が一致するか確認
                if str(record.get('keyword')) == user_text:
                    found_response = record.get('response')
                    break
            
            if found_response:
                reply_text = found_response
            else:
                # 3. 未登録の場合（ここがループの最大の原因でした）
                # 返信に「教える：{user_text}」を含めず、固定の説明文にします
                reply_text = f"「{user_text}」はまだ知らないなぁ。下の形式で送ってくれたら覚えるよ！\n\n教える：言葉,返事"
        
        except Exception as e:
            reply_text = "スプレッドシートの読み込みでエラーが発生したよ。"

    # LINEへ返信を送信
    with ApiClient(conf) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )

if __name__ == "__main__":
    # Renderなどの環境に合わせてポートを指定
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
