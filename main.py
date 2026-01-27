import os
import json
import logging

import gspread
from flask import Flask, request, abort
from google.oauth2.service_account import Credentials

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    StickerMessage,
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    StickerMessageContent,
)

# ==============================
# logging 設定（★超重要）
# ==============================
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# ==============================
# LINE設定（環境変数）
# ==============================
conf = Configuration(
    access_token=os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
)

handler = WebhookHandler(
    os.environ.get("LINE_CHANNEL_SECRET")
)

# ==============================
# Google Sheets（今回は未使用でもOK）
# ==============================
def get_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    json_str = os.environ.get("GOOGLE_SHEETS_JSON")
    if not json_str:
        return None

    creds_dict = json.loads(json_str)
    credentials = Credentials.from_service_account_info(
        creds_dict, scopes=scopes
    )
    gc = gspread.authorize(credentials)
    return gc.open_by_key(
        os.environ.get("SPREADSHEET_KEY")
    ).sheet1


# ==============================
# Webhook 受信口
# ==============================
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)

    logging.info("REQUEST BODY: %s", body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"


# ==============================
# テキストメッセージ処理
# ==============================
@handler.add(MessageEvent, message=TextMessageContent)
def handle_text(event):
    text = event.message.text.strip()
    logging.info(f"TEXT EVENT: {text}")

    # 普通のテキスト返信
    with ApiClient(conf) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    TextMessage(text=f"受信したよ：{text}")
                ],
            )
        )


# ==============================
# ★スタンプメッセージ処理（ここが今回の核心）
# ==============================
@handler.add(MessageEvent, message=StickerMessageContent)
def handle_sticker(event):
    logging.info("STICKER EVENT")
    logging.info(
        f"package_id={event.message.package_id}, "
        f"sticker_id={event.message.sticker_id}"
    )

    # 受信したスタンプをそのまま返す
    with ApiClient(conf) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    StickerMessage(
                        package_id=event.message.package_id,
                        sticker_id=event.message.sticker_id,
                    )
                ],
            )
        )


# ==============================
# Render 起動用
# ==============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)