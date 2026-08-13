"""Audio and Volume management tools for querying and adjusting Windows system audio."""

from typing import Any

from pydantic import BaseModel, Field

from app.tools.base.metadata import ToolMetadata
from app.tools.base.permissions import ToolPermission
from app.tools.base.risk import ToolRiskLevel
from app.tools.base.tool import BaseTool
from app.tools.categories import ToolCategory
from app.tools.models.errors import ToolErrorCode, ToolExecutionError

# Global in-memory audio state fallback for virtualized/test environments
_MOCK_AUDIO_STATE: dict[str, Any] = {
    "volume": 50,
    "is_muted": False,
}


def _get_audio_endpoint():
    """Attempt to initialize Windows Core Audio Endpoint volume interface via pycaw / comtypes."""
    try:
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return interface.QueryInterface(IAudioEndpointVolume)
    except Exception:  # noqa: BLE001
        return None


# 1. Get Volume Tool
class GetVolumeInput(BaseModel):
    """Input parameters for GetVolumeTool."""


class GetVolumeTool(BaseTool):
    """Tool querying Windows master volume level and mute state."""

    def __init__(self) -> None:
        meta = ToolMetadata(
            tool_id="audio.get_volume",
            name="get_volume",
            display_name="Get Audio Volume",
            description="Queries system master volume percentage (0-100) and mute status.",
            category=ToolCategory.MEDIA,
            tags=["audio", "volume", "sound", "media"],
            input_schema=GetVolumeInput,
            risk_level=ToolRiskLevel.LOW,
            permissions=[ToolPermission.SYSTEM_SETTINGS],
            confirmation_required=False,
            idempotent=True,
            retryable=True,
        )
        super().__init__(metadata=meta)

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        endpoint = _get_audio_endpoint()
        if endpoint:
            try:
                vol = round(endpoint.GetMasterVolumeLevelScalar() * 100)
                muted = bool(endpoint.GetMute())
                return {"volume": vol, "is_muted": muted}
            except Exception as exc:  # noqa: BLE001
                _MOCK_AUDIO_STATE["error"] = str(exc)

        return {
            "volume": _MOCK_AUDIO_STATE["volume"],
            "is_muted": _MOCK_AUDIO_STATE["is_muted"],
        }


# 2. Set Volume Tool
class SetVolumeInput(BaseModel):
    """Input parameters for SetVolumeTool."""

    volume: int = Field(ge=0, le=100, description="Target volume percentage (0 to 100)")


class SetVolumeTool(BaseTool):
    """Tool adjusting Windows master volume percentage."""

    def __init__(self) -> None:
        meta = ToolMetadata(
            tool_id="audio.set_volume",
            name="set_volume",
            display_name="Set Audio Volume",
            description="Sets master audio volume percentage (0-100).",
            category=ToolCategory.MEDIA,
            tags=["audio", "volume", "sound", "media"],
            input_schema=SetVolumeInput,
            risk_level=ToolRiskLevel.LOW,
            permissions=[ToolPermission.SYSTEM_SETTINGS],
            confirmation_required=False,
            idempotent=True,
        )
        super().__init__(metadata=meta)

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        inp: SetVolumeInput = validated_input  # type: ignore
        target_vol = inp.volume

        endpoint = _get_audio_endpoint()
        if endpoint:
            try:
                endpoint.SetMasterVolumeLevelScalar(target_vol / 100.0, None)
                _MOCK_AUDIO_STATE["volume"] = target_vol
                return {"volume": target_vol, "success": True}
            except Exception as exc:
                raise ToolExecutionError(
                    error_code=ToolErrorCode.EXECUTION_FAILED,
                    message=f"Failed to set audio volume: {exc}",
                    tool_id=self.tool_id,
                ) from exc

        _MOCK_AUDIO_STATE["volume"] = target_vol
        return {"volume": target_vol, "success": True}


# 3. Mute Audio Tool
class MuteAudioInput(BaseModel):
    """Input parameters for MuteAudioTool."""


class MuteAudioTool(BaseTool):
    """Tool muting master audio output."""

    def __init__(self) -> None:
        meta = ToolMetadata(
            tool_id="audio.mute",
            name="mute",
            display_name="Mute Audio",
            description="Mutes system master audio output.",
            category=ToolCategory.MEDIA,
            tags=["audio", "mute", "sound", "media"],
            input_schema=MuteAudioInput,
            risk_level=ToolRiskLevel.LOW,
            permissions=[ToolPermission.SYSTEM_SETTINGS],
            confirmation_required=False,
            idempotent=True,
        )
        super().__init__(metadata=meta)

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        endpoint = _get_audio_endpoint()
        if endpoint:
            try:
                endpoint.SetMute(1, None)
                _MOCK_AUDIO_STATE["is_muted"] = True
                return {"is_muted": True, "success": True}
            except Exception as exc:
                raise ToolExecutionError(
                    error_code=ToolErrorCode.EXECUTION_FAILED,
                    message=f"Failed to mute audio: {exc}",
                    tool_id=self.tool_id,
                ) from exc

        _MOCK_AUDIO_STATE["is_muted"] = True
        return {"is_muted": True, "success": True}


# 4. Unmute Audio Tool
class UnmuteAudioInput(BaseModel):
    """Input parameters for UnmuteAudioTool."""


class UnmuteAudioTool(BaseTool):
    """Tool unmuting master audio output."""

    def __init__(self) -> None:
        meta = ToolMetadata(
            tool_id="audio.unmute",
            name="unmute",
            display_name="Unmute Audio",
            description="Unmutes system master audio output.",
            category=ToolCategory.MEDIA,
            tags=["audio", "unmute", "sound", "media"],
            input_schema=UnmuteAudioInput,
            risk_level=ToolRiskLevel.LOW,
            permissions=[ToolPermission.SYSTEM_SETTINGS],
            confirmation_required=False,
            idempotent=True,
        )
        super().__init__(metadata=meta)

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        endpoint = _get_audio_endpoint()
        if endpoint:
            try:
                endpoint.SetMute(0, None)
                _MOCK_AUDIO_STATE["is_muted"] = False
                return {"is_muted": False, "success": True}
            except Exception as exc:
                raise ToolExecutionError(
                    error_code=ToolErrorCode.EXECUTION_FAILED,
                    message=f"Failed to unmute audio: {exc}",
                    tool_id=self.tool_id,
                ) from exc

        _MOCK_AUDIO_STATE["is_muted"] = False
        return {"is_muted": False, "success": True}
