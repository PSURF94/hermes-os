import os
from groq import Groq

GROQ_API_KEY = os.getenv("GROQ_API_KEY")


def transcrever(audio_bytes: bytes, filename: str = "audio.ogg") -> str:
    client = Groq(api_key=GROQ_API_KEY)
    transcription = client.audio.transcriptions.create(
        file=(filename, audio_bytes),
        model="whisper-large-v3",
        language="pt",
    )
    return transcription.text.strip()
