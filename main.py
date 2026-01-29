import os
import google.generativeai as genai
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent

app = Flask(__name__)

# LINE設定
conf = Configuration(access_token='yjobhTbQspZH6F/2Wq7xM7o23JbauiKXlrPNWI8Xm2grwm6i/jBriYvklRiywVMfpNrri9XrlkiAM9/cgzO+6V/PHR91sR+XNH4qx43Oo9VdKWheclWG7B85uiEoNPZhAzU3LXUa4xOLCk9tI0C2RQdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('bef8d0e0dfa3395715dead2aaecc450e')

# Gemini設定
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# ★制限回避用の「Lite」モデル
model = genai.GenerativeModel("models/gemini-2.5-flash-lite")

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
    try:
        # ボットの性格付け
        prompt = f"あなたは親しみやすい友達のようなAIです。30文字以内で短く返事をして。ユーザー: {event.message.text}"
        
        # Geminiに生成させる
        response = model.generate_content(prompt)
        reply_text = response.text.strip()
        
    except Exception as e:
        reply_text = f"エラー: {str(e)}"

    with ApiClient(conf) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(ReplyMessageRequest(
            reply_token=event.reply_token, 
            messages=[TextMessage(text=reply_text)]
        )) # ←ここが重要！カッコが閉じているか確認してください

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
