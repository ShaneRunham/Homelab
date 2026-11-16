"""The conversation entity: send the sentence (plus conversation, user and device ids) to the JARVIS service."""
import asyncio
import logging

from wyoming.asr import Transcript
from wyoming.client import AsyncTcpClient
from wyoming.handle import Handled, NotHandled

from homeassistant.components import conversation
from homeassistant.const import MATCH_ALL
from homeassistant.helpers import intent
from homeassistant.util import ulid as ulid_util

_LOGGER = logging.getLogger(__name__)
HOST, PORT = "127.0.0.1", 10400
TIMEOUT = 330  # the service gives up after 300 s


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([JarvisClaudeEntity(entry)])


class JarvisClaudeEntity(conversation.ConversationEntity, conversation.AbstractConversationAgent):
    _attr_has_entity_name = True
    _attr_name = None
    # No CONTROL feature on purpose (2026-11-12): with it, HA sends state questions ("is the light on?") to Claude
    # instead of answering them locally. Without it, HA's own intents answer everything they can, instantly.

    def __init__(self, entry):
        super().__init__()
        self._attr_unique_id = entry.entry_id
        self._attr_device_info = None

    @property
    def supported_languages(self):
        return MATCH_ALL

    async def async_process(self, user_input: conversation.ConversationInput) -> conversation.ConversationResult:
        conversation_id = user_input.conversation_id or ulid_util.ulid_now()
        response = intent.IntentResponse(language=user_input.language)
        context = {"conversation_id": conversation_id, "user_id": user_input.context.user_id}
        if user_input.device_id:
            context["device_id"] = user_input.device_id
        try:
            async with asyncio.timeout(TIMEOUT), AsyncTcpClient(HOST, PORT) as client:
                await client.write_event(Transcript(user_input.text, context=context, language=user_input.language).event())
                while True:
                    event = await client.read_event()
                    if event is None:
                        raise OSError("connection closed")
                    if Handled.is_type(event.type):
                        response.async_set_speech(Handled.from_event(event).text or "")
                        break
                    if NotHandled.is_type(event.type):
                        response.async_set_error(intent.IntentResponseErrorCode.FAILED_TO_HANDLE,
                                                 NotHandled.from_event(event).text or "")
                        break
        except (OSError, TimeoutError) as err:
            _LOGGER.warning("JARVIS service unreachable: %s", err)
            response.async_set_speech("Sorry Shane, my brain on the PC isn't answering.")
        return conversation.ConversationResult(response=response, conversation_id=conversation_id)
