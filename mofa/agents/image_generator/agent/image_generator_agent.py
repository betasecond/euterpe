"""
MoFA Image Generator Agent - Generates images from keyframe data using KlingDemo API.
"""
import os
import sys
import json
import asyncio
import concurrent.futures
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

# Import KlingDemo components (ensure these are in your environment)
try:
    from klingdemo.api import KlingAPIClient
    from klingdemo.models import ImageGenerationRequest
except ImportError:
    logging.error("KlingDemo package not found. Please install it to use this agent.")
    # Continue without raising error, so we don't crash the agent structure

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ImageGenerator:
    """Handles image generation using the KlingDemo API."""
    
    def __init__(self, kling_config: Dict[str, Any], output_dir: Path):
        """
        Initialize the image generator with API credentials.
        
        Args:
            kling_config: Configuration for the KlingAPIClient
            output_dir: Directory to save generated images
        """
        self.output_dir = output_dir
        output_dir.mkdir(exist_ok=True, parents=True)
        
        # Initialize KlingAPIClient
        self.client = KlingAPIClient(
            access_key=kling_config.get('access_key'),
            secret_key=kling_config.get('secret_key'),
            base_url=kling_config.get('api_base_url', 'https://api.klingai.com'),
            timeout=kling_config.get('timeout', 60),
            max_retries=kling_config.get('max_retries', 3),
        )
        logger.info("Initialized image generator with KlingDemo client")
    
    async def generate(self, prompt: str, model_name: str = "kling-v1-5", 
                      negative_prompt: str = "", aspect_ratio: str = "16:9", 
                      seed: Optional[int] = None, frame_id: str = None) -> Optional[Path]:
        """
        Generate an image using the KlingDemo API.
        
        Args:
            prompt: Text prompt describing the desired image
            model_name: Model to use for generation
            negative_prompt: Elements to avoid in the image
            aspect_ratio: Image aspect ratio (e.g., "16:9")
            seed: Random seed for reproducibility
            frame_id: Identifier for the generated frame
            
        Returns:
            Path to the generated image, or None if generation failed
        """
        try:
            # Create image generation request
            request = ImageGenerationRequest(
                model_name=model_name,
                prompt=prompt,
                negative_prompt=negative_prompt,
                n=1,
                aspect_ratio=aspect_ratio,
                seed=seed
            )
            
            # Submit image generation task
            task = self.client.create_image_generation_task(request)
            logger.info(f"Image generation task created with ID: {task.task_id}")
            
            # Wait for task completion - Run blocking method in a thread pool
            def run_task_wait():
                return self.client.wait_for_image_generation_completion(task.task_id)
            
            # Use run_in_executor to run the blocking operation in a thread pool
            with concurrent.futures.ThreadPoolExecutor() as pool:
                completed_task = await asyncio.get_event_loop().run_in_executor(pool, run_task_wait)
            
            # Save image locally
            if completed_task.task_result and completed_task.task_result.images:
                image_url = completed_task.task_result.images[0].url
                
                # Use frame_id in the filename if provided
                filename = f"{frame_id}.png" if frame_id else f"image_{task.task_id}.png"
                output_path = self.output_dir / filename
                
                # Download the image
                import requests
                response = requests.get(image_url)
                with open(output_path, "wb") as f:
                    f.write(response.content)
                
                logger.info(f"Image downloaded to {output_path}")
                return output_path
            
            logger.warning(f"No images generated for task {task.task_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error generating image: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

def load_kling_config() -> Dict[str, Any]:
    """
    Load KlingDemo configuration from environment variables.
    
    Returns:
        Dictionary with KlingDemo configuration
    """
    # Load from environment variables
    config = {
        'access_key': os.environ.get('KLING_ACCESS_KEY'),
        'secret_key': os.environ.get('KLING_SECRET_KEY'),
        'api_base_url': os.environ.get('KLING_API_BASE_URL', 'https://api.klingai.com'),
        'timeout': int(os.environ.get('KLING_TIMEOUT', '60')),
        'max_retries': int(os.environ.get('KLING_MAX_RETRIES', '3'))
    }
    
    # Validate required fields
    if not config['access_key'] or not config['secret_key']:
        logger.warning("Missing required KlingDemo API credentials. Set KLING_ACCESS_KEY and KLING_SECRET_KEY in environment.")
    
    return config

async def process_keyframes(keyframes_data: List[Dict[str, Any]], 
                         output_dir: Path, 
                         model_name: str, 
                         frame_id_prefix: str) -> List[Dict[str, Any]]:
    """
    Process keyframes and generate images.
    
    Args:
        keyframes_data: List of keyframe data dictionaries
        output_dir: Directory to save generated images
        model_name: Model name for image generation
        frame_id_prefix: Prefix for frame IDs
        
    Returns:
        List of dictionaries with processed keyframe results
    """
    # Initialize image generator
    kling_config = load_kling_config()
    image_generator = ImageGenerator(kling_config, output_dir)
    
    results = []
    
    # Process each keyframe
    for idx, keyframe in enumerate(keyframes_data):
        # Create frame ID
        frame_number = keyframe.get('frame_number') or (idx + 1)
        frame_id = f"{frame_id_prefix}{frame_number}"
        
        # Extract keyframe parameters
        prompt = keyframe.get('prompt', '')
        negative_prompt = keyframe.get('negative_prompt', '')
        aspect_ratio = keyframe.get('aspect_ratio', '16:9')
        seed = keyframe.get('seed')
        
        logger.info(f"Processing keyframe {frame_id}: {prompt[:30]}...")
        
        # Generate image
        image_path = await image_generator.generate(
            prompt=prompt,
            model_name=model_name,
            negative_prompt=negative_prompt,
            aspect_ratio=aspect_ratio,
            seed=seed,
            frame_id=frame_id
        )
        
        # Store result
        result = {
            "frame_id": frame_id,
            "frame_number": frame_number,
            "prompt": prompt,
            "image_path": str(image_path) if image_path else None,
            "status": "success" if image_path else "failed",
            "original_keyframe": keyframe
        }
        results.append(result)
        
    return results

async def process_input_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process input message containing keyframe data and generate images.
    
    Args:
        message: Input message from previous agent
        
    Returns:
        Output message with generated image paths
    """
    # Extract parameters
    keyframes = message.get('keyframes', [])
    model_name = os.environ.get('KLING_MODEL_NAME', 'kling-v1-5')
    output_dir_str = os.environ.get('OUTPUT_DIR', 'workflow/outputs/images')
    frame_id_prefix = message.get('metadata', {}).get('frame_id_prefix', 'frame_')
    
    # Set up output directory
    output_dir = Path(output_dir_str)
    output_dir.mkdir(exist_ok=True, parents=True)
    
    if not keyframes:
        logger.error("No keyframes provided in input message")
        return {
            "status": "error",
            "error": "No keyframes provided in input message"
        }
    
    try:
        # Process keyframes
        results = await process_keyframes(
            keyframes_data=keyframes,
            output_dir=output_dir,
            model_name=model_name,
            frame_id_prefix=frame_id_prefix
        )
        
        # Create output message
        output = {
            "status": "success",
            "frames": results,
            "count": len(results),
            "metadata": {
                "model_name": model_name,
                "output_dir": str(output_dir)
            }
        }
        
        return output
        
    except Exception as e:
        logger.error(f"Error processing keyframes: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        return {
            "status": "error",
            "error": str(e)
        }

async def main_async():
    """Async main function for the agent."""
    # Get the input message from stdin
    try:
        input_data = sys.stdin.buffer.read().decode('utf-8')
        message = json.loads(input_data)
        logger.info(f"Received message with {len(message.get('keyframes', []))} keyframes")
        
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