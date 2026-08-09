#!/usr/bin/env python3
"""
Telegram Bot: Welcome new users + IPTV troubleshooting helper
"""

import logging
import os
from typing import Optional, Tuple

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatMember,
    ChatMemberUpdated,
    Chat,
)
from telegram.constants import ParseMode, ChatMemberStatus
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ChatMemberHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ============== CONFIG ==============
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set!")

WELCOME_MESSAGE = (
    "👋 Welcome {mention} to <b>{chat_title}</b>!\n\n"
    "I'm here to help with IPTV issues.\n"
    "Type /help or use the buttons below to get started."
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

IPTV_HELPS = {
    "quick": {
        "title": "⚡ Quick Fixes (try these first)",
        "text": (
            "<b>Most IPTV problems are fixed in under 2 minutes:</b>\n\n"
            "1. <b>Restart your streaming device</b> — power it off completely, wait 30 seconds, then turn it back on.\n"
            "2. <b>Restart your router/modem</b> — unplug from the wall, wait 60 seconds, plug modem first, then router.\n"
            "3. <b>Test internet speed</b> on the same device (need ≥10 Mbps for HD, ≥25 Mbps for 4K).\n"
            "4. <b>Clear IPTV app cache</b> and reopen the app.\n"
            "5. <b>Confirm subscription is active</b> — expired plans cause login/channel errors.\n\n"
            "Still stuck? Choose a specific problem below."
        ),
    },
    "buffering": {
        "title": "📺 Buffering / Freezing",
        "text": (
            "<b>Buffering is the #1 IPTV complaint.</b>\n\n"
            "<b>Most common causes & fixes:</b>\n"
            "• <b>Wi-Fi issues</b> → Switch to Ethernet (biggest fix). Use a USB Ethernet adapter for Firestick/Android boxes.\n"
            "• <b>Weak signal</b> → Use 5 GHz Wi-Fi, move closer to router, reduce interference.\n"
            "• <b>ISP throttling</b> → Try a good VPN (often solves peak-hour buffering).\n"
            "• <b>App settings</b> → Increase buffer size (e.g. TiviMate: Settings → Player → Buffer Size → Very Large).\n"
            "• <b>Lower quality</b> → Switch from 4K/HD to a lower stream if available.\n"
            "• Close other downloads/streaming on the network.\n"
            "• Change DNS to 1.1.1.1 (Cloudflare) or 8.8.8.8 (Google).\n\n"
            "Run a speed test on the device itself while the problem happens."
        ),
    },
    "login": {
        "title": "🔑 Login / Authorization Errors",
        "text": (
            "<b>“Failed to Authorize”, “Invalid credentials”, “Connection Error”</b>\n\n"
            "Usually one of these:\n"
            "• <b>Expired subscription</b> — Check your provider portal or email.\n"
            "• <b>Wrong credentials</b> — Copy-paste username/password/URL exactly (no extra spaces).\n"
            "• <b>Wrong server URL</b> — Make sure it includes http:// or https:// and is the correct portal.\n"
            "• <b>Too many connections</b> — Some plans limit simultaneous devices. Log out elsewhere.\n"
            "• Clear app data/cache and re-enter credentials.\n"
            "• Try a different IPTV player app (TiviMate, IPTV Smarters, XCIPTV, etc.).\n\n"
            "If using M3U: re-import the playlist URL.\n"
            "If using Xtream Codes: double-check host, username, password."
        ),
    },
    "blackscreen": {
        "title": "⬛ Black Screen / No Video",
        "text": (
            "<b>Audio plays but screen is black, or complete blank screen</b>\n\n"
            "Fixes to try:\n"
            "• Change video decoder / player engine in app settings (Hardware ↔ Software, or try ExoPlayer / VLC / Native).\n"
            "• Restart the streaming device and the app.\n"
            "• Test the same channel on another device — if it fails everywhere, it’s the provider/channel.\n"
            "• Check HDMI cable and TV input.\n"
            "• Update the IPTV app and device firmware.\n"
            "• Clear app cache.\n"
            "• Try a different player app entirely."
        ),
    },
    "epg": {
        "title": "📅 EPG / Guide Not Showing",
        "text": (
            "<b>Electronic Program Guide missing or outdated</b>\n\n"
            "• Force an EPG update / refresh in the app.\n"
            "• Verify the EPG URL is correct (or switch to Xtream Codes which often includes EPG).\n"
            "• Clear app cache and restart.\n"
            "• Make sure the playlist/EPG source is still valid from your provider.\n"
            "• Some apps need “Update EPG” or a manual reload after adding the playlist.\n"
            "• Check that your device date/time is set correctly (automatic)."
        ),
    },
    "channels": {
        "title": "📋 Channels Not Loading / Empty List",
        "text": (
            "<b>No channels appear or playlist won’t load</b>\n\n"
            "• Re-enter or re-import your M3U / Xtream credentials (copy-paste carefully).\n"
            "• Clear app cache and data, then re-add the playlist.\n"
            "• Check if the provider changed the portal URL or is under maintenance.\n"
            "• Confirm your subscription is active.\n"
            "• Try another IPTV player.\n"
            "• If only some categories are missing, it may be a temporary provider-side issue."
        ),
    },
    "audio": {
        "title": "🔊 Audio Issues (no sound / out of sync)",
        "text": (
            "<b>No audio or audio/video out of sync</b>\n\n"
            "• Pause and resume the stream.\n"
            "• Switch audio track in the player (if multiple are available).\n"
            "• Change player engine / enable hardware acceleration.\n"
            "• Restart the app and device.\n"
            "• Lower the buffer size slightly or switch player.\n"
            "• Check device volume and TV/soundbar settings."
        ),
    },
    "general": {
        "title": "🛠️ General Tips",
        "text": (
            "<b>Extra advice for smoother IPTV:</b>\n\n"
            "• Prefer Ethernet over Wi-Fi whenever possible.\n"
            "• Keep your IPTV app and device software updated.\n"
            "• Use a reputable player: TiviMate (Android), IPTV Smarters, etc.\n"
            "• Avoid peak hours if your ISP throttles; a VPN can help.\n"
            "• Don’t share your credentials — it can get your account limited or banned.\n"
            "• If nothing works after trying the above, contact your IPTV provider with:\n"
            "  - Device + app name/version\n"
            "  - Exact error message\n"
            "  - What you already tried\n"
            "  - Speed test result"
        ),
    },
}


def get_main_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("⚡ Quick Fixes", callback_data="help_quick")],
        [
            InlineKeyboardButton("📺 Buffering", callback_data="help_buffering"),
            InlineKeyboardButton("🔑 Login Errors", callback_data="help_login"),
        ],
        [
            InlineKeyboardButton("⬛ Black Screen", callback_data="help_blackscreen"),
            InlineKeyboardButton("📅 EPG Issues", callback_data="help_epg"),
        ],
        [
            InlineKeyboardButton("📋 No Channels", callback_data="help_channels"),
            InlineKeyboardButton("🔊 Audio Issues", callback_data="help_audio"),
        ],
        [InlineKeyboardButton("🛠️ General Tips", callback_data="help_general")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("◀️ Back to menu", callback_data="help_menu")]]
    )


def extract_status_change(
    chat_member_update: ChatMemberUpdated,
) -> Optional[Tuple[bool, bool]]:
    status_change = chat_member_update.difference().get("status")
    old_is_member, new_is_member = chat_member_update.difference().get(
        "is_member", (None, None)
    )

    if status_change is None:
        return None

    old_status, new_status = status_change
    was_member = old_status in [
        ChatMemberStatus.MEMBER,
        ChatMemberStatus.OWNER,
        ChatMemberStatus.ADMINISTRATOR,
    ] or (old_status == ChatMemberStatus.RESTRICTED and old_is_member is True)
    is_member
