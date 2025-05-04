"""
MoFA Result Logger Agent - Collects and logs results from the workflow.
"""
import os
import sys
import json
import logging
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ResultLogger:
    """Handles collecting and logging workflow results."""
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize the result logger.
        
        Args:
            output_dir: Directory to save result logs
        """
        self.output_dir = output_dir or Path("workflow/logs")
        self.output_dir.mkdir(exist_ok=True, parents=True)
        logger.info(f"Initialized result logger with output directory: {self.output_dir}")
    
    def log_results(self, video_results: List[Dict[str, Any]], 
                   music_result: Optional[Dict[str, Any]] = None,
                   run_id: Optional[str] = None) -> Path:
        """
        Log the workflow results to a JSON file.
        
        Args:
            video_results: List of video generation results
            music_result: Music generation result
            run_id: Unique identifier for the workflow run
            
        Returns:
            Path to the log file
        """
        # Generate run ID if not provided
        if not run_id:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            run_id = f"run_{timestamp}"
        
        # Create log entry
        log_entry = {
            "run_id": run_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "video_results": video_results,
            "music_result": music_result,
            "summary": {
                "video_frames": len(video_results),
                "successful_videos": sum(1 for v in video_results if v.get("status") == "success"),
                "failed_videos": sum(1 for v in video_results if v.get("status") == "failed"),
                "music_generated": music_result is not None and music_result.get("status") == "success"
            }
        }
        
        # Write log to file
        log_file = self.output_dir / f"{run_id}.json"
        with open(log_file, 'w') as f:
            json.dump(log_entry, f, indent=2)
            
        logger.info(f"Results logged to {log_file}")
        
        # Generate human-readable summary in markdown format
        summary_file = self.output_dir / f"{run_id}_summary.md"
        self._generate_markdown_summary(log_entry, summary_file)
        
        return log_file
    
    def _generate_markdown_summary(self, log_entry: Dict[str, Any], output_file: Path) -> None:
        """
        Generate a human-readable summary in markdown format.
        
        Args:
            log_entry: Log entry dictionary
            output_file: Path to save the markdown summary
        """
        summary = log_entry["summary"]
        video_results = log_entry["video_results"]
        music_result = log_entry["music_result"]
        
        # Build markdown content
        lines = [
            f"# Workflow Results Summary - {log_entry['run_id']}",
            f"Generated on: {log_entry['timestamp']}",
            "",
            "## Overview",
            f"- Total video frames: {summary['video_frames']}",
            f"- Successful videos: {summary['successful_videos']}",
            f"- Failed videos: {summary['failed_videos']}",
            f"- Music track generated: {'Yes' if summary['music_generated'] else 'No'}",
            "",
            "## Video Results",
            ""
        ]
        
        # Add video results
        for i, video in enumerate(video_results):
            frame_id = video.get("frame_id", f"Frame {i+1}")
            status = video.get("status", "unknown")
            video_path = video.get("video_path", "Not available")
            image_path = video.get("image_path", "Not available")
            prompt = video.get("prompt", "")[:50] + ("..." if len(video.get("prompt", "")) > 50 else "")
            
            lines.extend([
                f"### {frame_id}",
                f"- Status: {status}",
                f"- Video: {video_path}",
                f"- Source image: {image_path}",
                f"- Prompt: {prompt}",
                ""
            ])
        
        # Add music result if available
        if music_result:
            music_status = music_result.get("status", "unknown")
            music_path = music_result.get("music_path", "Not available")
            music_prompt = music_result.get("metadata", {}).get("prompt", "")[:50]
            music_prompt += "..." if len(music_result.get("metadata", {}).get("prompt", "")) > 50 else ""
            
            lines.extend([
                "## Music Result",
                f"- Status: {music_status}",
                f"- File: {music_path}",
                f"- Prompt: {music_prompt}",
                ""
            ])
        
        # Write to file
        with open(output_file, 'w') as f:
            f.write("\n".join(lines))
            
        logger.info(f"Markdown summary generated at {output_file}")

def process_input_messages(video_message: Dict[str, Any], music_message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process input messages from video and music generators and log results.
    
    Args:
        video_message: Message from video generator agent
        music_message: Message from music generator agent
        
    Returns:
        Output message with results summary
    """
    # Extract video results and music result
    video_results = video_message.get("videos", [])
    
    # Generate a unique run ID
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"run_{timestamp}"
    
    # Initialize result logger
    output_dir = Path(os.environ.get("LOG_DIR", "workflow/logs"))
    result_logger = ResultLogger(output_dir)
    
    try:
        # Log the results
        log_file = result_logger.log_results(
            video_results=video_results,
            music_result=music_message,
            run_id=run_id
        )
        
        # Count successes and failures
        successful_videos = sum(1 for v in video_results if v.get("status") == "success")
        failed_videos = sum(1 for v in video_results if v.get("status") == "failed")
        music_success = music_message.get("status") == "success"
        
        # Generate output message
        output = {
            "status": "success",
            "run_id": run_id,
            "summary": {
                "total_frames": len(video_results),
                "successful_videos": successful_videos,
                "failed_videos": failed_videos,
                "music_generated": music_success,
                "log_file": str(log_file)
            },
            "video_paths": [v.get("video_path") for v in video_results if v.get("status") == "success"],
            "music_path": music_message.get("music_path")
        }
        
        logger.info(f"Results processed and logged with run ID: {run_id}")
        return output
        
    except Exception as e:
        logger.error(f"Error logging results: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        return {
            "status": "error",
            "error": str(e),
            "run_id": run_id
        }

def main():
    """Main entry point for the agent."""
    try:
        # Get the input message from stdin
        input_data = sys.stdin.buffer.read().decode('utf-8')
        message = json.loads(input_data)
        
        # Extract video and music messages from inputs
        video_message = message.get("video_frame_in", {})
        music_message = message.get("music_track_in", {})
        
        logger.info(f"Received video results with {len(video_message.get('videos', []))} videos")
        logger.info(f"Received music result with status: {music_message.get('status')}")
        
        # Process the messages
        output = process_input_messages(video_message, music_message)
        
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