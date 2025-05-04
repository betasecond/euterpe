"""
Terminal Input Node for MoFA Framework.
Handles receiving initial parameters from terminal input.
"""
import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_arguments() -> Dict[str, Any]:
    """Parse command line arguments for the workflow."""
    parser = argparse.ArgumentParser(description="Video generation workflow with MoFA")
    
    parser.add_argument(
        "--keyframes-file",
        type=str,
        default="workflow/keyframes.txt",
        help="Path to the keyframes file"
    )
    
    parser.add_argument(
        "--model-name",
        type=str,
        default="kling-v1-5",
        help="Model name for image generation"
    )
    
    parser.add_argument(
        "--video-model-name",
        type=str,
        default="kling-v1",
        help="Model name for video generation"
    )
    
    parser.add_argument(
        "--use-dify",
        action="store_true",
        help="Use Dify to enhance prompts for video generation"
    )
    
    parser.add_argument(
        "--music-prompt",
        type=str,
        default=None,
        help="Prompt for generating background music for the entire workflow"
    )
    
    parser.add_argument(
        "--music-filename",
        type=str,
        default="background_music",
        help="Filename for the generated music file (without extension)"
    )
    
    return vars(parser.parse_args())

def main():
    """
    Main entry point for the terminal input node.
    
    Parses command line arguments and forwards them to the next node.
    """
    try:
        # Parse arguments
        args = parse_arguments()
        
        # Convert Path objects to strings for JSON serialization
        for key, value in args.items():
            if isinstance(value, Path):
                args[key] = str(value)
        
        logger.info(f"Parsed input parameters: {args}")
        
        # Output the arguments as JSON to be consumed by the next node
        sys.stdout.buffer.write(json.dumps(args).encode('utf-8'))
        
    except Exception as e:
        logger.error(f"Error processing terminal input: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Send error response
        error_output = {"status": "error", "error": str(e)}
        sys.stdout.buffer.write(json.dumps(error_output).encode('utf-8'))

if __name__ == "__main__":
    main()