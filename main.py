import os
import google.generativeai as genai
from flask import Flask, request, abort
from psn_api import PSNApi
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent, ImageMessageContent

app = Flask(__name__)

# --- 🔐 各種設定（RenderのEnvironmentで設定してください） ---
LINE_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
NPSSO_TOKEN = os.environ.get("PSN_NPSSO_TOKEN")

# --- 🧠 AIの「人格」と「能力」の設定 ---
instruction = """
あなたは、以下の3つの役割を完璧にこなす親しみやすいAIパートナーです。
1. **数学の専門家**: 小学生の算数から大学レベルの高度な数学まで、ステップバイステップで丁寧に解説してください。
2. **英語の先生**: ネイティブレベルの英語力を持ち、自然な会話や翻訳を行ってください。
3. **親しみやすい友達**: 日常会話では親身に接してください。

【制約】
- 数学や英語の解説が必要な場合は詳しく説明してください。
- それ以外の日常雑談は短めに返してください。
"""

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=instruction
)

conf = Configuration(access_token=LINE_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# --- 💬 テキストメッセージを受け取った時の処理 ---
@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    user_message = event.message.text

    # 🎮 1. PSNフレンドリスト判定（最優先）
    if "フレンド" in user_message:
        try:
            api = PSNApi(npsso=NPSSO_TOKEN)
            friends = api.get_friends()
            names = [f"・{f.online_id}" for f in friends[:20]]
            reply_text = f"🎮 PSNフレンド一覧（合計 {len(friends)}人）:\n" + "\n".join(names)
            if len(friends) > 20:
                reply_text += f"\n\n他 {len(friends)-20}人は省略したよ。"
        except Exception as e:
            # トークン切れや設定ミスの場合にエラーを表示
            reply_text = f"PSNエラーが発生したよ。トークンの期限切れかも？\n{str(e)}"
    
    # 🧠 2. それ以外（数学・英語・日常会話）はGemini
    else:
        response = model.generate_content(user_message)
        reply_text = response.text.strip()

    reply_to_line(event.reply_token, reply_text)

# --- 🖼️ 画像を受け取った時の処理（修正済み 🌟） ---
@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image_message(event):
    with ApiClient(conf) as api_client:
        messaging_api = MessagingApi(api_client)
        
        # 修正ポイント: 画像データを最後まで読み込んで結合する
        message_content = messaging_api.get_message_content(event.message.id)
        image_bytes = b"".join([chunk for chunk in message_content]) 
        
        # 修正されたデータを使ってGeminiに送る
        response = model.generate_content([
            "この画像の内容を解析してください。数学の問題なら詳しく解き、英語なら翻訳や解説、それ以外なら説明をして。",
            {"mime_type": "image/jpeg", "data": image_bytes}
        ])
        
        reply_to_line(event.reply_token, response.text.strip())

def reply_to_line(reply_token, text):
    with ApiClient(conf) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(ReplyMessageRequest(
            reply_token=reply_token,
            messages=[TextMessage(text=text)]
        ))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
