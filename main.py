import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, ImageMessage, TextSendMessage
import google.generativeai as genai

app = Flask(__name__)

# --- 🔑 設定（自分のキーを貼り付けてください） ---
LINE_CHANNEL_ACCESS_TOKEN = 'yjobhTbQspZH6F/2Wq7xM7o23JbauiKXlrPNWI8Xm2grwm6i/jBriYvklRiywVMfpNrri9XrlkiAM9/cgzO+6V/PHR91sR+XNH4qx43Oo9VdKWheclWG7B85uiEoNPZhAzU3LXUa4xOLCk9tI0C2RQdB04t89/1O/w1cDnyilFU='
LINE_CHANNEL_SECRET = 'bef8d0e0dfa3395715dead2aaecc450e'
genai.configure(api_key="AIzaSyCxqkSRDntWhFMCKJuS6IbkMzyd5gZNP5A")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# --- 🧠 AIのモデル設定（画像認識ができる1.5-flashを使用） ---
model = genai.GenerativeModel('gemini-1.5-flash')

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# 🖼️ 画像を受け取った時の処理
@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    # 1. LINEのサーバーから画像バイナリを取得
    message_content = line_bot_api.get_message_content(event.message.id)
    image_data = b""
    for chunk in message_content.iter_content():
        image_data += chunk

    # 2. Geminiに画像を渡して解析
    # 「この画像は何？」という質問と一緒に画像データを送ります
    response = model.generate_content([
        "この画像には何が写っていますか？日本語で詳しく説明してください。",
        {"mime_type": "image/jpeg", "data": image_data}
    ])

    # 3. 解析結果をLINEで返信
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=response.text)
    )

if __name__ == "__main__":
    app.run()
