"""
MoFA Video Generator Agent - Generates videos from images using KlingDemo API.
"""
import os
import sys
import json
import asyncio
import concurrent.futures
import logging
import base64
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List

# Import KlingDemo components (ensure these are in your environment)
try:
    from klingdemo.api import KlingAPIClient
    from klingdemo.models import ImageToVideoRequest
except ImportError:
    logging.error("KlingDemo package not found. Please install it to use this agent.")
    # Continue without raising error, so we don't crash the agent structure

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Optional Dify enhancement
try:
    from src.dify_enhancer import DifyEnhancer
    DIFY_AVAILABLE = True
except ImportError:
    logger.warning("Dify enhancer not available. Prompts will not be enhanced.")
    DIFY_AVAILABLE = False

class VideoGenerator:
    """Handles video generation from images using the KlingDemo API."""
    
    def __init__(self, kling_config: Dict[str, Any], output_dir: Path):
        """
        Initialize the video generator with API credentials.
        
        Args:
            kling_config: Configuration for the KlingAPIClient
            output_dir: Directory to save generated videos
        """
        self.output_dir = output_dir
        output_dir.mkdir(exist_ok=True, parents=True)
        
        # Initialize KlingAPIClient
        self.client = KlingAPIClient(
            access_key=kling_config.get('access_key'),
            secret_key=kling_config.get('secret_key'),
            base_url=kling_config.get('api_base_url', 'https://api.klingai.com'),
            timeout=kling_config.get('timeout', 120),
            max_retries=kling_config.get('max_retries', 3),
        )
        logger.info("Initialized video generator with KlingDemo client")
    
    async def generate_from_image(self, image_path: Path, prompt: str, frame_id: str, 
                                 mode: str = "std", duration: str = "5",
                                 model_name: str = "kling-v1") -> Optional[Path]:
        """
        Generate a video from an image using the KlingDemo API.
        
        Args:
            image_path: Path to the input image
            prompt: Text prompt describing the desired video
            frame_id: Identifier for the generated frame
            mode: Video generation mode ("std" or other options)
            duration: Video duration in seconds as a string
            model_name: Model to use for generation
            
        Returns:
            Path to the generated video, or None if generation failed
        """
        try:
            # Properly encode the image file to base64
            with open(image_path, "rb") as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Create image-to-video request
            request = ImageToVideoRequest(
                model_name=model_name,
                image=encoded_image,
                prompt=prompt,
                mode=mode,
                duration=duration
            )
            
            # Submit image-to-video task
            task = self.client.create_image_to_video_task(request)
            logger.info(f"Video generation task created with ID: {task.task_id}")
            
            # Custom polling logic to handle potential validation errors
            max_wait_time = 300  # 5 minutes max wait time
            check_interval = 5   # Check every 5 seconds
            elapsed = 0
            
            # Define task status check function for thread pool
            def get_task_status():
                try:
                    response = self.client._request("GET", f"/v1/videos/image2video/{task.task_id}")
                    return response
                except Exception as e:
                    logger.error(f"Error getting task status: {e}")
                    raise
            
            # Wait for the task to complete with polling
            completed_task = None
            while elapsed < max_wait_time:
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    response = await asyncio.get_event_loop().run_in_executor(pool, get_task_status)
                
                # Extract status from response directly
                if "data" in response:
                    data = response["data"]
                    
                    # Check for task_status in data
                    if isinstance(data, dict) and "task_status" in data:
                        status = data["task_status"]
                        logger.info(f"Task {task.task_id} status: {status}")
                        
                        if status == "succeed":
                            logger.info(f"Task {task.task_id} completed successfully")
                            completed_task = data
                            break
                        elif status == "failed":
                            error_msg = data.get("task_status_msg", "Unknown error")
                            logger.error(f"Task {task.task_id} failed: {error_msg}")
                            return None
                
                # Sleep before next check
                await asyncio.sleep(check_interval)
                elapsed += check_interval
            else:
                # Timed out
                logger.warning(f"Timeout waiting for video generation task {task.task_id}")
                return None
            
            # Process completed task result
            if completed_task and "task_result" in completed_task and completed_task["task_result"]:
                task_result = completed_task["task_result"]
                
                if "videos" in task_result and task_result["videos"]:
                    videos = task_result["videos"]
                    if videos and len(videos) > 0 and isinstance(videos[0], dict) and "url" in videos[0]:
                        video_url = videos[0]["url"]
                        output_path = self.output_dir / f"{frame_id}.mp4"
                        
                        # Download the video
                        response = requests.get(video_url)
                        with open(output_path, "wb") as f:
                            f.write(response.content)
                        
                        logger.info(f"Video downloaded to {output_path}")
                        return output_path
            
            logger.warning(f"No video generated for task {task.task_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error generating video: {e}")
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
        'timeout': int(os.environ.get('KLING_TIMEOUT', '120')),
        'max_retries': int(os.environ.get('KLING_MAX_RETRIES', '3'))
    }
    
    # Validate required fields
    if not config['access_key'] or not config['secret_key']:
        logger.warning("Missing required KlingDemo API credentials. Set KLING_ACCESS_KEY and KLING_SECRET_KEY in environment.")
    
    return config

