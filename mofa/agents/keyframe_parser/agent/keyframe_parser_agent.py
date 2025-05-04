"""
MoFA Keyframe Parser Agent - Parses keyframe files and forwards data to image generation.
"""
import os
import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class KeyframeData:
    """Keyframe data model for MoFA framework."""
    
    def __init__(self, prompt: str, negative_prompt: Optional[str] = None, 
                 frame_number: Optional[int] = None, timestamp: Optional[str] = None, 
                 aspect_ratio: Optional[str] = None, seed: Optional[int] = None):
        """
        Initialize keyframe data.
        
        Args:
            prompt: Text prompt for image generation
            negative_prompt: Negative prompt for guiding image generation away from certain concepts
            frame_number: Sequential frame number
            timestamp: Timestamp for video timelines (if applicable)
            aspect_ratio: Aspect ratio for generated content
            seed: Random seed for reproducibility
        """
        self.prompt = prompt
        self.negative_prompt = negative_prompt
        self.frame_number = frame_number
        self.timestamp = timestamp
        self.aspect_ratio = aspect_ratio
        self.seed = seed
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "prompt": self.prompt,
            "negative_prompt": self.negative_prompt,
            "frame_number": self.frame_number,
            "timestamp": self.timestamp,
            "aspect_ratio": self.aspect_ratio,
            "seed": self.seed
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KeyframeData':
        """Create from dictionary."""
        return cls(
            prompt=data.get("prompt", ""),
            negative_prompt=data.get("negative_prompt"),
            frame_number=data.get("frame_number"),
            timestamp=data.get("timestamp"),
            aspect_ratio=data.get("aspect_ratio"),
            seed=data.get("seed")
        )

def parse_keyframe_file(file_path: Path) -> List[KeyframeData]:
    """
    Parse keyframe file and extract keyframe data.
    
    Args:
        file_path: Path to keyframe file
        
    Returns:
        List of KeyframeData objects
    """
    keyframes = []
    current_frame = {}
    
    logger.info(f"Parsing keyframe file: {file_path}")
    
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
    except Exception as e:
        logger.error(f"Failed to open keyframe file: {e}")
        raise
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
            
        if line.startswith("---"):
            # New keyframe
            if current_frame and "prompt" in current_frame:
                keyframes.append(KeyframeData(
                    prompt=current_frame.get("prompt", ""),
                    negative_prompt=current_frame.get("negative_prompt"),
                    frame_number=current_frame.get("frame_number"),
                    aspect_ratio=current_frame.get("aspect_ratio", "16:9"),
                    seed=current_frame.get("seed")
                ))
            current_frame = {}
            continue
        
        # Parse key-value pairs
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip().lower()
            value = value.strip()
            
            if key == "frame" or key == "frame_number":
                try:
                    current_frame["frame_number"] = int(value)
                except ValueError:
                    pass
            elif key == "prompt":
                current_frame["prompt"] = value
            elif key == "negative_prompt":
                current_frame["negative_prompt"] = value
            elif key == "aspect_ratio":
                current_frame["aspect_ratio"] = value
            elif key == "seed":
                try:
                    current_frame["seed"] = int(value)
                except ValueError:
                    pass
    
    # Add the last keyframe
    if current_frame and "prompt" in current_frame:
        keyframes.append(KeyframeData(
            prompt=current_frame.get("prompt", ""),
            negative_prompt=current_frame.get("negative_prompt"),
            frame_number=current_frame.get("frame_number"),
            aspect_ratio=current_frame.get("aspect_ratio", "16:9"),
            seed=current_frame.get("seed")
        ))
    
    logger.info(f"Successfully parsed {len(keyframes)} keyframes")
    return keyframes


def process_input_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process input message and parse keyframes.
    
    Args:
        message: Input message containing keyframe file path
        
    Returns:
        Output message with parsed keyframe data
    """
    # Extract parameters from input message
    keyframes_file = message.get("keyframes_file")
    default_aspect_ratio = message.get("default_aspect_ratio", "16:9")
    frame_id_prefix = message.get("frame_id_prefix", "frame_")
    
    if not keyframes_file:
        logger.error("Missing required parameter 'keyframes_file'")
        return {"error": "Missing required parameter 'keyframes_file'"}
    
    # Parse keyframes
    try:
        keyframe_path = Path(keyframes_file)
        keyframes_data = parse_keyframe_file(keyframe_path)
        
        # Convert to serializable format
        serialized_keyframes = [kf.to_dict() for kf in keyframes_data]
        
        # Create output message
        output = {
            "status": "success",
            "keyframes": serialized_keyframes,
            "count": len(serialized_keyframes),
            "metadata": {
                "source_file": str(keyframe_path),
                "default_aspect_ratio": default_aspect_ratio,
                "frame_id_prefix": frame_id_prefix
            }
        }
        
        return output
    
    except Exception as e:
        logger.error(f"Error processing keyframes: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "error": str(e),
            "metadata": {
                "source_file": keyframes_file
            }
        }


def main():
    """Main entry point for the agent."""
    # Get the input message from stdin
    try:
        input_data = sys.stdin.buffer.read().decode('utf-8')
        message = json.loads(input_data)
        logger.info(f"Received message: {message}")
        
        # Process the message
        output = process_input_message(message)
        
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


if __name__ == "__main__":
    main()