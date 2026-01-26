from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import random

app = Flask(__name__)

# アクセストークンとチャンネルシークレット
conf = Configuration(access_token='yjobhTbQspZH6F/2Wq7xM7o23JbauiKXlrPNWI8Xm2grwm6i/jBriYvklRiywVMfpNrri9XrlkiAM9/cgzO+6V/PHR91sR+XNH4qx43Oo9VdKWheclWG7B85uiEoNPZhAzU3LXUa4xOLCk9tI0C2RQdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('bef8d0e0dfa3395715dead2aaecc450e')

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
    reply_text = ""

    # --- 返答パターンの設定 ---
    if text == "おみくじ":
        results = ["大吉！最高の一日になります✨", "中吉。良いことあるかも！", "小吉。のんびりいきましょう🍵", "末吉。焦らず一歩ずつ。"]
        reply_text = random.choice(results)
        
    elif text in ["こんにちは", "ハロー", "hello"]:
        reply_text = "こんにちは！お話しできて嬉しいです。"
        
    elif text in ["おはよう", "おやすみ"]:
        reply_text = f"{text}！今日も素敵な日になりますように。"
        
    elif text == "名前は？":
        reply_text = "私はRender上で24時間動いている、あなたの専用ボットです！"
        
    elif text == "何ができるの？":
        reply_text = "「おみくじ」を引いたり、挨拶したりできます。これからもっと勉強します！"
        
    else:
        # 知らない言葉への対応（案内を出すと親切です）
        reply_text = f"「{text}」だね！まだその言葉はわからないけど、いつか覚えるよ。「おみくじ」って送ってみて！"

    # --- LINEに返信を送る ---
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