def enhance_prompt_with_dify(original_prompt: str) -> str:
    """
    Enhance a prompt using Dify if available.
    
    Args:
        original_prompt: Original text prompt
        
    Returns:
        Enhanced prompt or original prompt if enhancement fails
    """
    if not DIFY_AVAILABLE:
        return original_prompt
        
    try:
        dify_enhancer = DifyEnhancer()
        enhanced_prompt = dify_enhancer.enhance_prompt(original_prompt)
        logger.info(f"Enhanced prompt using Dify: {enhanced_prompt[:50]}...")
        return enhanced_prompt
    except Exception as e:
        logger.warning(f"Failed to enhance prompt with Dify: {e}")
        return original_prompt

async def process_frame_images(frames_data: List[Dict[str, Any]], 
                            output_dir: Path,
                            model_name: str,
                            mode: str, 
                            duration: str,
                            use_dify: bool) -> List[Dict[str, Any]]:
    """
    Process frame images and generate videos.
    
    Args:
        frames_data: List of frame data with image paths
        output_dir: Directory to save generated videos
        model_name: Model name for video generation
        mode: Video generation mode
        duration: Video duration in seconds
        use_dify: Whether to use Dify for prompt enhancement
        
    Returns:
        List of dictionaries with processed video results
    """
    # Initialize video generator
    kling_config = load_kling_config()
    video_generator = VideoGenerator(kling_config, output_dir)
    
    results = []
    
    # Process each frame
    for frame in frames_data:
        frame_id = frame.get('frame_id')
        image_path = frame.get('image_path')
        prompt = frame.get('prompt', '')
        
        # Skip frames with no images
        if not image_path:
            logger.warning(f"Skipping frame {frame_id} with no image")
            results.append({
                "frame_id": frame_id,
                "status": "skipped",
                "reason": "No image available",
                "original_frame": frame
            })
            continue
            
        logger.info(f"Processing video for frame {frame_id}...")
        
        # Enhance prompt with Dify if enabled
        if use_dify:
            prompt = enhance_prompt_with_dify(prompt)
        
        # Generate video from image
        video_path = await video_generator.generate_from_image(
            image_path=Path(image_path),
            prompt=prompt,
            frame_id=frame_id,
            mode=mode,
            duration=duration,
            model_name=model_name
        )
        
        # Store result
        result = {
            "frame_id": frame_id,
            "image_path": image_path,
            "video_path": str(video_path) if video_path else None,
            "prompt": prompt,
            "status": "success" if video_path else "failed",
            "original_frame": frame
        }
        results.append(result)
        
    return results

async def process_input_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process input message containing image paths and generate videos.
    
    Args:
        message: Input message from previous agent
        
    Returns:
        Output message with generated video paths
    """
    # Extract parameters
    frames = message.get('frames', [])
    model_name = os.environ.get('KLING_MODEL_NAME', 'kling-v1')
    mode = os.environ.get('DEFAULT_MODE', 'std')
    duration = os.environ.get('DEFAULT_DURATION', '5')
    output_dir_str = os.environ.get('OUTPUT_DIR', 'workflow/outputs/videos')
    use_dify = os.environ.get('USE_DIFY', 'false').lower() == 'true'
    
    # Set up output directory
    output_dir = Path(output_dir_str)
    output_dir.mkdir(exist_ok=True, parents=True)
    
    if not frames:
        logger.error("No frames provided in input message")
        return {
            "status": "error",
            "error": "No frames provided in input message"
        }
    
    try:
        # Process frames
        results = await process_frame_images(
            frames_data=frames,
            output_dir=output_dir,
            model_name=model_name,
            mode=mode,
            duration=duration,
            use_dify=use_dify
        )
        
        # Create output message
        output = {
            "status": "success",
            "videos": results,
            "count": len(results),
            "metadata": {
                "model_name": model_name,
                "output_dir": str(output_dir),
                "mode": mode,
                "duration": duration,
                "dify_used": use_dify
            }
        }
        
        return output
        
    except Exception as e:
        logger.error(f"Error processing frames: {e}")
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
        logger.info(f"Received message with {len(message.get('frames', []))} frames")
        
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