import os
import requests
from linebot import LineBotApi
from linebot.models import TextSendMessage

LINE_CLIENT_ID = os.getenv("LINE_CLIENT_ID")
LINE_CLIENT_SECRET = os.getenv("LINE_CLIENT_SECRET")
LINE_REDIRECT_URI = os.getenv("LINE_REDIRECT_URI")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_REPLY_URL = "https://api.line.me/v2/bot/message/reply"

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)

def get_line_login_url():
    return (
        "https://access.line.me/oauth2/v2.1/authorize"
        "?response_type=code"
        f"&client_id={LINE_CLIENT_ID}"
        f"&redirect_uri={LINE_REDIRECT_URI}"
        "&state=random_state"
        "&scope=profile%20openid"
    )


def get_line_profile(code):
    token_url = "https://api.line.me/oauth2/v2.1/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": LINE_REDIRECT_URI,
        "client_id": LINE_CLIENT_ID,
        "client_secret": LINE_CLIENT_SECRET,
    }

    token_res = requests.post(token_url, headers=headers, data=payload).json()
    access_token = token_res.get("access_token")
    if not access_token:
        return None

    profile_res = requests.get(
        "https://api.line.me/v2/profile",
        headers={"Authorization": f"Bearer {access_token}"},
    ).json()

    return {
        "line_user_id": profile_res.get("userId"),
        "display_name": profile_res.get("displayName"),
    }


def reply_message(reply_token: str, messages: list[dict]) -> int:
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    body = {"replyToken": reply_token, "messages": messages}
    res = requests.post(LINE_REPLY_URL, headers=headers, json=body)
    return res.status_code


def flex_welcome_message(username: str) -> list[dict]:
    return [
        {
            "type": "flex",
            "altText": "ยินดีต้อนรับ",
            "contents": {
                "type": "bubble",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": f"ยินดีต้อนรับ {username}",
                            "weight": "bold",
                            "size": "lg",
                        },
                        {"type": "text", "text": "คลิกเพื่อเชื่อมบัญชี", "margin": "md"},
                        {
                            "type": "button",
                            "style": "primary",
                            "action": {
                                "type": "uri",
                                "label": "เชื่อมบัญชี",
                                "uri": "https://your-website.com/line-login",
                            },
                        },
                    ],
                },
            },
        }
    ]


def push_text_message(user_id: str, text: str) -> None:
    try:
        line_bot_api.push_message(user_id, TextSendMessage(text=text))
    except Exception as exc:  # pragma: no cover - network call
        print("Error sending message:", exc)
