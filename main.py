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
# 小学生の算数から大学数学（微積分・線形代数・統計など）まで解説でき、
# かつネイティブレベルの英語教師としての役割も持たせます。
instruction = """
あなたは、以下の3つの役割を完璧にこなす親しみやすいAIパートナーです。
1. **数学の専門家**: 小学生の算数から大学レベルの高度な数学（微積分、線形代数、解析学、統計学など）まで、ステップバイステップで丁寧に解説してください。数式は分かりやすく表示して。
2. **英語の先生**: ネイティブレベルの英語力を持ち、英語での会話、翻訳、英文添削、学習のアドバイスを自然に行ってください。
3. **親しみやすい友達**: 日常会話では親身に、かつ楽しく接してください。

【制約】
- 数学や英語の解説が必要な場合は、文字数を気にせず詳しく説明してください。
- それ以外の日常的な雑談は、LINEで読みやすいよう短めに返してください。
"""

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=instruction  # 🌟 ここで能力を注入！
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

    # 🎮 PSNフレンドリスト表示
    if "フレンド" in user_message:
        try:
            api = PSNApi(npsso=NPSSO_TOKEN)
            friends = api.get_friends()
            names = [f"・{f.online_id}" for f in friends[:20]]
            reply_text = f"🎮 PSNフレンド一覧（合計 {len(friends)}人）:\n" + "\n".join(names)
            if len(friends) > 20:
                reply_text += f"\n\n他 {len(friends)-20}人は省略したよ。"
        except Exception as e:
            reply_text = f"エラー：PSN情報を取得できなかったよ...\n{str(e)}"
    
    # 🧠 数学・英語・日常会話（Geminiにお任せ）
    else:
        # system_instructionがあるため、シンプルなプロンプトでOKです
        response = model.generate_content(user_message)
        reply_text = response.text.strip()

    reply_to_line(event.reply_token, reply_text)

# --- 🖼️ 画像を受け取った時の処理 ---
@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image_message(event):
    with ApiClient(conf) as api_client:
        messaging_api = MessagingApi(api_client)
        message_content = messaging_api.get_message_content(event.message.id)
        
        # 画像内の数式も読み取って解くことができます！
        response = model.generate_content([
            "この画像の内容を解析してください。数学の問題なら詳しく解き、英語なら翻訳や解説、それ以外なら説明をして。",
            {"mime_type": "image/jpeg", "data": message_content}
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
