"""
Asynchronous Google Cloud Text-to-Speech Implementation
=====================================================

This module provides a comprehensive async interface for Google Cloud Text-to-Speech,
including voice selection, audio format options, and caching capabilities.

Requirements:
- google-cloud-texttospeech library
- aiofiles library (`pip install aiofiles`)
"""

import os
import logging
import hashlib
import asyncio
import aiofiles
from typing import Optional, Dict, List, Tuple
# Import the asynchronous client
from google.cloud import texttospeech_async as texttospeech
from google.cloud.texttospeech import VoiceSelectionParams, AudioConfig, SynthesisInput

logger = logging.getLogger(__name__)

class GoogleCloudTTSAsync:
    """Async Google Cloud Text-to-Speech client with caching and voice management."""
    
    def __init__(self, cache_dir: str = "static/audio_cache", enable_caching: bool = True):
        """
        Initialize the async Google Cloud TTS client.
        """
        # Use the TextToSpeechAsyncClient
        self.client = texttospeech.TextToSpeechAsyncClient()
        self.cache_dir = cache_dir
        self.enable_caching = enable_caching
        
        if enable_caching:
            os.makedirs(cache_dir, exist_ok=True)
            
        self.default_voice = {
            'language_code': 'hi-IN',
            'name': 'hi-IN-Wavenet-D', # Using a standard Wavenet voice
            'ssml_gender': texttospeech.SsmlVoiceGender.FEMALE
        }
        self._voices_cache = None
        logger.info("Google Cloud TTS async client initialized")
    
    async def get_available_voices(self, language_code: str = None) -> List[Dict]:
        """
        Asynchronously get available voices from Google Cloud TTS.
        """
        try:
            if self._voices_cache is not None:
                voices = self._voices_cache
            else:
                # Await the async network call
                voices = await self.client.list_voices()
                self._voices_cache = voices
            
            available_voices = []
            for voice in voices.voices:
                voice_info = {
                    'name': voice.name,
                    'language_codes': list(voice.language_codes),
                    'ssml_gender': voice.ssml_gender.name,
                    'natural_sample_rate_hertz': voice.natural_sample_rate_hertz
                }
                if language_code is None or language_code in voice.language_codes:
                    available_voices.append(voice_info)
            
            logger.info(f"Found {len(available_voices)} voices for language: {language_code or 'all'}")
            return available_voices
            
        except Exception as e:
            logger.error(f"Error fetching available voices: {str(e)}")
            return []
    
    async def generate_speech(
        self,
        text: str,
        voice_name: str = None,
        language_code: str = None,
        ssml_gender: str = None,
        audio_encoding: str = 'MP3',
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
        volume_gain_db: float = 0.0,
        use_ssml: bool = False
    ) -> Optional[str]:
        """
        Asynchronously generate speech audio using Google Cloud TTS.
        """
        if not text.strip():
            logger.warning("Empty text provided for TTS")
            return None
        
        try:
            cache_key = self._generate_cache_key(
                text, voice_name, language_code, ssml_gender,
                audio_encoding, speaking_rate, pitch, volume_gain_db, use_ssml
            )
            
            if self.enable_caching:
                cached_file = self._get_cached_file(cache_key, audio_encoding)
                if cached_file:
                    logger.info(f"Using cached audio file: {cached_file}")
                    return cached_file
            
            voice_params = VoiceSelectionParams()
            if voice_name:
                voice_params.name = voice_name
            elif language_code:
                voice_params.language_code = language_code
                if ssml_gender:
                    voice_params.ssml_gender = getattr(texttospeech.SsmlVoiceGender, ssml_gender.upper())
            else:
                voice_params.language_code = self.default_voice['language_code']
                voice_params.name = self.default_voice['name']

            audio_config = AudioConfig(
                audio_encoding=getattr(texttospeech.AudioEncoding, audio_encoding.upper()),
                speaking_rate=speaking_rate, pitch=pitch, volume_gain_db=volume_gain_db
            )
            
            synthesis_input = SynthesisInput(ssml=text) if use_ssml else SynthesisInput(text=text)
            
            # Await the async network call
            response = await self.client.synthesize_speech(
                input=synthesis_input, voice=voice_params, audio_config=audio_config
            )
            
            file_extension = self._get_file_extension(audio_encoding)
            filename = f"speech_{cache_key}.{file_extension}"
            filepath = os.path.join(self.cache_dir, filename)
            
            # Use aiofiles for non-blocking file write
            async with aiofiles.open(filepath, 'wb') as f:
                await f.write(response.audio_content)
            
            logger.info(f"Generated speech audio: {filepath}")
            # The URL path returned is relative to the web server root
            return f"/static/audio_cache/{filename}"
            
        except Exception as e:
            logger.error(f"Error generating speech: {str(e)}")
            return None
    
    async def generate_speech_ssml(self, ssml_text: str, **kwargs) -> Optional[str]:
        """
        Asynchronously generate speech from SSML text.
        """
        return await self.generate_speech(ssml_text, use_ssml=True, **kwargs)
    
    # Helper methods below are synchronous as they don't perform I/O
    def _generate_cache_key(self, text: str, *args) -> str:
        content = f"{text}_{'_'.join(str(arg) for arg in args)}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_cached_file(self, cache_key: str, audio_encoding: str) -> Optional[str]:
        file_extension = self._get_file_extension(audio_encoding)
        filename = f"speech_{cache_key}.{file_extension}"
        filepath = os.path.join(self.cache_dir, filename)
        if os.path.exists(filepath):
            # Return URL path
            return f"/{self.cache_dir.replace('static/', '')}/{filename}"
        return None
        
    def _get_file_extension(self, audio_encoding: str) -> str:
        extensions = {'MP3': 'mp3', 'LINEAR16': 'wav', 'OGG_OPUS': 'ogg'}
        return extensions.get(audio_encoding.upper(), 'mp3')
    
    # Management methods are kept synchronous for simplicity, as they are not
    # typically part of a performance-critical request-response cycle.
    def clear_cache(self) -> bool:
        """Clear all cached audio files."""
        # This remains synchronous
        ...

    def get_cache_info(self) -> Dict:
        """Get information about cached files."""
        # This remains synchronous
        ...


# --- Main Async Test Block ---
async def main():
    """Main async function to run tests."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=== Google Cloud TTS Async Test ===")
    
    if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        print("WARNING: GOOGLE_APPLICATION_CREDENTIALS environment variable not set!")
        exit(1)
    
    tts = GoogleCloudTTSAsync()
    
    test_cases = [
        # ... (same test cases as before)
    ]
    
    # Await the async calls
    print(f"\nAvailable voices for English: {len(await tts.get_available_voices('en-US'))}")
    print(f"Available voices for Hindi: {len(await tts.get_available_voices('hi-IN'))}")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test {i}: {test_case['description']} ---")
        kwargs = {k: v for k, v in test_case.items() if k != 'description'}
        text = kwargs.pop('text')
        
        # Await the async speech generation
        audio_path = await tts.generate_speech(text, **kwargs)
        
        if audio_path:
            print(f"✅ SUCCESS: Audio generated at {audio_path}")
            file_path = audio_path.lstrip('/')
            if os.path.exists(file_path):
                print(f"📁 File verified: {os.path.getsize(file_path)} bytes")
            else:
                print("⚠️  WARNING: File not found at generated path")
        else:
            print("❌ FAILED: No audio path returned")

    print("\n=== Testing Complete ===")

if __name__ == "__main__":
    # Use asyncio.run() to execute the async main function
    asyncio.run(main())