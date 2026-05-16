"""
Telegram Bot for Digital Clone v3
==================================
Full-featured Telegram bot integrated with JarvisOrchestrator.

Features:
- Text messages -> Jarvis -> response
- Voice messages -> faster-whisper -> Jarvis -> response
- Commands: /start, /help, /status, /tasks, /autonomy
- Notifications from AutonomousLoop
- Admin-only commands for system control

Requires:
- python-telegram-bot >= 20.0
- faster-whisper (optional, for voice messages)
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set

from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logger = logging.getLogger("telegram_bot")


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class BotStats:
    """Runtime statistics for the bot."""

    messages_received: int = 0
    messages_sent: int = 0
    voice_processed: int = 0
    errors: int = 0
    started_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        uptime = time.time() - self.started_at
        return {
            "messages_received": self.messages_received,
            "messages_sent": self.messages_sent,
            "voice_processed": self.voice_processed,
            "errors": self.errors,
            "uptime_sec": round(uptime, 1),
            "uptime_human": f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m",
        }


# ---------------------------------------------------------------------------
# JarvisTelegramBot
# ---------------------------------------------------------------------------


class JarvisTelegramBot:
    """Telegram Bot that routes all messages through JarvisOrchestrator.

    Architecture:
        User (text/voice) -> Telegram API -> this bot -> Jarvis.process()
        -> Jarvis decides intent -> Worker executes -> Response sent back

    Voice pipeline:
        Voice file -> download -> faster_whisper transcribe -> text -> Jarvis

    Integration with AutonomousLoop:
        loop.send_notification(chat_id, text) sends alerts to admin users.
    """

    def __init__(
        self,
        jarvis: Any,
        token: Optional[str] = None,
        admin_chat_ids: Optional[List[int]] = None,
    ) -> None:
        """Initialize the bot.

        Args:
            jarvis: JarvisOrchestrator instance.
            token: Telegram Bot API token. If None, reads from TG_BOT_TOKEN env.
            admin_chat_ids: List of admin Telegram chat IDs for notifications.
        """
        self.jarvis = jarvis
        self.token = token or os.getenv("TG_BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
        self.admin_chat_ids: Set[int] = set(admin_chat_ids or [])
        self.stats = BotStats()

        # Whisper model (lazy init)
        self._whisper_model: Any = None
        self._whisper_available: Optional[bool] = None

        # Application (initialized in start())
        self.application: Optional[Application] = None
        self._running = False

        # Pending approvals (for autonomy level 1-2)
        self._pending_approvals: Dict[str, Dict[str, Any]] = {}

    # -- lifecycle -----------------------------------------------------------

    async def start(self) -> None:
        """Start the bot polling loop."""
        if not self.token:
            logger.error("TG_BOT_TOKEN not set. Bot cannot start.")
            return

        if self._running:
            logger.warning("Bot already running")
            return

        logger.info("Starting Telegram Bot...")

        self.application = (
            Application.builder()
            .token(self.token)
            .build()
        )

        # Register handlers
        self._register_handlers()

        await self.application.initialize()
        await self.application.start()
        self._running = True

        logger.info("Telegram Bot started. Polling for updates...")
        await self.application.updater.start_polling(drop_pending_updates=True)

    async def stop(self) -> None:
        """Stop the bot gracefully."""
        if not self._running or self.application is None:
            return

        logger.info("Stopping Telegram Bot...")
        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()
        self._running = False
        logger.info("Telegram Bot stopped")

    def _register_handlers(self) -> None:
        """Register all command and message handlers."""
        app = self.application
        if app is None:
            return

        # Commands
        app.add_handler(CommandHandler("start", self._cmd_start))
        app.add_handler(CommandHandler("help", self._cmd_help))
        app.add_handler(CommandHandler("status", self._cmd_status))
        app.add_handler(CommandHandler("tasks", self._cmd_tasks))
        app.add_handler(CommandHandler("autonomy", self._cmd_autonomy))
        app.add_handler(CommandHandler("stats", self._cmd_stats))

        # Messages
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text))
        app.add_handler(MessageHandler(filters.VOICE, self._handle_voice))

        # Error handler
        app.add_error_handler(self._handle_error)

    # -- command handlers ----------------------------------------------------

    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        user = update.effective_user
        chat_id = update.effective_chat.id

        # Auto-register admin if first user
        if not self.admin_chat_ids:
            self.admin_chat_ids.add(chat_id)
            logger.info("Auto-registered first user as admin: chat_id=%s", chat_id)

        welcome = (
            f"<b>Privet, {user.first_name}!</b>\n\n"
            f"Ya — <b>Jarvis</b>, tvoy AI-agent.\n"
            f"Mogu:\n"
            f"  • Sozdavat posty dlya socsetey\n"
            f"  • Generirovat shortsy\n"
            f"  • Pisat kod\n"
            f"  • Analizirovat trendi\n"
            f"  • Otvetat na voprosy\n\n"
            f"Prosto napishi mne tekstom ili golosovym soobsheniem.\n\n"
            f"Komandy:\n"
            f"/status — status systemy\n"
            f"/tasks — zadachi v rabote\n"
            f"/autonomy — uroven avtonomnosti\n"
            f"/help — pomosh"
        )
        await update.message.reply_text(welcome, parse_mode="HTML")

    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        help_text = (
            "<b>Jarvis — komandy:</b>\n\n"
            "/start — privetstvie\n"
            "/status — status systemy i provayderov\n"
            "/tasks — spisok aktivnyh zadach\n"
            "/autonomy — smenit uroven avtonomnosti (1/2/3)\n"
            "/stats — statistika bota\n\n"
            "<b>Primeri zaprosov:</b>\n"
            '• "Napishi post pro AI v prodazhah"\n'
            '• "Sozdai shortc pro MCP protokol"\n'
            '• "Pofiks blya s importom"\n'
            '• "Chto tam u konkurentov?"\n'
            '• "Sgenerirui kod parsera"\n\n'
            "Golosovie soobsheniya tozhe rabotayut!"
        )
        await update.message.reply_text(help_text, parse_mode="HTML")

    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command."""
        # LLM health
        llm_health = {}
        if hasattr(self.jarvis, "llm_router") and self.jarvis.llm_router:
            try:
                llm_health = await self.jarvis.llm_router.health_check()
            except Exception as exc:
                llm_health = {"error": str(exc)}

        active_llms = sum(1 for h in llm_health.values() if h) if isinstance(llm_health, dict) else 0
        total_llms = len(llm_health) if isinstance(llm_health, dict) else 0

        # Autonomy
        autonomy = getattr(self.jarvis, "autonomy", None)
        autonomy_str = autonomy.name if autonomy else "UNKNOWN"

        status_text = (
            f"<b>Status Systemy:</b>\n\n"
            f"LLM: {active_llms}/{total_llms} active\n"
            f"Avtonomiya: {autonomy_str}\n"
            f"Bot uptime: {self.stats.to_dict()['uptime_human']}\n"
            f"Soobsheniy: {self.stats.messages_received}"
        )
        await update.message.reply_text(status_text, parse_mode="HTML")

    async def _cmd_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /tasks command."""
        tasks = getattr(self.jarvis, "tasks", {})
        if not tasks:
            await update.message.reply_text("Net aktivnyh zadach.")
            return

        lines = ["<b>Aktivnye zadachi:</b>"]
        for task_id, task in list(tasks.items())[-10:]:
            status = getattr(task, "status", "?")
            desc = getattr(task, "description", "?")[:40]
            intent = getattr(task, "intent", "?")
            lines.append(f"  • {intent}: {desc}... ({status})")

        await update.message.reply_text("\n".join(lines), parse_mode="HTML")

    async def _cmd_autonomy(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /autonomy command. Set autonomy level."""
        args = context.args
        if not args:
            current = getattr(self.jarvis, "autonomy", None)
            current_str = current.name if current else "UNKNOWN"
            await update.message.reply_text(
                f"Tekushiy uroven avtonomnosti: <b>{current_str}</b>\n\n"
                f"Urovni:\n"
                f"  1 — MANUAL (vse na proverku)\n"
                f"  2 — ASSISTED (prostoe sam, slozhnoe — sprosit)\n"
                f"  3 — AUTONOMOUS (polnaya avtonomiya)\n\n"
                f"Ispolzuy: /autonomy 2"
            )
            return

        try:
            level = int(args[0])
            from core.jarvis_v3 import AutonomyLevel
            new_level = AutonomyLevel(level)
            self.jarvis.set_autonomy(new_level)
            await update.message.reply_text(
                f"Uroven avtonomnosti izmenen na: <b>{new_level.name}</b>"
            )
        except (ValueError, AttributeError) as exc:
            await update.message.reply_text(f"Oshibka: {exc}")

    async def _cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /stats command."""
        stats = self.stats.to_dict()
        text = (
            f"<b>Statistika bota:</b>\n\n"
            f"Soobsheniy polucheno: {stats['messages_received']}\n"
            f"Soobsheniy otpravleno: {stats['messages_sent']}\n"
            f"Golosovyh obrabotano: {stats['voice_processed']}\n"
            f"Oshibok: {stats['errors']}\n"
            f"Uptime: {stats['uptime_human']}"
        )
        await update.message.reply_text(text, parse_mode="HTML")

    # -- message handlers ----------------------------------------------------

    async def _handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming text messages."""
        if not update.message or not update.message.text:
            return

        self.stats.messages_received += 1
        user_text = update.message.text
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id if update.effective_user else 0

        logger.info("Text from chat_id=%s: %s...", chat_id, user_text[:60])

        # Typing indicator
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")

        # Process through Jarvis
        try:
            result = await self.jarvis.process(
                user_text,
                context={
                    "chat_id": chat_id,
                    "user_id": user_id,
                    "source": "telegram",
                },
            )
            response_text = self._extract_response_text(result)
        except Exception as exc:
            logger.exception("Jarvis processing error")
            self.stats.errors += 1
            response_text = f"Izvinite, proizoshla oshibka: {type(exc).__name__}"

        # Send response
        await self._send_response(context.bot, chat_id, response_text)

    async def _handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming voice messages."""
        if not update.message or not update.message.voice:
            return

        self.stats.messages_received += 1
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id if update.effective_user else 0

        logger.info("Voice from chat_id=%s", chat_id)
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")

        # Step 1: Download voice file
        try:
            voice_file = await context.bot.get_file(update.message.voice.file_id)
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
                tmp_path = tmp.name
            await voice_file.download_to_drive(tmp_path)
        except Exception as exc:
            logger.exception("Voice download error")
            self.stats.errors += 1
            await update.message.reply_text("Ne udalos skachat golosovoe soobshenie.")
            return

        # Step 2: Transcribe with faster-whisper
        try:
            transcript = await self._transcribe_audio(tmp_path)
            self.stats.voice_processed += 1
        except Exception as exc:
            logger.exception("Transcription error")
            self.stats.errors += 1
            await update.message.reply_text("Ne udalos raspoznat rech. Poprobuyte tekstom.")
            return
        finally:
            # Cleanup temp file
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception:
                pass

        if not transcript:
            await update.message.reply_text("Raspoznavanie vernulo pustoy tekst.")
            return

        logger.info("Transcribed: %s...", transcript[:60])

        # Show transcribed text
        await update.message.reply_text(f"<i>Raspoznano:</i> {transcript}", parse_mode="HTML")

        # Step 3: Process through Jarvis
        try:
            result = await self.jarvis.process(
                transcript,
                context={
                    "chat_id": chat_id,
                    "user_id": user_id,
                    "source": "telegram_voice",
                    "voice_transcript": transcript,
                },
            )
            response_text = self._extract_response_text(result)
        except Exception as exc:
            logger.exception("Jarvis processing error (voice)")
            self.stats.errors += 1
            response_text = f"Izvinite, proizoshla oshibka: {type(exc).__name__}"

        await self._send_response(context.bot, chat_id, response_text)

    # -- helpers -------------------------------------------------------------

    async def _send_response(self, bot: Bot, chat_id: int, text: str) -> None:
        """Send response text, splitting if too long."""
        if not text:
            text = "(pustoy otvet)"

        # Telegram limit: 4096 chars per message
        MAX_LEN = 4000
        chunks = []
        while len(text) > MAX_LEN:
            # Find last newline or space within limit
            split_at = text.rfind("\n", 0, MAX_LEN)
            if split_at == -1:
                split_at = text.rfind(" ", 0, MAX_LEN)
            if split_at == -1:
                split_at = MAX_LEN
            chunks.append(text[:split_at])
            text = text[split_at:].lstrip()
        chunks.append(text)

        for chunk in chunks:
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=chunk,
                    parse_mode="HTML",
                )
                self.stats.messages_sent += 1
            except Exception as exc:
                # If HTML parsing fails, send as plain text
                logger.warning("HTML send failed: %s. Retrying plain text.", exc)
                try:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=chunk,
                    )
                    self.stats.messages_sent += 1
                except Exception as exc2:
                    logger.error("Failed to send message: %s", exc2)
                    self.stats.errors += 1

    def _extract_response_text(self, jarvis_result: Dict[str, Any]) -> str:
        """Extract human-readable text from Jarvis result dict."""
        if not isinstance(jarvis_result, dict):
            return str(jarvis_result)

        result = jarvis_result.get("result")
        if isinstance(result, str):
            return result
        elif isinstance(result, dict):
            # Try common keys
            for key in ("content", "text", "analysis", "script", "output", "message"):
                if key in result:
                    val = result[key]
                    return str(val) if not isinstance(val, dict) else str(val)
            return str(result)
        elif result is not None:
            return str(result)

        # Fallback: show status
        status = jarvis_result.get("status", "unknown")
        intent = jarvis_result.get("intent", "unknown")
        return f"Zadacha vypolnena. Status: {status}, intent: {intent}."

    async def _transcribe_audio(self, audio_path: str) -> str:
        """Transcribe audio file using faster-whisper."""
        if self._whisper_available is False:
            raise RuntimeError("Whisper not available")

        if self._whisper_model is None:
            try:
                from faster_whisper import WhisperModel
                # Use CPU, INT8 quantization for speed
                self._whisper_model = WhisperModel(
                    "base",
                    device="cpu",
                    compute_type="int8",
                )
                self._whisper_available = True
                logger.info("Whisper model loaded (base, int8)")
            except Exception as exc:
                logger.error("Failed to load whisper: %s", exc)
                self._whisper_available = False
                raise

        if self._whisper_model is None:
            raise RuntimeError("Whisper model not loaded")

        segments, _ = self._whisper_model.transcribe(audio_path, language="ru")
        text_parts = [segment.text for segment in segments]
        return " ".join(text_parts).strip()

    async def _handle_error(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors in handlers."""
        logger.error("Handler error: %s", context.error, exc_info=context.error)
        self.stats.errors += 1
        if isinstance(update, Update) and update.effective_chat:
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Proizoshla vnutrennyaya oshibka. Poprobuyte pozzhe.",
                )
            except Exception:
                pass

    # -- notifications (called from AutonomousLoop) --------------------------

    async def send_notification(self, chat_id: int, text: str, parse_mode: str = "HTML") -> bool:
        """Send a notification message to a specific chat.

        Used by AutonomousLoop to send alerts, reports, and approvals.
        """
        if not self._running or self.application is None:
            logger.warning("Bot not running, cannot send notification")
            return False

        try:
            await self.application.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
            )
            self.stats.messages_sent += 1
            return True
        except Exception as exc:
            logger.error("Failed to send notification: %s", exc)
            self.stats.errors += 1
            return False

    async def broadcast_to_admins(self, text: str, parse_mode: str = "HTML") -> int:
        """Send a message to all admin chat IDs.

        Returns:
            Number of successfully sent messages.
        """
        if not self.admin_chat_ids:
            logger.warning("No admin chat IDs configured")
            return 0

        sent = 0
        for chat_id in self.admin_chat_ids:
            if await self.send_notification(chat_id, text, parse_mode):
                sent += 1
        return sent

    def add_admin(self, chat_id: int) -> None:
        """Add a chat ID to the admin list."""
        self.admin_chat_ids.add(chat_id)
        logger.info("Added admin chat_id: %s", chat_id)
