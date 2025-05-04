"""
MoFA Music Generator Agent - Generates background music using Beatoven.ai API.
"""
import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Import Beatoven components (ensure these are in your environment)
try:
    import aiohttp
    import beatoven_ai
    from beatoven_ai.beatoven_ai.config import get_settings
    from beatoven_ai import BeatovenClient
    BEATOVEN_AVAILABLE = True
except ImportError:
    logging.error("Beatoven package not found. Please install it to use this agent.")
    BEATOVEN_AVAILABLE = False

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MusicGenerator:
    """Handles music generation using BeatovenDemo."""
    
    def __init__(self, api_key: Optional[str] = None, api_url: Optional[str] = None, output_dir: Optional[Path] = None, env_file: Optional[str] = None):
        """
        Initialize the music generator with API credentials.
        
        Args:
            api_key: Beatoven API key (overrides env_file settings)
            api_url: Beatoven API URL (overrides env_file settings)
            output_dir: Directory to save generated music files (overrides env_file settings)
            env_file: Path to environment file for settings
        """
        if not BEATOVEN_AVAILABLE:
            logger.error("Cannot initialize MusicGenerator: Beatoven package is not available")
            return
            
        # Load settings either from env_file or use defaults with overrides
        if env_file:
            self.settings = get_settings(env_file)
        else:
            self.settings = beatoven_ai.settings
            
        # Override settings with explicit parameters if provided
        if api_key:
            self.settings.API_KEY = api_key
        if api_url:
            self.settings.API_URL = api_url
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            self.settings.OUTPUT_DIR = str(output_dir)
            
        # Initialize client with our settings
        self.client = BeatovenClient(
            api_key=self.settings.API_KEY
        )
        
        logger.info("Initialized music generator with Beatoven settings")
    
    async def generate(self, prompt: str, duration: int = None, 
                      format: str = None, filename: str = "background_music") -> Optional[Path]:
        """
        Generate music based on a text prompt.
        
        Args:
            prompt: Text prompt describing the desired music
            duration: Music duration in seconds (uses DEFAULT_DURATION from settings if None)
            format: Output audio format (mp3, wav, ogg) (uses DEFAULT_FORMAT from settings if None)
            filename: Output filename (without extension)
            
        Returns:
            Path to the generated audio file, or None if generation failed
        """
        if not BEATOVEN_AVAILABLE:
            logger.error("Cannot generate music: Beatoven package is not available")
            return None
            
        if not self.settings.API_KEY:
            logger.warning("Cannot generate music: Beatoven API key is not configured")
            return None
        
        # Use settings defaults if parameters not provided
        if duration is None:
            duration = self.settings.DEFAULT_DURATION
        if format is None:
            format = self.settings.DEFAULT_FORMAT
            
        try:
            logger.info(f"Generating music with prompt: {prompt[:50]}...")
            
            # Create output directory if it doesn't exist
            output_dir = Path(self.settings.OUTPUT_DIR)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Use the client's generate_music method which handles the session internally
            output_path = await self.client.generate_music(
                prompt=prompt,
                duration=duration,
                format=format,
                output_path=str(output_dir),
                filename=filename
            )
            
            logger.info(f"Music generated at: {output_path}")
            return Path(output_path)
            
        except Exception as e:
            logger.error(f"Failed to generate music: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

def load_beatoven_config() -> Dict[str, Any]:
    """
    Load Beatoven configuration from environment variables.
    
    Returns:
        Dictionary with Beatoven configuration
    """
    # Load from environment variables
    config = {
        'api_key': os.environ.get('BEATOVEN_API_KEY'),
        'api_url': os.environ.get('BEATOVEN_API_URL', 'https://api.beatoven.ai/v1'),
        'output_dir': os.environ.get('BEATOVEN_OUTPUT_DIR', 'workflow/outputs/music'),
        'default_duration': int(os.environ.get('DEFAULT_DURATION', '180')),
        'default_format': os.environ.get('DEFAULT_FORMAT', 'mp3'),
        'default_filename': os.environ.get('DEFAULT_FILENAME', 'background_music'),
        'polling_interval': int(os.environ.get('POLLING_INTERVAL', '5')),
        'request_timeout': int(os.environ.get('REQUEST_TIMEOUT', '30')),
        'download_timeout': int(os.environ.get('DOWNLOAD_TIMEOUT', '60'))
    }
    
    # Validate required fields
    if not config['api_key']:
        logger.warning("Missing Beatoven API key. Set BEATOVEN_API_KEY in environment.")
    
    return config

async def process_music_request(message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process music generation request from the input message.
    
    Args:
        message: Input message containing music prompt
        
    Returns:
        Output message with generated music path
    """
    # Extract parameters from message
    prompt = message.get('music_prompt')
    filename = message.get('music_filename', 'background_music')
    
    # Load configuration
    config = load_beatoven_config()
    output_dir = Path(config['output_dir'])
    
    # Ensure output directory exists
    output_dir.mkdir(exist_ok=True, parents=True)
    
    if not prompt:
        logger.warning("No music prompt provided, using default generic prompt")
        prompt = "Create a calming, atmospheric background music suitable for video content"
    
    try:
        # Initialize music generator
        music_generator = MusicGenerator(
            api_key=config['api_key'],
            api_url=config['api_url'],
            output_dir=output_dir
        )
        
        # Generate music
        music_path = await music_generator.generate(
            prompt=prompt,
            duration=config['default_duration'],
            format=config['default_format'],
            filename=filename
        )
        
        if not music_path:
            return {
                "status": "error",
                "error": "Failed to generate music",
                "metadata": {
                    "prompt": prompt,
                    "filename": filename
                }
            }
        
        # Return success response
        return {
            "status": "success",
            "music_path": str(music_path),
            "metadata": {
                "prompt": prompt,
                "format": config['default_format'],
                "duration": config['default_duration'],
                "filename": filename
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating music: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        return {
            "status": "error",
            "error": str(e),
            "metadata": {
                "prompt": prompt,
                "filename": filename
            }
        }

async def process_input_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process input message and generate music.
    
    Args:
        message: Input message from start node
        
    Returns:
        Output message with generated music path
    """
    # Extract specific parameters for music generation
    music_params = {
        "music_prompt": message.get("music_prompt"),
        "music_filename": message.get("music_filename", "background_music")
    }
    
    # Generate music
    result = await process_music_request(music_params)
    
    return result

async def main_async():
    """Async main function for the agent."""
    # Get the input message from stdin
    try:
        input_data = sys.stdin.buffer.read().decode('utf-8')
        message = json.loads(input_data)
        logger.info(f"Received message: {message}")
        
        # Process the message
        output = await process_input_message(message)
        
        # Send the output to stdout
        sys.stdout.buffer.write(json.dumps(output).encode('utf-8'))
        logger.info("Processing complete")
        
    except Exception as e:
        logger.error(f"Error in main function: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Send error response
        error_output = {"status": "error", "error": str(e)}
        sys.stdout.buffer.write(json.dumps(error_output).encode('utf-8'))

def main():
    """Main entry point for the agent."""
    asyncio.run(main_async())

if __name__ == "__main__":
    main()