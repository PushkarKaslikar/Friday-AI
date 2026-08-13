"""Audio Device Manager encapsulating hardware enumeration, discovery, validation, and fallback."""

import threading

import sounddevice as sd

from app.exceptions.base import FridayBaseException
from app.logging import logger
from app.voice.audio.models import AudioDevice


class AudioDeviceError(FridayBaseException):
    """Exception raised for audio device discovery, selection, or capability failures."""

    def __init__(self, message: str, details: str = "") -> None:
        super().__init__(message=f"Audio Device Error: {message}", details=details)


class AudioDeviceManager:
    """Discovers, enumerates, validates, and selects hardware audio input and output devices."""

    def __init__(self) -> None:
        self._lock = threading.Lock()

    def get_all_devices(self) -> list[AudioDevice]:
        """Enumerate all system audio input and output devices.

        Returns:
            list[AudioDevice]: Strongly typed AudioDevice domain models.
        """
        with self._lock:
            try:
                raw_devices = sd.query_devices()
                host_apis = sd.query_hostapis()
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    f"AudioDeviceManager: Failed to query sounddevice devices: {exc}"
                )
                return []

            device_models: list[AudioDevice] = []
            for idx, dev in enumerate(raw_devices):
                api_name = "Unknown"
                api_idx = dev.get("hostapi", -1)
                if 0 <= api_idx < len(host_apis):
                    api_name = host_apis[api_idx].get("name", "Unknown")

                in_ch = int(dev.get("max_input_channels", 0))
                out_ch = int(dev.get("max_output_channels", 0))
                default_sr = int(dev.get("default_samplerate", 44100))

                device_models.append(
                    AudioDevice(
                        device_id=idx,
                        name=str(dev.get("name", f"Device #{idx}")),
                        host_api=api_name,
                        is_input=in_ch > 0,
                        is_output=out_ch > 0,
                        max_input_channels=in_ch,
                        max_output_channels=out_ch,
                        default_sample_rate=default_sr,
                        supported_sample_rates=self._determine_supported_rates(
                            idx, default_sr
                        ),
                        metadata={
                            "default_low_input_latency": dev.get(
                                "default_low_input_latency", 0.0
                            ),
                            "default_low_output_latency": dev.get(
                                "default_low_output_latency", 0.0
                            ),
                        },
                    )
                )

            return device_models

    def get_input_devices(self) -> list[AudioDevice]:
        """Enumerate available audio input devices (microphones)."""
        return [d for d in self.get_all_devices() if d.is_input]

    def get_output_devices(self) -> list[AudioDevice]:
        """Enumerate available audio output devices (speakers/headphones)."""
        return [d for d in self.get_all_devices() if d.is_output]

    def get_default_input_device(self) -> AudioDevice | None:
        """Identify the system default audio input device."""
        try:
            default_idx = sd.default.device[0]
            if default_idx is not None and default_idx >= 0:
                devices = self.get_all_devices()
                for d in devices:
                    if d.device_id == default_idx and d.is_input:
                        return d
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                f"AudioDeviceManager: Default input device query failed: {exc}"
            )

        # Fallback to first available input device
        input_devs = self.get_input_devices()
        return input_devs[0] if input_devs else None

    def get_default_output_device(self) -> AudioDevice | None:
        """Identify the system default audio output device."""
        try:
            default_idx = sd.default.device[1]
            if default_idx is not None and default_idx >= 0:
                devices = self.get_all_devices()
                for d in devices:
                    if d.device_id == default_idx and d.is_output:
                        return d
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                f"AudioDeviceManager: Default output device query failed: {exc}"
            )

        # Fallback to first available output device
        out_devs = self.get_output_devices()
        return out_devs[0] if out_devs else None

    def validate_input_device(
        self, device_id: int | str | None, sample_rate: int = 16000
    ) -> AudioDevice:
        """Validate input device selection and return AudioDevice model.

        Raises AudioDeviceError if device does not exist or is invalid.
        """
        if device_id is None:
            default_dev = self.get_default_input_device()
            if not default_dev:
                raise AudioDeviceError(
                    "No valid audio input devices (microphones) available on system."
                )
            return default_dev

        input_devs = self.get_input_devices()
        for dev in input_devs:
            if (
                str(dev.device_id) == str(device_id)
                or dev.name.lower() == str(device_id).lower()
            ):
                return dev

        # Fallback handling if configured device missing
        default_dev = self.get_default_input_device()
        if default_dev:
            logger.warning(
                f"AudioDeviceManager: Requested input device '{device_id}' missing. Falling back to default '{default_dev.name}'."
            )
            return default_dev

        raise AudioDeviceError(
            f"Requested input device '{device_id}' is not available on this system."
        )

    def validate_output_device(
        self, device_id: int | str | None, sample_rate: int = 16000
    ) -> AudioDevice:
        """Validate output device selection and return AudioDevice model.

        Raises AudioDeviceError if device does not exist or is invalid.
        """
        if device_id is None:
            default_dev = self.get_default_output_device()
            if not default_dev:
                raise AudioDeviceError(
                    "No valid audio output devices (speakers) available on system."
                )
            return default_dev

        output_devs = self.get_output_devices()
        for dev in output_devs:
            if (
                str(dev.device_id) == str(device_id)
                or dev.name.lower() == str(device_id).lower()
            ):
                return dev

        # Fallback handling if configured device missing
        default_dev = self.get_default_output_device()
        if default_dev:
            logger.warning(
                f"AudioDeviceManager: Requested output device '{device_id}' missing. Falling back to default '{default_dev.name}'."
            )
            return default_dev

        raise AudioDeviceError(
            f"Requested output device '{device_id}' is not available on this system."
        )

    def _determine_supported_rates(
        self, device_id: int, default_rate: int
    ) -> list[int]:
        """Query supported sample rates for a specific device index."""
        standard_rates = [16000, 44100, 48000]
        supported = [default_rate] if default_rate in standard_rates else []

        for rate in standard_rates:
            if rate not in supported:
                try:
                    sd.check_input_settings(device=device_id, samplerate=rate)
                    supported.append(rate)
                except Exception:  # noqa: BLE001
                    try:
                        sd.check_output_settings(device=device_id, samplerate=rate)
                        supported.append(rate)
                    except Exception:  # noqa: BLE001, S110
                        pass

        return sorted(set(supported))
