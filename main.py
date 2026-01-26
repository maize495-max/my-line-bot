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
    # 送信されたそのままのテキスト
    raw_text = event.message.text.strip()
    
    # 【改良】判定用に、記号の全角半角や空白をすべて整える
    # コロンを半角に、コンマ類を半角に、空白をすべて削除
    norm = raw_text.replace("：", ":").replace("，", ",").replace("、", ",").replace(" ", "").replace("　", "")
    
    sheet = get_sheet()
    reply_messages = []

    # 1. 固定返信：お疲れ様（文字が完全一致したとき）
    if raw_text == "お疲れ様":
        reply_messages.append(StickerMessage(packageId="446", stickerId="1989"))
        reply_messages.append(TextMessage(text="今日もお疲れ様！ゆっくり休んでね。"))

    # 2. 学習モード：教える（整えた文字が「教える:」で始まるとき）
    elif norm.startswith("教える:"):
        try:
            # 「教える:」の4文字目以降を取り出す
            content = norm[4:]
            
            # 最初の1つ目のコンマだけで分割（スタンプIDのコンマと混ざらないように）
            if "," in content:
                parts = content.split(",", 1)
                keyword = parts[0].strip()
                response = parts[1].strip()
                
                if keyword and response:
                    sheet.append_row([keyword, response])
                    reply_messages.append(TextMessage(text=f"「{keyword}」って言われたら「{response}」って返すように覚えたよ！"))
                else:
                    reply_messages.append(TextMessage(text="教え方が正しくないみたい。もう一度確認してね。"))
            else:
                reply_messages.append(TextMessage(text="「教える:言葉,返事」の形で送ってね！"))
        except:
            reply_messages.append(TextMessage(text="スプレッドシートへの登録でエラーが起きたよ。"))

    # 3. 登録済みワードの検索
    else:
        try:
            records = sheet.get_all_records()
            found_res = None
            for r in records:
                # スプレッドシートのkeyword列と入力文字が一致するか
                if str(r.get('keyword')) == raw_text:
                    found_res = r.get('response')
                    break
            
            if found_res:
                # 返事が「STK:」で始まっていればスタンプとして送信
                if found_res.startswith("STK:"):
                    try:
                        # STK:の後をコンマで分けてパッケージIDとスタンプIDを取得
                        stk_data = found_res.replace("STK:", "").replace("，", ",").split(",")
                        reply_messages.append(StickerMessage(packageId=stk_data[0].strip(), stickerId=stk_data[1].strip()))
                    except:
                        reply_messages.append(TextMessage(text=found_res))
                else:
                    reply_messages.append(TextMessage(text=found_res))
            else:
                # 何も知らない場合
                reply_messages.append(TextMessage(text=f"「{raw_text}」はまだ知らないなぁ。\n教える:言葉,返事\nの形で教えてね！"))
        except:
            reply_messages.append(TextMessage(text="スプレッドシートの読み込みエラーだよ。"))

    # LINEへ返信
    if reply_messages:
        with ApiClient(conf) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message(
                ReplyMessageRequest(reply_token=event.reply_token, messages=reply_messages[:5])
            )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
