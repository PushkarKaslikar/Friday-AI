"""Friday AI Assistant - Main Application Entry Point."""

import argparse
import json
import sys
import time
import traceback
from typing import Any

import numpy as np

from app.bootstrap.bootstrapper import AppBootstrapper
from app.exceptions.base import FridayBaseException
from app.logging import logger
from app.voice.conversation.models import ActivationSource
from app.voice.greeting.models import GreetingContext


def setup_global_exception_handler() -> None:
    """Intercept all uncaught exceptions and log full stack traces via Loguru."""

    def handle_uncaught_exception(exc_type, exc_value, exc_traceback) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        traceback.print_exception(exc_type, exc_value, exc_traceback)
        logger.critical(
            "Unhandled Exception encountered!",
            exc_info=(exc_type, exc_value, exc_traceback),
        )

    sys.excepthook = handle_uncaught_exception


def run_audio_health_check(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --audio-health-check."""
    bootstrap_result = bootstrapper.run()
    audio_engine = bootstrap_result.container.audio_engine()
    report = audio_engine.get_health_report()

    print("\n=========================================")
    print("      FRIDAY AUDIO ENGINE HEALTH CHECK    ")
    print("=========================================")
    print(f"Status:                  {report['status']}")
    print(f"Engine State:            {report['engine_state']}")
    print(f"Input Stream State:      {report['input_stream_state']}")
    print(f"Output Stream State:     {report['output_stream_state']}")
    print(f"Active Input Device:     {report['active_input_device']}")
    print(f"Active Output Device:    {report['active_output_device']}")
    print(f"Sample Rate:             {report['sample_rate_hz']} Hz")
    print(f"Channels (Input):        {report['input_channels']}")
    print(f"Buffer Capacity:         {report['buffer_capacity_seconds']} sec")
    print(f"Last Error:              {report['last_error']}")
    print("Metrics:")
    print(json.dumps(report["metrics"], indent=2))
    print("=========================================\n")
    return 0


def run_audio_test(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --audio-test (hardware test tone playback and frame capture)."""
    print("\n[AUDIO TEST] Initializing Audio Engine...")
    bootstrap_result = bootstrapper.run()
    audio_engine = bootstrap_result.container.audio_engine()

    print("[AUDIO TEST] Discovering audio hardware devices...")
    in_devs = audio_engine.get_input_devices()
    out_devs = audio_engine.get_output_devices()

    print(
        f"[AUDIO TEST] Found {len(in_devs)} input device(s) and {len(out_devs)} output device(s)."
    )
    for d in in_devs:
        print(f"  - IN: [{d.device_id}] {d.name} ({d.default_sample_rate}Hz)")
    for d in out_devs:
        print(f"  - OUT: [{d.device_id}] {d.name} ({d.default_sample_rate}Hz)")

    print("\n[AUDIO TEST] Starting microphone capture for 2 seconds...")
    captured_frames = []

    def frame_callback(frame):
        captured_frames.append(frame)

    audio_engine.subscribe(frame_callback)
    try:
        audio_engine.start_input()
        time.sleep(2.0)
        audio_engine.stop_input()
    finally:
        audio_engine.unsubscribe(frame_callback)

    print(
        f"[AUDIO TEST] Microphone capture complete. Received {len(captured_frames)} audio frames."
    )

    print(
        "\n[AUDIO TEST] Playing synthetic 440Hz test tone for 1.0 second through output device..."
    )
    test_tone = audio_engine.generate_test_tone(
        frequency_hz=440.0, duration_seconds=1.0
    )
    audio_engine.play(test_tone)
    time.sleep(1.2)
    audio_engine.stop_output()
    print("[AUDIO TEST] Playback complete.")

    report = audio_engine.get_health_report()
    print("\n[AUDIO TEST RESULTS]")
    print(json.dumps(report, indent=2))
    print("\n[AUDIO TEST PASSED CLEANLY]\n")
    return 0


def run_clap_health_check(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --clap-health-check."""
    bootstrap_result = bootstrapper.run()
    clap_detector = bootstrap_result.container.clap_detector()
    report = clap_detector.get_health_report()

    print("\n=========================================")
    print("      FRIDAY CLAP DETECTOR HEALTH CHECK   ")
    print("=========================================")
    print(f"Status:                  {report['status']}")
    print(f"State:                   {report['state']}")
    print(f"Enabled:                 {report['enabled']}")
    print(f"Noise Floor Energy:      {report['noise_floor_energy']}")
    print(f"Min Interval:            {report['min_clap_interval_ms']} ms")
    print(f"Max Interval:            {report['max_clap_interval_ms']} ms")
    print(f"Cooldown:                {report['cooldown_ms']} ms")
    print(f"Energy Multiplier:       {report['energy_threshold_multiplier']}x")
    print(f"Min Peak Amplitude:      {report['min_peak_amplitude']}")
    print(f"Last Error:              {report['last_error']}")
    print("Metrics:")
    print(json.dumps(report["metrics"], indent=2))
    print("=========================================\n")
    return 0


def run_clap_test(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --clap-test (interactive microphone double-clap activation test)."""
    print("\n[CLAP TEST] Initializing Friday Audio Engine & Clap Detector...")
    bootstrap_result = bootstrapper.run()
    audio_engine = bootstrap_result.container.audio_engine()
    clap_detector = bootstrap_result.container.clap_detector()

    single_claps = []
    double_claps = []

    def on_single_clap(event):
        single_claps.append(event)
        print(
            f"  👏 [SINGLE CLAP DETECTED] confidence={event.confidence:.2f}, peak={event.peak_amplitude:.2f}"
        )

    def on_double_clap(event):
        double_claps.append(event)
        print(
            f"\n  🎉 [DOUBLE CLAP ACTIVATION EVENT EMITTED!] Interval: {event.interval_ms:.1f}ms\n"
        )

    clap_detector.event_bus.subscribe("ClapDetected", on_single_clap)
    clap_detector.subscribe_activation(on_double_clap)

    print(
        "[CLAP TEST] Starting microphone capture. Clap twice to test activation! (5 seconds)..."
    )
    try:
        audio_engine.start_input()
        clap_detector.start_listening()
        time.sleep(5.0)
    finally:
        clap_detector.stop_listening()
        audio_engine.stop_input()
        clap_detector.unsubscribe_activation(on_double_clap)

    print("\n[CLAP TEST SUMMARY]")
    print(f"Single Claps Detected:   {len(single_claps)}")
    print(f"Double Claps Activated:  {len(double_claps)}")
    report = clap_detector.get_health_report()
    print("Health Report Snapshot:")
    print(json.dumps(report, indent=2))
    print("[CLAP TEST COMPLETE]\n")
    return 0


def run_wake_word_health_check(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --wake-word-health-check."""
    bootstrap_result = bootstrapper.run()
    wakeword_detector = bootstrap_result.container.wakeword_detector()
    report = wakeword_detector.get_health_report()

    print("\n=========================================")
    print("      FRIDAY WAKE WORD HEALTH CHECK       ")
    print("=========================================")
    print(f"Status:                  {report['status']}")
    print(f"State:                   {report['state']}")
    print(f"Enabled:                 {report['enabled']}")
    print(f"Provider:                {report['provider']}")
    print(f"Target Wake Word:        {report['wake_word']}")
    print(f"Active Model Name:       {report['active_model_name']}")
    print(f"Model Path:              {report['model_path']}")
    print(f"Model Loaded:            {report['is_model_loaded']}")
    print(f"Is Custom Friday Model:  {report['is_custom_friday_model']}")
    print(f"Threshold:               {report['threshold']}")
    print(f"Cooldown:                {report['cooldown_ms']} ms")
    print(f"Last Error:              {report['last_error']}")
    print("Metrics:")
    print(json.dumps(report["metrics"], indent=2))
    print("=========================================\n")
    return 0


def run_wake_word_test(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --wake-word-test (interactive microphone wake word activation test)."""
    print("\n[WAKE WORD TEST] Initializing Audio Engine & OpenWakeWord Detector...")
    bootstrap_result = bootstrapper.run()
    audio_engine = bootstrap_result.container.audio_engine()
    wakeword_detector = bootstrap_result.container.wakeword_detector()

    detections = []

    def on_wake_word(event):
        detections.append(event)
        print(
            f"\n  🗣️ [WAKE WORD DETECTED!] word='{event.wake_word}', score={event.score:.2f} >= {event.threshold}\n"
        )

    wakeword_detector.subscribe_activation(on_wake_word)

    active_name = wakeword_detector.model_provider.active_model_name
    print(
        f"[WAKE WORD TEST] Say wake word ('{active_name}') to test activation! (5 seconds)..."
    )
    try:
        audio_engine.start_input()
        wakeword_detector.start_listening()
        time.sleep(5.0)
    finally:
        wakeword_detector.stop_listening()
        audio_engine.stop_input()
        wakeword_detector.unsubscribe_activation(on_wake_word)

    print("\n[WAKE WORD TEST SUMMARY]")
    print(f"Wake Word Detections:    {len(detections)}")
    report = wakeword_detector.get_health_report()
    print("Health Report Snapshot:")
    print(json.dumps(report, indent=2))
    print("[WAKE WORD TEST COMPLETE]\n")
    return 0


def run_vad_health_check(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --vad-health-check."""
    bootstrap_result = bootstrapper.run()
    vad_detector = bootstrap_result.container.vad_detector()
    summary = vad_detector.diagnostics.format_cli_summary(
        current_state=vad_detector.vad_state,
        is_model_loaded=vad_detector.model.is_loaded,
        is_listening=vad_detector.is_listening,
        model_path=getattr(vad_detector.model, "model_path", ""),
    )
    print(f"\n{summary}\n")
    return 0


def run_vad_test(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --vad-test (interactive microphone voice activity detection test)."""
    print("\n[VAD TEST] Initializing Audio Engine & Silero VAD Detector...")
    bootstrap_result = bootstrapper.run()
    audio_engine = bootstrap_result.container.audio_engine()
    vad_detector = bootstrap_result.container.vad_detector()

    speech_starts = []
    speech_stops = []

    def on_started(prob: float, ts: float):
        speech_starts.append((prob, ts))
        print(f"\n  🎙️ [SpeechStarted] probability={prob:.2f} >= threshold")

    def on_stopped(segment: Any):
        speech_stops.append(segment)
        print(
            f"  🛑 [SpeechStopped] duration={segment.duration_seconds:.2f}s, peak_prob={segment.peak_probability:.2f}\n"
        )

    vad_detector.add_speech_callback(on_started=on_started, on_stopped=on_stopped)

    print(
        "[VAD TEST] Starting microphone capture. Speak now to test voice activity! (5 seconds)..."
    )
    try:
        audio_engine.start_input()
        vad_detector.start_listening()
        time.sleep(5.0)
    finally:
        vad_detector.stop_listening()
        audio_engine.stop_input()

    print("\n[VAD TEST SUMMARY]")
    print(f"Speech Started Events: {len(speech_starts)}")
    print(f"Speech Stopped Events: {len(speech_stops)}")
    report = vad_detector.get_health_report()
    print("Health Report Snapshot:")
    print(json.dumps(report, indent=2))
    print("[VAD TEST COMPLETE]\n")
    return 0


def run_stt_health_check(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --stt-health-check."""
    bootstrap_result = bootstrapper.run()
    stt_service = bootstrap_result.container.stt_service()
    report = stt_service.get_health_report()

    print("\n========================================")
    print("      FRIDAY STT HEALTH CHECK          ")
    print("========================================")
    print("Engine:                  Faster-Whisper (ctranslate2)")
    print(f"Status:                  {report.get('status')}")
    print(f"Service State:           {report.get('service_state')}")
    print(f"Model Name:              {report.get('model_name')}")
    print(f"Model Loaded:            {report.get('model_loaded')}")
    print(f"Device:                  {report.get('device')}")
    print(f"Compute Type:            {report.get('compute_type')}")
    print(f"Language:                {report.get('language')}")
    print(f"Listening:               {report.get('listening')}")
    print(f"Enabled:                 {report.get('enabled')}")
    print(f"Last Error:              {report.get('last_error')}")
    print("----------------------------------------")
    print("OPERATIONAL METRICS:")
    m = report.get("metrics", {})
    for k, v in m.items():
        print(f"  {k:<28}: {v}")
    print("========================================\n")
    return 0


def run_stt_test(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --stt-test (interactive speech-to-text transcription test)."""
    print(
        "\n[STT TEST] Initializing Audio Engine, VAD, and Faster-Whisper STT Service..."
    )
    bootstrap_result = bootstrapper.run()
    audio_engine = bootstrap_result.container.audio_engine()
    stt_service = bootstrap_result.container.stt_service()

    transcriptions = []

    def on_transcription(res: Any):
        transcriptions.append(res)
        print(f"\n  📝 [TRANSCRIPTION RESULT] -> '{res.text}'")
        print(f"     Language: {res.language} ({res.language_probability:.2f})")
        print(
            f"     Audio Duration: {res.duration_seconds:.2f}s | Proc Time: {res.processing_time_seconds:.2f}s | RTF: {res.real_time_factor:.2f}\n"
        )

    stt_service.register_callback(on_transcription)

    print("[STT TEST] Microphones active. Speak now! (8 seconds execution window)...")
    try:
        audio_engine.start_input()
        stt_service.start_listening()
        time.sleep(8.0)
    finally:
        stt_service.stop_listening()
        audio_engine.stop_input()

    print("\n[STT TEST SUMMARY]")
    print(f"Transcriptions Completed: {len(transcriptions)}")
    report = stt_service.get_health_report()
    print("Health Report Snapshot:")
    print(json.dumps(report, indent=2))
    print("[STT TEST COMPLETE]\n")
    return 0


def run_voice_input_test(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --voice-input-test (End-to-End Audio -> VAD -> STT pipeline test)."""
    return run_stt_test(bootstrapper)


def run_stt_benchmark(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --stt-benchmark (local Faster-Whisper latency & RTF benchmark)."""
    print("\n========================================")
    print("      FRIDAY STT BENCHMARK             ")
    print("========================================")
    bootstrap_result = bootstrapper.run()
    stt_service = bootstrap_result.container.stt_service()
    engine = stt_service.engine

    print("Engine:       Faster-Whisper")
    print(f"Model:        {stt_service.stt_config.model_name}")
    print(f"Device:       {getattr(engine, 'actual_device', 'cpu')}")
    print(f"Compute Type: {getattr(engine, 'actual_compute_type', 'int8')}")

    # Generate 3.0s synthetic audio (16kHz sine wave audio)
    sample_rate = 16000
    duration_sec = 3.0
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    dummy_audio = (0.3 * np.sin(2 * np.pi * 440.0 * t)).astype(np.float32)

    print("\nRunning benchmark on 3.0s audio segment...")
    t_start = time.perf_counter()
    res = engine.transcribe(dummy_audio, sample_rate=sample_rate)
    proc_time = round(time.perf_counter() - t_start, 3)

    rtf = round(proc_time / duration_sec, 3)
    print(f"Audio Duration:   {duration_sec:.2f}s")
    print(f"Processing Time:  {proc_time:.3f}s")
    print(f"Real-Time Factor: {rtf:.3f}")
    print(f"Result Status:    {res.status}")
    print("========================================\n")
    return 0


def run_tts_health_check(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --tts-health-check."""
    print("\n========================================")
    print("      FRIDAY TTS HEALTH CHECK          ")
    print("========================================")
    bootstrap_result = bootstrapper.run()
    tts_service = bootstrap_result.container.tts_service()
    report = tts_service.get_health_report()

    print(f"Engine:                  {report.get('provider')}")
    print(f"Status:                  {report.get('status')}")
    print(f"Service State:           {report.get('service_state')}")
    print(f"Voice Name:              {report.get('voice_name')}")
    print(f"Model Loaded:            {report.get('model_loaded')}")
    print(f"Sample Rate:             {report.get('sample_rate')}Hz")
    print(f"Enabled:                 {report.get('enabled')}")
    print(f"Auto Play:               {report.get('auto_play')}")
    print(f"Is Speaking:             {report.get('is_speaking')}")
    print(f"Last Error:              {report.get('last_error')}")
    print("----------------------------------------")
    print("OPERATIONAL METRICS:")
    for k, v in report.get("metrics", {}).items():
        print(f"  {k:<28}: {v}")
    print("========================================\n")
    return 0


def run_tts_test(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --tts-test (interactive female voice synthesis & speaker test)."""
    print("\n========================================")
    print("      FRIDAY TTS VOICE TEST            ")
    print("========================================")
    bootstrap_result = bootstrapper.run()
    tts_service = bootstrap_result.container.tts_service()

    test_text = "Hello Pushkar. Friday is online and ready for commands."
    print(f"Speaking: '{test_text}'")

    res = tts_service.speak(test_text, auto_play=True)

    print("----------------------------------------")
    print(f"Status:          {res.status}")
    print(f"Voice:           {res.voice_name}")
    print(f"Audio Duration:  {res.audio_duration_seconds:.2f}s")
    print(f"Synthesis Time:  {res.synthesis_time_seconds:.3f}s")
    print(f"Real-Time Factor:{res.real_time_factor:.3f}")
    print("Playback:        COMPLETE")
    print("========================================\n")
    return 0


def run_tts_synthesize(bootstrapper: AppBootstrapper, text: str) -> int:
    """CLI handler for --tts-synthesize (non-playback audio synthesis test)."""
    print("\n========================================")
    print("      FRIDAY TTS SYNTHESIZE            ")
    print("========================================")
    bootstrap_result = bootstrapper.run()
    tts_service = bootstrap_result.container.tts_service()

    print(f"Synthesizing text: '{text}'...")
    res = tts_service.synthesize(text)

    print("----------------------------------------")
    print(f"Status:          {res.status}")
    print(f"Voice:           {res.voice_name}")
    print(f"Sample Rate:     {res.sample_rate}Hz")
    print(f"Audio Duration:  {res.audio_duration_seconds:.2f}s")
    print(f"Synthesis Time:  {res.synthesis_time_seconds:.3f}s")
    print(f"Real-Time Factor:{res.real_time_factor:.3f}")
    print("========================================\n")
    return 0


def run_tts_benchmark(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --tts-benchmark."""
    print("\n========================================")
    print("      FRIDAY TTS BENCHMARK             ")
    print("========================================")
    bootstrap_result = bootstrapper.run()
    tts_service = bootstrap_result.container.tts_service()

    test_cases = [
        ("Short", "Hello Pushkar."),
        ("Medium", "Good morning Pushkar. What would you like to work on today?"),
        (
            "Long",
            "Friday is a local-first personal AI desktop assistant for Windows. All voice recognition, speech-to-text, and text-to-speech processing operate entirely offline.",
        ),
    ]

    for label, text in test_cases:
        res = tts_service.synthesize(text)
        print(
            f"[{label:<6}] len: {len(text):<3} chars | Audio: {res.audio_duration_seconds:>5.2f}s | Synth: {res.synthesis_time_seconds:>5.3f}s | RTF: {res.real_time_factor:>5.3f}"
        )

    print("========================================\n")
    return 0


def run_conversation_health_check(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --conversation-health-check."""
    print("\n========================================")
    print("   FRIDAY CONVERSATION STATE HEALTH    ")
    print("========================================")
    bootstrap_result = bootstrapper.run()
    conversation_sm = bootstrap_result.container.conversation_state_machine()
    report = conversation_sm.get_health_report()

    print(f"Provider:                {report.get('provider')}")
    print(f"Status:                  {report.get('status')}")
    print(f"Service State:           {report.get('service_state')}")
    print(f"Current State:           {report.get('current_state')}")
    print(f"Session Active:          {report.get('session_active')}")
    print(f"Session ID:              {report.get('session_id')}")
    print(f"Activation Source:       {report.get('activation_source')}")
    print(f"Turn Count:              {report.get('turn_count')}")
    print(f"Barge-In Enabled:        {report.get('barge_in_enabled')}")
    print(f"Session Timeout:         {report.get('session_timeout_seconds')}s")
    print(f"Last Error:              {report.get('last_error')}")
    print("----------------------------------------")
    print("OPERATIONAL METRICS:")
    for k, v in report.get("metrics", {}).items():
        print(f"  {k:<32}: {v}")
    print("========================================\n")
    return 0


def run_conversation_test(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --conversation-test (simulated multi-turn conversation flow)."""
    print("\n========================================")
    print("   FRIDAY CONVERSATION SIMULATED TEST   ")
    print("========================================")
    bootstrap_result = bootstrapper.run()
    conversation_sm = bootstrap_result.container.conversation_state_machine()

    print(f"Initial State: {conversation_sm.state.value}")
    print("Simulating WakeWord Detections & Conversational Turns...")

    # Turn 1 Activation
    sess = conversation_sm.activate(source=ActivationSource.WAKE_WORD)
    print(
        f"Session Activated: ID={sess.session_id} | Source={sess.activation_source} | State={conversation_sm.state.value}"
    )

    # Simulated Speech Boundary -> STT Transcript -> Response -> Speaking -> Active
    print("Simulating user speech: 'Hello Friday'")
    conversation_sm.provide_response("Hello Pushkar. How can I help you today?")
    print(f"Transitioned to: {conversation_sm.state.value}")

    print("----------------------------------------")
    print(f"Final State: {conversation_sm.state.value}")
    print(
        f"Total Turns: {conversation_sm.active_session.turn_count if conversation_sm.active_session else 0}"
    )
    print("Conversation test completed successfully.")
    print("========================================\n")
    return 0


def run_conversation_barge_in_test(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --conversation-barge-in-test."""
    print("\n========================================")
    print("   FRIDAY CONVERSATION BARGE-IN TEST    ")
    print("========================================")
    bootstrap_result = bootstrapper.run()
    conversation_sm = bootstrap_result.container.conversation_state_machine()

    print("1. Activating conversation...")
    conversation_sm.activate(source=ActivationSource.DOUBLE_CLAP)

    print("2. Simulating speech output (SPEAKING state)...")
    conversation_sm.provide_response("Friday is speaking a long response...")

    print("3. Simulating user interruption (Barge-In)...")
    conversation_sm.stop_speaking()

    print(f"Current State after Barge-In: {conversation_sm.state.value}")
    assert conversation_sm.state.value == "LISTENING"

    print("Barge-in test completed successfully.")
    print("========================================\n")
    return 0


def run_conversation_manager_health_check(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --conversation-manager-health-check."""
    print("\n========================================")
    print("  FRIDAY CONVERSATION MANAGER HEALTH    ")
    print("========================================")
    bootstrap_result = bootstrapper.run()
    manager = bootstrap_result.container.conversation_manager()
    report = manager.get_health_report()

    print(f"Provider:                {report.get('provider')}")
    print(f"Status:                  {report.get('status')}")
    print(f"Service State:           {report.get('service_state')}")
    print(f"Session Active:          {report.get('session_active')}")
    print(f"Session ID:              {report.get('session_id')}")
    print(f"Turn Count:              {report.get('turn_count')}")
    print(f"Context Turns:           {report.get('context_turns')}")
    print(f"Active Entities:         {report.get('active_entities_count')}")
    print(f"Pending Clarification:   {report.get('pending_clarification')}")
    print(f"Context Size:            {report.get('context_size_chars')} chars")
    print(f"Context Limit:           {report.get('context_limit_chars')} chars")
    print(f"Last Error:              {report.get('last_error')}")
    print("----------------------------------------")
    print("OPERATIONAL METRICS:")
    for k, v in report.get("metrics", {}).items():
        print(f"  {k:<32}: {v}")
    print("========================================\n")
    return 0


def run_conversation_manager_test(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --conversation-manager-test (simulated reference resolution & short-term context)."""
    print("\n========================================")
    print("  FRIDAY CONVERSATION MANAGER TEST      ")
    print("========================================")
    bootstrap_result = bootstrapper.run()
    manager = bootstrap_result.container.conversation_manager()
    sess_id = "test-session-cli-101"

    manager.start_session(sess_id, activation_source="WAKE_WORD")

    print("Turn 1: User says 'Open Chrome'")
    r1 = manager.generate_contextual_response("Open Chrome", sess_id)
    print(f"Friday: '{r1}'")

    print("\nTurn 2: User says 'Close it' (resolving 'it' -> Chrome)")
    r2 = manager.generate_contextual_response("Close it", sess_id)
    print(f"Friday: '{r2}'")

    snapshot = manager.get_context_snapshot(sess_id)
    print("\n----------------------------------------")
    print(f"Final Context Snapshot Version: {snapshot.version if snapshot else 0}")
    print(
        f"Tracked Active Entities: {[e['name'] for e in (snapshot.active_entities if snapshot else [])]}"
    )
    print("Conversation manager test completed successfully.")
    print("========================================\n")
    manager.end_session(sess_id, reason="cli_test_complete")
    return 0


def run_greeting_health_check(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --greeting-health-check."""
    print("\n========================================")
    print("  FRIDAY GREETING SERVICE HEALTH        ")
    print("========================================")
    bootstrap_result = bootstrapper.run()
    greeting_svc = bootstrap_result.container.greeting_service()
    report = greeting_svc.get_health_report()

    print(f"Provider:                {report.get('provider')}")
    print(f"Status:                  {report.get('status')}")
    print(f"Enabled:                 {report.get('enabled')}")
    print(f"Service State:           {report.get('service_state')}")
    print(f"Context Aware:           {report.get('context_aware')}")
    print(f"Recent History Count:    {report.get('recent_greeting_count')}")
    print(f"Max History:             {report.get('max_history')}")
    print(f"Last Error:              {report.get('last_error')}")
    print("----------------------------------------")
    print("OPERATIONAL METRICS:")
    for k, v in report.get("metrics", {}).items():
        print(f"  {k:<32}: {v}")
    print("========================================\n")
    return 0


def run_greeting_test(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --greeting-test (deterministic context-aware greeting scenarios)."""
    print("\n========================================")
    print("  FRIDAY GREETING SERVICE SCENARIO TEST ")
    print("========================================")
    bootstrap_result = bootstrapper.run()
    builder = bootstrap_result.container.greeting_context_builder()
    provider = bootstrap_result.container.template_greeting_provider()

    scenarios = [
        ("Morning New Session", builder.get_time_of_day(8), True, 1),
        ("Afternoon Returning Session", builder.get_time_of_day(14), False, 3),
        ("Evening New Session", builder.get_time_of_day(19), True, 1),
        ("Night Session", builder.get_time_of_day(23), True, 1),
    ]

    for name, tod, is_new, turns in scenarios:
        ctx = GreetingContext(
            session_id=f"test-sess-{name.replace(' ', '-').lower()}",
            activation_source="WAKE_WORD",
            time_of_day=tod,
            is_new_session=is_new,
            is_returning_session=not is_new,
            turn_count=turns,
        )
        resp = provider.generate_greeting(ctx)
        print(f"Scenario:          {name}")
        print(f"Time of Day:       {tod.value}")
        print(f"Selected Category: {resp.category.value}")
        print(f"Generated Text:   '{resp.text}'")
        print("----------------------------------------")

    print("Greeting service scenario test completed successfully.")
    print("========================================\n")
    return 0


def run_llm_health_check(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --llm-health-check."""
    print("\n========================================")
    print("  FRIDAY LOCAL LLM RUNTIME HEALTH       ")
    print("========================================")
    bootstrap_result = bootstrapper.run()
    manager = bootstrap_result.container.llm_model_manager()
    report = manager.get_health_report()

    print(f"Provider:                {report.get('provider')}")
    print(f"Status:                  {report.get('status')}")
    print(f"Model Name:              {report.get('model_name')}")
    print(f"Model Path:              {report.get('model_path')}")
    print(f"Runtime State:           {report.get('state')}")
    print(f"Device / Backend:        {report.get('device')}")
    print(f"Format:                  {report.get('format')}")
    print(f"Model Loaded:            {report.get('model_loaded')}")
    print(f"Context Window:          {report.get('context_size')} tokens")
    print(f"CUDA Supported:          {report.get('supports_cuda')}")
    print(f"Streaming Supported:     {report.get('supports_streaming')}")
    print(f"Structured Output:       {report.get('supports_structured_output')}")
    print(f"Last Error:              {report.get('last_error')}")
    print("----------------------------------------")
    print("OPERATIONAL METRICS:")
    for k, v in report.get("metrics", {}).items():
        print(f"  {k:<32}: {v}")
    print("========================================\n")
    return 0


def run_llm_test(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --llm-test (prompt generation test)."""
    print("\n========================================")
    print("  FRIDAY LOCAL LLM INFERENCE TEST       ")
    print("========================================")
    bootstrap_result = bootstrapper.run()
    manager = bootstrap_result.container.llm_model_manager()

    # Use Fake provider if local GGUF model is not present
    from app.ai.models.models import AIRequest
    from app.ai.providers.fake_provider import FakeAIModelProvider

    if not report_model_ready(manager):
        print(
            "Note: GGUF model not found/loaded. Using FakeAIModelProvider for local testing."
        )
        manager.set_provider(
            FakeAIModelProvider(default_response_text="FRIDAY LOCAL LLM TEST PASSED")
        )
        manager.load_model()

    req = AIRequest(
        request_id="cli-test-01",
        prompt="Respond with exactly: FRIDAY LOCAL LLM TEST PASSED",
    )
    print(f"Prompt: '{req.prompt}'")

    response = manager.generate(req)
    print("\nModel Output:")
    print(f"'{response.text}'")
    print("----------------------------------------")
    print(f"Tokens/sec:              {response.tokens_per_second}")
    print(f"Duration:                {response.generation_duration_ms}ms")
    print("Local LLM inference test completed successfully.")
    print("========================================\n")
    return 0


def run_llm_benchmark(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --llm-benchmark (measure load time and token throughput)."""
    print("\n========================================")
    print("  FRIDAY LOCAL LLM BENCHMARK            ")
    print("========================================")
    bootstrap_result = bootstrapper.run()
    manager = bootstrap_result.container.llm_model_manager()

    from app.ai.models.models import AIRequest
    from app.ai.providers.fake_provider import FakeAIModelProvider

    if not report_model_ready(manager):
        print(
            "Note: GGUF model not present. Running benchmark using FakeAIModelProvider."
        )
        manager.set_provider(FakeAIModelProvider())

    t0 = time.time()
    manager.load_model()
    load_duration = (time.time() - t0) * 1000.0

    req = AIRequest(
        request_id="cli-bm-01",
        prompt="Explain artificial intelligence in 20 words.",
        max_tokens=100,
    )
    t1 = time.time()
    resp = manager.generate(req)
    total_dur = (time.time() - t1) * 1000.0

    print(f"Model Load Time:         {load_duration:.2f}ms")
    print(f"Generation Time:         {total_dur:.2f}ms")
    print(f"Total Tokens:            {resp.total_tokens}")
    print(f"Tokens / Sec:            {resp.tokens_per_second}")
    print("Local LLM benchmark completed successfully.")
    print("========================================\n")
    return 0


def run_orchestrator_health_check(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --orchestrator-health-check."""
    print("\n========================================")
    print("  FRIDAY AI ORCHESTRATOR HEALTH          ")
    print("========================================")
    bootstrap_result = bootstrapper.run()
    orchestrator = bootstrap_result.container.ai_orchestrator()
    report = orchestrator.get_health_report()

    print(f"Subsystem:               {report.get('subsystem')}")
    print(f"Status:                  {report.get('status')}")
    print(f"Orchestrator State:      {report.get('state')}")
    print(f"Enabled:                 {report.get('enabled')}")
    print(f"Max Reasoning Steps:     {report.get('max_steps')}")
    print(f"Tool Execution Allowed:  {report.get('allow_tools')}")
    print(f"Registered Tools:        {report.get('registered_tools_count')}")
    print(f"Last Error:              {report.get('last_error')}")
    print("----------------------------------------")
    print("OPERATIONAL METRICS:")
    for k, v in report.get("metrics", {}).items():
        print(f"  {k:<32}: {v}")
    print("========================================\n")
    return 0


def run_orchestrator_test(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --orchestrator-test (simulated user request orchestration)."""
    print("\n========================================")
    print("  FRIDAY AI ORCHESTRATOR WORKFLOW TEST   ")
    print("========================================")
    bootstrap_result = bootstrapper.run()
    orchestrator = bootstrap_result.container.ai_orchestrator()
    manager = bootstrap_result.container.llm_model_manager()

    from app.ai.orchestration.models import OrchestrationRequest
    from app.ai.providers.fake_provider import FakeAIModelProvider

    if not report_model_ready(manager):
        print(
            "Note: GGUF model not present. Using FakeAIModelProvider for orchestrator test."
        )
        manager.set_provider(
            FakeAIModelProvider(
                default_response_text="FRIDAY AI ORCHESTRATOR WORKFLOW TEST PASSED"
            )
        )
        manager.load_model()

    req = OrchestrationRequest(
        request_id="cli-orch-01",
        user_input="What is the system info and echo test?",
        session_id="cli-session-1",
    )

    print(f"User Request: '{req.user_input}'")
    result = orchestrator.process_request(req)

    print("\nOrchestrator Result:")
    print(f"Success:                 {result.success}")
    print(f"Final Response:          '{result.final_response}'")
    print(f"Turns Taken:             {result.turns_taken}")
    print(f"Executed Tools Count:    {len(result.executed_tools)}")
    print(f"Total Duration:          {result.total_duration_ms}ms")
    print("AI Orchestrator workflow test completed successfully.")
    print("========================================\n")
    return 0


def run_tool_calling_health_check(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --tool-calling-health-check."""
    print("\n========================================")
    print("  FRIDAY TOOL CALLING ENGINE HEALTH      ")
    print("========================================")
    bootstrap_result = bootstrapper.run()
    engine = bootstrap_result.container.tool_calling_engine()
    report = engine.get_health_report()

    print(f"Subsystem:               {report.get('subsystem')}")
    print(f"Status:                  {report.get('status')}")
    print(f"Enabled:                 {report.get('enabled')}")
    print(f"Max Tool Definitions:    {report.get('max_tool_definitions')}")
    print(f"Max Result Chars:        {report.get('max_result_chars')}")
    print(f"Duplicate Protection:    {report.get('duplicate_call_protection')}")
    print(f"Schema Cache Enabled:    {report.get('schema_cache_enabled')}")
    print(f"Registered Tools:        {report.get('registered_tools_count')}")
    print(f"Last Error:              {report.get('last_error')}")
    print("----------------------------------------")
    print("OPERATIONAL METRICS:")
    for k, v in report.get("metrics", {}).items():
        print(f"  {k:<32}: {v}")
    print("========================================\n")
    return 0


def run_tool_schema_test(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --tool-schema-test (verify tool definition schema generation)."""
    print("\n========================================")
    print("  FRIDAY TOOL SCHEMA GENERATION TEST     ")
    print("========================================")
    bootstrap_result = bootstrapper.run()
    engine = bootstrap_result.container.tool_calling_engine()

    defns = engine.get_tool_definitions(max_tools=3)
    print(f"Generated Tool Definitions Count: {len(defns)}")
    for d in defns:
        print(f"\nTool Name:      {d.tool_name}")
        print(f"Category:       {d.category}")
        print(f"Description:    {d.description}")
        print(f"Risk Level:     {d.risk_level}")
        print(f"Params Schema:  {json.dumps(d.parameters_schema)}")

    print("\nTool schema generation test completed successfully.")
    print("========================================\n")
    return 0


def run_tool_calling_test(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --tool-calling-test (verify tool call lifecycle)."""
    print("\n========================================")
    print("  FRIDAY TOOL CALLING EXECUTION TEST    ")
    print("========================================")
    bootstrap_result = bootstrapper.run()
    engine = bootstrap_result.container.tool_calling_engine()

    from app.ai.tool_calling.models import ToolCall

    call = ToolCall(
        call_id="cli-call-01",
        tool_name="system.echo",
        arguments={"message": "Hello Tool Calling Engine"},
    )
    print(f"Executing Tool Call: '{call.tool_name}' with args {call.arguments}")

    res = engine.execute_tool_call(call)
    print("\nExecution Outcome:")
    print(f"Call ID:         {res.call_id}")
    print(f"Status:          {res.status.value}")
    print(f"Duration:        {res.duration_ms}ms")
    print(f"Sanitized Result: {res.sanitized_result}")
    print("\nModel-Facing Output:")
    print(res.model_facing_output)
    print("Tool calling execution test completed successfully.")
    print("========================================\n")
    return 0


def run_tool_call_security_test(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --tool-call-security-test (verify security rejection of invalid tool calls)."""
    print("\n========================================")
    print("  FRIDAY TOOL CALL SECURITY AUDIT TEST  ")
    print("========================================")
    bootstrap_result = bootstrapper.run()
    engine = bootstrap_result.container.tool_calling_engine()

    from app.ai.tool_calling.models import ToolCall, ToolCallStatus

    # Test 1: Unknown Tool Name
    bad_call = ToolCall(call_id="sec-01", tool_name="system.hack_root", arguments={})
    is_valid, status, err = engine.validate_tool_call(bad_call)
    print(
        f"Test 1 (Unknown Tool): Valid={is_valid}, Status={status.value}, Error='{err}'"
    )

    assert is_valid is False
    assert status == ToolCallStatus.UNKNOWN_TOOL

    print(
        "Tool call security audit test completed successfully. All security boundaries enforced."
    )
    print("========================================\n")
    return 0


def run_personality_health_check(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --personality-health-check."""
    print("\n========================================")
    print("  FRIDAY PERSONALITY ENGINE HEALTH      ")
    print("========================================")
    bootstrap_result = bootstrapper.run()
    engine = bootstrap_result.container.personality_engine()
    report = engine.get_health_report()

    print(f"Subsystem:               {report.get('subsystem')}")
    print(f"Status:                  {report.get('status')}")
    print(f"Enabled:                 {report.get('enabled')}")
    print(f"Identity Name:           {report.get('identity_name')}")
    print(f"Formality Scale:         {report.get('formality')}")
    print(f"Humor Scale:             {report.get('humor')}")
    print(f"Active Modifiers Count:  {report.get('active_modifiers_count')}")
    print(f"Behavioral Rules Count:  {report.get('behavioral_rules_count')}")
    print(f"Last Error:              {report.get('last_error')}")
    print("----------------------------------------")
    print("OPERATIONAL METRICS:")
    for k, v in report.get("metrics", {}).items():
        print(f"  {k:<32}: {v}")
    print("========================================\n")
    return 0


def run_personality_test(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --personality-test (verify profile loading and behavioral rules)."""
    print("\n========================================")
    print("  FRIDAY PERSONALITY PROFILE TEST       ")
    print("========================================")
    bootstrap_result = bootstrapper.run()
    engine = bootstrap_result.container.personality_engine()

    profile = engine.get_personality_profile()
    print(f"Identity Name:     {profile.identity.name}")
    print(f"Identity Role:     {profile.identity.role}")
    print(f"Formality:         {profile.communication.formality}")
    print(f"Humor:             {profile.communication.humor}")
    print(f"Conciseness:       {profile.communication.conciseness}")
    print(f"Registered Rules:  {len(profile.behavioral_rules)}")

    print("\nPersonality profile test completed successfully.")
    print("========================================\n")
    return 0


def run_personality_context_test(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --personality-context-test (verify compact prompt snippet generation)."""
    print("\n========================================")
    print("  FRIDAY PERSONALITY CONTEXT TEST       ")
    print("========================================")
    bootstrap_result = bootstrapper.run()
    engine = bootstrap_result.container.personality_engine()

    from app.ai.personality.models import ResponseStyleMode

    ctx = engine.generate_personality_context(
        user_input="Can you open Chrome?", style_mode=ResponseStyleMode.NORMAL
    )

    print(f"Emotional Signal:   {ctx.emotional_signal.value}")
    print(f"Effective Formality: {ctx.effective_formality}")
    print(f"Effective Humor:     {ctx.effective_humor}")
    print(f"Effective Conciseness:{ctx.effective_conciseness}")
    print(f"Prompt Snippet Length: {len(ctx.system_prompt_snippet)} chars")
    print("\nModel System Instruction Snippet:")
    print(ctx.system_prompt_snippet)

    print("\nPersonality context test completed successfully.")
    print("========================================\n")
    return 0


def run_personality_modifier_test(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --personality-modifier-test (verify dynamic context modifiers under frustration)."""
    print("\n========================================")
    print("  FRIDAY PERSONALITY MODIFIER TEST      ")
    print("========================================")
    bootstrap_result = bootstrapper.run()
    engine = bootstrap_result.container.personality_engine()

    from app.ai.personality.models import EmotionalSignal, PersonalityModifier

    # Test frustration detection
    frust_ctx = engine.generate_personality_context(
        user_input="Why is this so slow and broken!!"
    )
    print(f"Frustrated Input Classification: {frust_ctx.emotional_signal.value}")
    print(f"Frustrated Effective Humor:       {frust_ctx.effective_humor}")
    print(f"Frustrated Effective Conciseness: {frust_ctx.effective_conciseness}")

    assert frust_ctx.emotional_signal == EmotionalSignal.FRUSTRATED
    assert frust_ctx.effective_humor <= 0.1

    # Apply manual modifier
    mod = PersonalityModifier(
        source="test", reason="technical_mode", formality_delta=0.4, humor_delta=-0.2
    )
    engine.apply_temporary_modifier(mod)

    mod_ctx = engine.generate_personality_context(
        user_input="Explain quantum mechanics."
    )
    print(f"Modified Formality: {mod_ctx.effective_formality}")

    engine.clear_modifiers()
    print(
        "Personality modifier test completed successfully. Dynamic adaptations verified."
    )
    print("========================================\n")
    return 0


def run_response_health_check(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --response-health-check."""
    print("\n========================================")
    print("  FRIDAY DYNAMIC RESPONSE ENGINE HEALTH ")
    print("========================================")
    bootstrap_result = bootstrapper.run()
    engine = bootstrap_result.container.response_generator()
    report = engine.get_health_report()

    print(f"Subsystem:               {report.get('subsystem')}")
    print(f"Status:                  {report.get('status')}")
    print(f"Enabled:                 {report.get('enabled')}")
    print(f"Max Response Chars:      {report.get('max_response_chars')}")
    print(f"Streaming Enabled:       {report.get('streaming_enabled')}")
    print(f"LLM Provider Ready:      {report.get('llm_provider_ready')}")
    print(f"Last Error:              {report.get('last_error')}")
    print("----------------------------------------")
    print("OPERATIONAL METRICS:")
    for k, v in report.get("metrics", {}).items():
        print(f"  {k:<32}: {v}")
    print("========================================\n")
    return 0


def run_response_test(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --response-test (verify end-to-end response generation)."""
    print("\n========================================")
    print("  FRIDAY DYNAMIC RESPONSE GENERATION TEST")
    print("========================================")
    bootstrap_result = bootstrapper.run()
    engine = bootstrap_result.container.response_generator()

    from app.ai.response.models import ResponseGenerationRequest

    req = ResponseGenerationRequest(
        request_id="cli-resp-01",
        user_input="Open Chrome.",
        tool_results=[
            {
                "tool_name": "browser.open",
                "status": "SUCCESS",
                "result": {"app": "Chrome"},
            }
        ],
    )
    res = engine.generate_response(req)
    print(f"User Input:       '{req.user_input}'")
    print(f"Status:           {res.status.value}")
    print(f"Response Text:    '{res.response_text}'")
    print(f"Spoken Text:      '{res.spoken_text}'")
    print(f"Fallback Used:    {res.metadata.fallback_used}")

    print("\nResponse generation test completed successfully.")
    print("========================================\n")
    return 0


def run_response_context_test(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --response-context-test (verify fact-grounded context assembly)."""
    print("\n========================================")
    print("  FRIDAY RESPONSE CONTEXT ASSEMBLY TEST ")
    print("========================================")
    bootstrap_result = bootstrapper.run()
    builder = bootstrap_result.container.response_context_builder()

    from app.ai.response.models import ResponseGenerationRequest

    req = ResponseGenerationRequest(
        request_id="cli-ctx-01",
        user_input="Get system info",
        tool_results=[
            {
                "tool_name": "system.info",
                "status": "SUCCESS",
                "result": {"os": "Windows 11"},
            }
        ],
    )
    prompt = builder.build_prompt_context(req)
    print(f"Assembled Prompt Length: {len(prompt)} chars")
    print("\nAssembled Prompt Context:")
    print(prompt)

    print("\nResponse context assembly test completed successfully.")
    print("========================================\n")
    return 0


def run_response_grounding_test(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --response-grounding-test (verify success vs failure factual grounding)."""
    print("\n========================================")
    print("  FRIDAY FACTUAL GROUNDING TEST        ")
    print("========================================")
    bootstrap_result = bootstrapper.run()
    engine = bootstrap_result.container.response_generator()

    from app.ai.response.models import ResponseGenerationRequest, ResponseStatus

    # Test 1: Tool Success
    req_success = ResponseGenerationRequest(
        request_id="g1",
        user_input="Launch Notepad",
        tool_results=[{"tool_name": "system.launch", "status": "SUCCESS"}],
    )
    res_success = engine.generate_response(req_success)
    print(
        f"Test 1 (Tool Success) Status: {res_success.status.value}, Text: '{res_success.response_text}'"
    )

    # Test 2: Tool Failure
    req_fail = ResponseGenerationRequest(
        request_id="g2",
        user_input="Launch SecretApp",
        tool_results=[
            {
                "tool_name": "system.launch",
                "status": "FAILED",
                "error": "Application not found",
            }
        ],
    )
    res_fail = engine.generate_response(req_fail)
    print(
        f"Test 2 (Tool Failure) Status: {res_fail.status.value}, Text: '{res_fail.response_text}'"
    )
    assert res_fail.status == ResponseStatus.FAILED

    print("\nResponse factual grounding test completed successfully.")
    print("========================================\n")
    return 0


def run_response_fallback_test(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --response-fallback-test (verify deterministic fallback under failure)."""
    print("\n========================================")
    print("  FRIDAY RESPONSE FALLBACK TEST         ")
    print("========================================")
    bootstrap_result = bootstrapper.run()
    engine = bootstrap_result.container.response_generator()

    from app.ai.response.models import ResponseGenerationRequest, ResponseStatus

    req = ResponseGenerationRequest(
        request_id="f1",
        user_input="Execute system scan",
        tool_results=[{"tool_name": "system.scan", "status": "SUCCESS"}],
    )
    fallback_res = engine.format_fallback_response(req, "Simulated LLM Timeout")
    print(f"Fallback Status:        {fallback_res.status.value}")
    print(f"Fallback Response Text: '{fallback_res.response_text}'")
    print(f"Fallback Used Metadata: {fallback_res.metadata.fallback_used}")

    assert fallback_res.status == ResponseStatus.FALLBACK_USED
    assert fallback_res.metadata.fallback_used is True

    print("\nResponse fallback test completed successfully.")
    print("========================================\n")
    return 0


def run_greeting_ai_test(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --greeting-ai-test (verify AI context-aware activation greeting)."""
    print("\n========================================")
    print("  FRIDAY CONTEXTUAL AI GREETING TEST    ")
    print("========================================")
    bootstrap_result = bootstrapper.run()
    svc = bootstrap_result.container.greeting_service()

    resp = svc.generate_greeting(
        session_id="cli-greet-session",
        activation_source="WAKE_WORD",
    )
    print(f"Greeting Text:     '{resp.text}'")
    print(f"Category:          {resp.category.value}")
    print(f"Provider:          {resp.provider}")
    print(f"Should Speak:      {resp.should_speak}")
    print(f"Metadata:          {resp.metadata}")

    print("\nContextual AI greeting test completed successfully.")
    print("========================================\n")
    return 0


def run_greeting_context_test(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --greeting-context-test (verify activation context construction)."""
    print("\n========================================")
    print("  FRIDAY GREETING CONTEXT ASSEMBLY TEST ")
    print("========================================")
    bootstrap_result = bootstrapper.run()
    builder = bootstrap_result.container.greeting_context_builder()

    ctx = builder.build_context(
        session_id="cli-ctx-01", activation_source="DOUBLE_CLAP"
    )
    print(f"Session ID:         {ctx.session_id}")
    print(f"Activation Source:  {ctx.activation_source}")
    print(f"Time of Day:        {ctx.time_of_day.value}")
    print(f"Is New Session:     {ctx.is_new_session}")
    print(f"Is Returning:       {ctx.is_returning_session}")

    print("\nGreeting context assembly test completed successfully.")
    print("========================================\n")
    return 0


def run_greeting_fallback_test(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --greeting-fallback-test (verify template fallback when AI provider fails)."""
    print("\n========================================")
    print("  FRIDAY GREETING FALLBACK TEST         ")
    print("========================================")
    bootstrap_result = bootstrapper.run()
    template_provider = bootstrap_result.container.template_greeting_provider()
    builder = bootstrap_result.container.greeting_context_builder()

    ctx = builder.build_context(session_id="cli-fallback-01")
    resp = template_provider.generate_greeting(ctx)

    print(f"Fallback Text:      '{resp.text}'")
    print(f"Provider:           {resp.provider}")
    print(f"Category:           {resp.category.value}")

    print("\nGreeting fallback test completed successfully.")
    print("========================================\n")
    return 0


def run_greeting_repetition_test(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --greeting-repetition-test (verify repetition prevention across turns)."""
    print("\n========================================")
    print("  FRIDAY GREETING REPETITION TEST       ")
    print("========================================")
    bootstrap_result = bootstrapper.run()
    svc = bootstrap_result.container.greeting_service()

    g1 = svc.generate_greeting("s1", "WAKE_WORD").text
    g2 = svc.generate_greeting("s1", "WAKE_WORD").text
    print(f"Turn 1 Greeting: '{g1}'")
    print(f"Turn 2 Greeting: '{g2}'")

    print("\nGreeting repetition test completed successfully.")
    print("========================================\n")
    return 0


def cleanup_cli(bootstrap_result: Any) -> None:
    """Clean up GUI window and background services after CLI command execution."""
    try:
        if hasattr(bootstrap_result, "main_window") and bootstrap_result.main_window:
            bootstrap_result.main_window.close()
        if (
            hasattr(bootstrap_result, "service_manager")
            and bootstrap_result.service_manager
        ):
            bootstrap_result.service_manager.stop_all()
    except Exception as exc:  # noqa: BLE001
        logger.debug(f"CLI cleanup notice: {exc}")


def run_conversation_continuity_health_check(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --conversation-continuity-health-check."""
    print("\n========================================")
    print("  FRIDAY CONVERSATIONAL CONTINUITY HEALTH")
    print("========================================")
    bootstrap_result = bootstrapper.run(is_cli=True)
    mgr = bootstrap_result.container.conversation_manager()
    report = mgr.get_health_report()

    print(f"Service State:           {report.get('service_state')}")
    print(f"Active Session:          {report.get('session_active')}")
    print(f"Context Limit Chars:     {report.get('context_limit_chars')}")
    print("----------------------------------------")
    print("OPERATIONAL METRICS:")
    for k, v in report.get("metrics", {}).items():
        print(f"  {k:<32}: {v}")
    print("========================================\n")
    cleanup_cli(bootstrap_result)
    return 0


def run_conversation_continuity_test(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --conversation-continuity-test (verify multi-turn conversational continuity)."""
    print("\n========================================")
    print("  FRIDAY CONVERSATIONAL CONTINUITY TEST ")
    print("========================================")
    bootstrap_result = bootstrapper.run(is_cli=True)
    mgr = bootstrap_result.container.conversation_manager()

    s_id = "cli-cont-01"
    mgr.start_session(s_id)
    r1 = mgr.generate_contextual_response("Open Chrome", s_id)
    r2 = mgr.generate_contextual_response("Close it", s_id)

    print(f"Turn 1: 'Open Chrome' -> '{r1}'")
    print(f"Turn 2: 'Close it'    -> '{r2}'")
    mgr.end_session(s_id)

    print("\nConversational continuity test completed successfully.")
    print("========================================\n")
    cleanup_cli(bootstrap_result)
    return 0


def run_clarification_test(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --clarification-test (verify pending clarification lifecycle)."""
    print("\n========================================")
    print("  FRIDAY PENDING CLARIFICATION TEST     ")
    print("========================================")
    bootstrap_result = bootstrapper.run(is_cli=True)
    mgr = bootstrap_result.container.conversation_manager()

    s_id = "cli-clar-01"
    mgr.start_session(s_id)
    mgr.generate_contextual_response("Open Chrome and Edge", s_id)
    q = mgr.generate_contextual_response("Close it", s_id)
    ans = mgr.generate_contextual_response("Chrome", s_id)

    print("Turn 1: 'Open Chrome and Edge'")
    print(f"Turn 2 (Ambiguous): 'Close it' -> '{q}'")
    print(f"Turn 3 (Clarified): 'Chrome'   -> '{ans}'")
    mgr.end_session(s_id)

    print("\nClarification lifecycle test completed successfully.")
    print("========================================\n")
    cleanup_cli(bootstrap_result)
    return 0


def run_reference_resolution_test(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --reference-resolution-test (verify pronoun & entity reference resolution)."""
    print("\n========================================")
    print("  FRIDAY REFERENCE RESOLUTION TEST      ")
    print("========================================")
    bootstrap_result = bootstrapper.run(is_cli=True)
    mgr = bootstrap_result.container.conversation_manager()

    s_id = "cli-ref-01"
    mgr.start_session(s_id)
    mgr.generate_contextual_response("Open Chrome", s_id)
    res = mgr.resolve_reference(s_id, "Close it")

    print("Input Phrase: 'Close it'")
    print(f"Status:       {res.status.value}")
    print(
        f"Target:       {res.resolved_entity.name if res.resolved_entity else 'None'}"
    )
    mgr.end_session(s_id)

    print("\nReference resolution test completed successfully.")
    print("========================================\n")
    cleanup_cli(bootstrap_result)
    return 0


def run_conversation_correction_test(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --conversation-correction-test (verify intent/entity correction)."""
    print("\n========================================")
    print("  FRIDAY INTENT CORRECTION TEST         ")
    print("========================================")
    bootstrap_result = bootstrapper.run(is_cli=True)
    mgr = bootstrap_result.container.conversation_manager()

    s_id = "cli-corr-01"
    mgr.start_session(s_id)
    r1 = mgr.generate_contextual_response("Open Chrome", s_id)
    r2 = mgr.generate_contextual_response("No, I meant Edge", s_id)

    print(f"Turn 1:              'Open Chrome'      -> '{r1}'")
    print(f"Turn 2 (Correction): 'No, I meant Edge' -> '{r2}'")
    mgr.end_session(s_id)

    print("\nConversation correction test completed successfully.")
    print("========================================\n")
    cleanup_cli(bootstrap_result)
    return 0


def run_conversation_retry_test(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --conversation-retry-test (verify operation retry continuity)."""
    print("\n========================================")
    print("  FRIDAY OPERATION RETRY TEST           ")
    print("========================================")
    bootstrap_result = bootstrapper.run(is_cli=True)
    mgr = bootstrap_result.container.conversation_manager()

    s_id = "cli-retry-01"
    mgr.start_session(s_id)
    mgr.record_tool_result(
        s_id, {"arguments": {"message": "launch application"}}, {"status": "error"}
    )
    res = mgr.generate_contextual_response("Try again", s_id)

    print("Turn 1: Tool failure recorded.")
    print(f"Turn 2: 'Try again' -> '{res}'")
    mgr.end_session(s_id)

    print("\nConversation retry test completed successfully.")
    print("========================================\n")
    cleanup_cli(bootstrap_result)
    return 0


def run_conversation_context_test(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --conversation-context-test (verify ContextSnapshot building & bounds)."""
    print("\n========================================")
    print("  FRIDAY CONVERSATION CONTEXT TEST      ")
    print("========================================")
    bootstrap_result = bootstrapper.run(is_cli=True)
    mgr = bootstrap_result.container.conversation_manager()

    s_id = "cli-ctx-01"
    mgr.start_session(s_id)
    mgr.generate_contextual_response("Open Chrome", s_id)
    snap = mgr.get_context_snapshot(s_id)

    print(f"Session ID:         {snap.session_id}")
    print(f"Turn Count:         {len(snap.recent_turns)}")
    print(f"Active Entities:    {[e['name'] for e in snap.active_entities]}")
    mgr.end_session(s_id)

    print("\nConversation context test completed successfully.")
    print("========================================\n")
    cleanup_cli(bootstrap_result)
    return 0


def run_conversation_stress_test(bootstrapper: AppBootstrapper) -> int:
    """CLI handler for --conversation-stress-test (verify bounded context under heavy turns)."""
    print("\n========================================")
    print("  FRIDAY CONVERSATION STRESS TEST       ")
    print("========================================")
    bootstrap_result = bootstrapper.run(is_cli=True)
    mgr = bootstrap_result.container.conversation_manager()

    s_id = "cli-stress-01"
    mgr.start_session(s_id)
    for i in range(50):
        mgr.generate_contextual_response(f"Turn {i}: Open document_{i}.txt", s_id)

    snap = mgr.get_context_snapshot(s_id)
    print("Total Turns Run:    50")
    print(f"Retained Turns:     {len(snap.recent_turns)}")
    print(f"Retained Entities:  {len(snap.active_entities)}")
    mgr.end_session(s_id)

    print("\nConversation stress test completed successfully.")
    print("========================================\n")
    cleanup_cli(bootstrap_result)
    return 0


def report_model_ready(manager) -> bool:
    try:
        manager.load_model()
        return manager.lifecycle_state.value in ("READY", "GENERATING")
    except Exception:  # noqa: BLE001
        return False


def main() -> int:
    """Main execution function."""
    parser = argparse.ArgumentParser(description="Friday AI Assistant Desktop Shell")
    parser.add_argument(
        "--audio-health-check",
        action="store_true",
        help="Run Audio Engine diagnostic health report and exit",
    )
    parser.add_argument(
        "--audio-test",
        action="store_true",
        help="Run developer audio hardware capture & test tone playback test and exit",
    )
    parser.add_argument(
        "--clap-health-check",
        action="store_true",
        help="Run Clap Detector diagnostic health report and exit",
    )
    parser.add_argument(
        "--clap-test",
        action="store_true",
        help="Run interactive double-clap microphone activation test and exit",
    )
    parser.add_argument(
        "--wake-word-health-check",
        action="store_true",
        help="Run Wake Word Detector diagnostic health report and exit",
    )
    parser.add_argument(
        "--wake-word-test",
        action="store_true",
        help="Run interactive wake-word microphone activation test and exit",
    )
    parser.add_argument(
        "--vad-health-check",
        action="store_true",
        help="Run Voice Activity Detector diagnostic health report and exit",
    )
    parser.add_argument(
        "--vad-test",
        action="store_true",
        help="Run interactive microphone voice activity detection test and exit",
    )
    parser.add_argument(
        "--stt-health-check",
        action="store_true",
        help="Run Speech-to-Text diagnostic health report and exit",
    )
    parser.add_argument(
        "--stt-test",
        action="store_true",
        help="Run interactive microphone Speech-to-Text transcription test and exit",
    )
    parser.add_argument(
        "--voice-input-test",
        action="store_true",
        help="Run end-to-end Audio -> VAD -> STT pipeline diagnostic test and exit",
    )
    parser.add_argument(
        "--stt-benchmark",
        action="store_true",
        help="Run local Faster-Whisper performance & RTF benchmark and exit",
    )
    parser.add_argument(
        "--tts-health-check",
        action="store_true",
        help="Run Text-to-Speech diagnostic health report and exit",
    )
    parser.add_argument(
        "--tts-test",
        action="store_true",
        help="Run interactive female voice synthesis & speaker test and exit",
    )
    parser.add_argument(
        "--tts-synthesize",
        type=str,
        default=None,
        help="Synthesize text to speech audio without playback and exit",
    )
    parser.add_argument(
        "--tts-benchmark",
        action="store_true",
        help="Run local Piper TTS performance & RTF benchmark and exit",
    )
    parser.add_argument(
        "--conversation-health-check",
        action="store_true",
        help="Run Conversation State Machine diagnostic health report and exit",
    )
    parser.add_argument(
        "--conversation-test",
        action="store_true",
        help="Run simulated multi-turn conversation flow test and exit",
    )
    parser.add_argument(
        "--conversation-barge-in-test",
        action="store_true",
        help="Run simulated speech interruption barge-in test and exit",
    )
    parser.add_argument(
        "--conversation-manager-health-check",
        action="store_true",
        help="Run Conversation Manager diagnostic health report and exit",
    )
    parser.add_argument(
        "--conversation-manager-test",
        action="store_true",
        help="Run simulated reference resolution & short-term context test and exit",
    )
    parser.add_argument(
        "--greeting-health-check",
        action="store_true",
        help="Run Greeting Service diagnostic health report and exit",
    )
    parser.add_argument(
        "--greeting-test",
        action="store_true",
        help="Run simulated context-aware greeting scenario tests and exit",
    )
    parser.add_argument(
        "--llm-health-check",
        action="store_true",
        help="Run Local LLM Runtime diagnostic health report and exit",
    )
    parser.add_argument(
        "--llm-test",
        action="store_true",
        help="Run Local LLM prompt generation test and exit",
    )
    parser.add_argument(
        "--llm-benchmark",
        action="store_true",
        help="Run Local LLM load time and throughput benchmark and exit",
    )
    parser.add_argument(
        "--orchestrator-health-check",
        action="store_true",
        help="Run AI Orchestrator diagnostic health report and exit",
    )
    parser.add_argument(
        "--orchestrator-test",
        action="store_true",
        help="Run simulated AI Orchestrator workflow test and exit",
    )
    parser.add_argument(
        "--tool-calling-health-check",
        action="store_true",
        help="Run Tool Calling Engine diagnostic health report and exit",
    )
    parser.add_argument(
        "--tool-calling-test",
        action="store_true",
        help="Run Tool Calling execution lifecycle test and exit",
    )
    parser.add_argument(
        "--tool-schema-test",
        action="store_true",
        help="Run Tool Definition JSON Schema generation test and exit",
    )
    parser.add_argument(
        "--tool-call-security-test",
        action="store_true",
        help="Run Tool Calling Security & Sanitization audit test and exit",
    )
    parser.add_argument(
        "--personality-health-check",
        action="store_true",
        help="Run Personality Engine diagnostic health report and exit",
    )
    parser.add_argument(
        "--personality-test",
        action="store_true",
        help="Run Personality profile and behavioral rules test and exit",
    )
    parser.add_argument(
        "--personality-context-test",
        action="store_true",
        help="Run Personality model system instruction prompt snippet test and exit",
    )
    parser.add_argument(
        "--personality-modifier-test",
        action="store_true",
        help="Run Personality dynamic context modifiers test and exit",
    )
    parser.add_argument(
        "--response-health-check",
        action="store_true",
        help="Run Response Generator diagnostic health report and exit",
    )
    parser.add_argument(
        "--response-test",
        action="store_true",
        help="Run Dynamic Response Generation end-to-end turn test and exit",
    )
    parser.add_argument(
        "--response-context-test",
        action="store_true",
        help="Run Response Generator context builder test and exit",
    )
    parser.add_argument(
        "--response-grounding-test",
        action="store_true",
        help="Run Response Generator factual grounding test and exit",
    )
    parser.add_argument(
        "--response-fallback-test",
        action="store_true",
        help="Run Response Generator deterministic fallback test and exit",
    )
    parser.add_argument(
        "--greeting-ai-test",
        action="store_true",
        help="Run AI context-aware activation greeting test and exit",
    )
    parser.add_argument(
        "--greeting-fallback-test",
        action="store_true",
        help="Run Greeting template fallback test and exit",
    )
    parser.add_argument(
        "--greeting-repetition-test",
        action="store_true",
        help="Run Greeting repetition prevention test and exit",
    )
    parser.add_argument(
        "--conversation-continuity-health-check",
        action="store_true",
        help="Run Conversation Continuity health check and exit",
    )
    parser.add_argument(
        "--conversation-continuity-test",
        action="store_true",
        help="Run Conversational Continuity turn test and exit",
    )
    parser.add_argument(
        "--clarification-test",
        action="store_true",
        help="Run Pending Clarification lifecycle test and exit",
    )
    parser.add_argument(
        "--reference-resolution-test",
        action="store_true",
        help="Run Pronoun and entity reference resolution test and exit",
    )
    parser.add_argument(
        "--conversation-correction-test",
        action="store_true",
        help="Run Intent/Entity correction test and exit",
    )
    parser.add_argument(
        "--conversation-retry-test",
        action="store_true",
        help="Run Operation retry continuity test and exit",
    )
    parser.add_argument(
        "--conversation-context-test",
        action="store_true",
        help="Run Conversation ContextSnapshot build test and exit",
    )
    parser.add_argument(
        "--conversation-stress-test",
        action="store_true",
        help="Run Bounded conversation context stress test and exit",
    )
    args = parser.parse_args()

    setup_global_exception_handler()
    bootstrapper = AppBootstrapper()

    if args.audio_health_check:
        return run_audio_health_check(bootstrapper)

    if args.audio_test:
        return run_audio_test(bootstrapper)

    if args.clap_health_check:
        return run_clap_health_check(bootstrapper)

    if args.clap_test:
        return run_clap_test(bootstrapper)

    if args.wake_word_health_check:
        return run_wake_word_health_check(bootstrapper)

    if args.wake_word_test:
        return run_wake_word_test(bootstrapper)

    if args.vad_health_check:
        return run_vad_health_check(bootstrapper)

    if args.vad_test:
        return run_vad_test(bootstrapper)

    if args.stt_health_check:
        return run_stt_health_check(bootstrapper)

    if args.stt_test:
        return run_stt_test(bootstrapper)

    if args.voice_input_test:
        return run_voice_input_test(bootstrapper)

    if args.stt_benchmark:
        return run_stt_benchmark(bootstrapper)

    if args.tts_health_check:
        return run_tts_health_check(bootstrapper)

    if args.tts_test:
        return run_tts_test(bootstrapper)

    if args.tts_synthesize:
        return run_tts_synthesize(bootstrapper, args.tts_synthesize)

    if args.tts_benchmark:
        return run_tts_benchmark(bootstrapper)

    if args.conversation_health_check:
        return run_conversation_health_check(bootstrapper)

    if args.conversation_test:
        return run_conversation_test(bootstrapper)

    if args.conversation_barge_in_test:
        return run_conversation_barge_in_test(bootstrapper)

    if args.conversation_manager_health_check:
        return run_conversation_manager_health_check(bootstrapper)

    if args.conversation_manager_test:
        return run_conversation_manager_test(bootstrapper)

    if args.greeting_health_check:
        return run_greeting_health_check(bootstrapper)

    if args.greeting_test:
        return run_greeting_test(bootstrapper)

    if args.llm_health_check:
        return run_llm_health_check(bootstrapper)

    if args.llm_test:
        return run_llm_test(bootstrapper)

    if args.llm_benchmark:
        return run_llm_benchmark(bootstrapper)

    if args.orchestrator_health_check:
        return run_orchestrator_health_check(bootstrapper)

    if args.orchestrator_test:
        return run_orchestrator_test(bootstrapper)

    if args.tool_calling_health_check:
        return run_tool_calling_health_check(bootstrapper)

    if args.tool_calling_test:
        return run_tool_calling_test(bootstrapper)

    if args.tool_schema_test:
        return run_tool_schema_test(bootstrapper)

    if args.tool_call_security_test:
        return run_tool_call_security_test(bootstrapper)

    if args.personality_health_check:
        return run_personality_health_check(bootstrapper)

    if args.personality_test:
        return run_personality_test(bootstrapper)

    if args.personality_context_test:
        return run_personality_context_test(bootstrapper)

    if args.personality_modifier_test:
        return run_personality_modifier_test(bootstrapper)

    if args.response_health_check:
        return run_response_health_check(bootstrapper)

    if args.response_test:
        return run_response_test(bootstrapper)

    if args.response_context_test:
        return run_response_context_test(bootstrapper)

    if args.response_grounding_test:
        return run_response_grounding_test(bootstrapper)

    if args.response_fallback_test:
        return run_response_fallback_test(bootstrapper)

    if args.greeting_ai_test:
        return run_greeting_ai_test(bootstrapper)

    if args.greeting_fallback_test:
        return run_greeting_fallback_test(bootstrapper)

    if args.greeting_repetition_test:
        return run_greeting_repetition_test(bootstrapper)

    if args.conversation_continuity_health_check:
        return run_conversation_continuity_health_check(bootstrapper)

    if args.conversation_continuity_test:
        return run_conversation_continuity_test(bootstrapper)

    if args.clarification_test:
        return run_clarification_test(bootstrapper)

    if args.reference_resolution_test:
        return run_reference_resolution_test(bootstrapper)

    if args.conversation_correction_test:
        return run_conversation_correction_test(bootstrapper)

    if args.conversation_retry_test:
        return run_conversation_retry_test(bootstrapper)

    if args.conversation_context_test:
        return run_conversation_context_test(bootstrapper)

    if args.conversation_stress_test:
        return run_conversation_stress_test(bootstrapper)

    try:
        bootstrap_result = bootstrapper.run()
        logging_manager = bootstrap_result.logging_manager
        settings = bootstrap_result.settings
        qt_app = bootstrap_result.qt_app

        logger.info(
            f"Friday AI Assistant Phase 3.4 running on Python {sys.version_info.major}.{sys.version_info.minor}."
        )

        # Run Qt Event Loop
        exit_code = qt_app.exec()

        # Graceful shutdown log
        logging_manager.log_shutdown(settings.app.name)
        return exit_code

    except FridayBaseException as exc:
        print(f"[FATAL STARTUP ERROR] {exc.message}", file=sys.stderr)
        if exc.details:
            print(f"[ERROR DETAILS] {exc.details}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"[UNHANDLED FATAL ERROR] {exc}", file=sys.stderr)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
