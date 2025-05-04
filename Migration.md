很好！理解了 MoFA 的设计哲学和基本用法后，我们可以将之前的初步方案具体化，使其更符合 MoFA 的实践。核心思想是利用 MoFA 提供的 `@run_agent` 装饰器和 `MofaAgent` 类来简化 Operator（现在称为 Agent）的开发。

**再次确认可行性:**

*   MoFA 的数据流和 Agent 组合理念非常适合你的项目结构。
*   `@run_agent` 和 `MofaAgent` API 可以简化事件处理、输入/输出和日志记录。
*   通过 `.env.secret` 管理 API 密钥是标准且安全的做法。
*   将你的 Python 功能模块封装成独立的 Agent 是清晰且可行的。

**精炼后的迁移方案 (结合 MoFA 文档)**

1.  **项目结构 (采用 MoFA Agent 结构):**
    *   我们将每个 Operator 视为一个 MoFA Agent，并使用 `mofa new-agent` (或手动创建类似结构) 来组织代码。

    ```
    .
    ├── video_gen_dataflow.yml  # DORA/MoFA 数据流定义
    ├── .env.secret             # 存放所有 API Keys (Kling, Beatoven, Dify)
    ├── configs/                # 存放非敏感配置 (YAML)
    │   ├── keyframe_parser_config.yml
    │   ├── image_generator_config.yml
    │   ├── video_generator_config.yml # 包含 use_dify 等
    │   ├── music_generator_config.yml
    │   └── ...
    ├── agents/                 # MoFA Agent 目录
    │   ├── keyframe_parser/    # Agent 1
    │   │   ├── agent/
    │   │   │   ├── configs/agent.yml # 可选：Agent特定配置，或留空
    │   │   │   └── main.py           # Agent 核心逻辑
    │   │   ├── pyproject.toml      # Agent 依赖 (可指向项目根目录的 requirements)
    │   │   └── README.md
    │   ├── image_generator/    # Agent 2
    │   │   └── ... (类似结构)
    │   ├── video_generator/    # Agent 3
    │   │   └── ...
    │   ├── music_generator/    # Agent 4 (并行)
    │   │   └── ...
    │   └── result_logger/      # Agent 5 (Sink)
    │       └── ...
    ├── nodes/                  # 标准 DORA 节点 (如 terminal-input)
    │   └── terminal-input/     # (如果需要自定义启动或使用 MoFA 提供的)
    ├── requirements.txt        # 项目总依赖
    └── README.md
    ```

2.  **配置策略:**
    *   **API Keys:** 全部放入项目根目录下的 `.env.secret` 文件。
        ```.env.secret
        # Kling API
        KLING_ACCESS_KEY=your_kling_access_key
        KLING_SECRET_KEY=your_kling_secret_key
        KLING_API_BASE_URL=https://api.klingai.com # Or your endpoint

        # Beatoven API
        BEATOVEN_API_KEY=your_beatoven_api_key
        BEATOVEN_API_URL=https://api.beatoven.ai/v1 # Check actual URL
        BEATOVEN_OUTPUT_DIR=./workflow/outputs/music # Example output dir relative to where agent runs

        # Dify API (if used directly)
        DIFY_API_KEY=your_dify_api_key
        DIFY_API_URL=https://api.dify.ai/v1
        ```
    *   **其他配置:** 放入 `configs/` 目录下的 YAML 文件。Agent 在其 `main.py` 中加载这些 YAML 文件和 `.env.secret`。
        *   `video_generator_config.yml` 示例:
            ```yaml
            VIDEO_GENERATOR:
              KLING_MODEL_NAME: "kling-v1"
              DEFAULT_MODE: "std"
              DEFAULT_DURATION: "5"
              USE_DIFY: true # 控制是否启用 Dify 增强
              # Dify API Key/URL 从 .env.secret 读取, 这里不用写
              # Kling API Key/URL/Secret 从 .env.secret 读取
            ```

3.  **Dataflow 定义 (`video_gen_dataflow.yml`):**
    *   使用 MoFA Agent 的 `build` 和 `path` 语法。
    *   为 `result-logger` 设置 `IS_DATAFLOW_END: true` (如果它是流程的终点)。
    *   为调试方便，可以给所有 Agent 设置 `WRITE_LOG: true`。

    ```yaml
    nodes:
      # 1. 启动节点 (可以使用 MoFA 提供的 terminal-input 或自定义)
      #    假设它输出一个包含初始参数（如 keyframes 文件路径、音乐 prompt）的字典
      - id: start-input          # Renamed for clarity
        build: pip install -e ./nodes/terminal-input # Or path to MoFA's standard node
        path: dynamic            # Assuming standard terminal-input
        outputs: [start_params]  # Output name carrying initial parameters dict
        # inputs: {} # terminal-input usually doesn't have inputs from agents initially

      # 2. Keyframe 解析 Agent
      - id: keyframe-parser
        build: pip install -e ./agents/keyframe_parser # Build this specific agent
        path: agents/keyframe_parser          # Path to the agent's root dir
        inputs:
          trigger_params: start-input/start_params # Input name defined in agent's main.py
        outputs: [keyframe_data_out]        # Output name defined in agent's main.py

      # 3. 图像生成 Agent
      - id: image-generator
        build: pip install -e ./agents/image_generator
        path: agents/image_generator
        inputs:
          keyframe_info_in: keyframe-parser/keyframe_data_out # Input name matches output above
        outputs: [image_result_out]
        env:
          WRITE_LOG: true

      # 4. 视频生成 Agent
      - id: video-generator
        build: pip install -e ./agents/video_generator
        path: agents/video_generator
        inputs:
          image_info_in: image-generator/image_result_out
        outputs: [video_result_out]
        env:
          WRITE_LOG: true
          # IS_DATAFLOW_END: true # Maybe set this if music is optional/not always run

      # 5. 音乐生成 Agent (并行分支)
      - id: music-generator
        build: pip install -e ./agents/music_generator
        path: agents/music_generator
        inputs:
          trigger_params: start-input/start_params # Receives initial params too
        outputs: [music_result_out]
        env:
          WRITE_LOG: true
          # IS_DATAFLOW_END: true # Music might finish before video, careful with this flag

      # 6. 结果日志 Agent (Sink)
      - id: result-logger
        build: pip install -e ./agents/result_logger
        path: agents/result_logger
        inputs:
          video_frame_in: video-generator/video_result_out
          music_track_in: music-generator/music_result_out # Will receive only if music runs
        outputs: [] # No outputs, it's a sink
        env:
          WRITE_LOG: true
          IS_DATAFLOW_END: true # This node truly marks the end of processing for a cycle
    ```

4.  **Agent 实现 (`agents/<agent_name>/agent/main.py`):**
    *   **基本结构:**

        ```python
        # agents/image_generator/agent/main.py (Example)
        import os
        import sys
        from pathlib import Path
        import asyncio
        from dotenv import load_dotenv
        import yaml # To load config YAML

        # MoFA imports
        from mofa.agent_build.base.base_agent import MofaAgent, run_agent

        # Your original project imports (adjust paths if needed)
        # Assuming your original 'src' is accessible or refactored into agent libs
        # Example: Add project root to sys.path if necessary, or structure differently
        project_root = Path(__file__).parent.parent.parent.parent
        sys.path.append(str(project_root))
        from src.image_generator import ImageGenerator # Assuming original structure is in src/
        # Or better: move the core ImageGenerator class logic into this agent's directory

        # Helper to load YAML (can be shared utility)
        def read_yaml(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            except Exception as e:
                print(f"Error reading YAML {file_path}: {e}") # Use logger in agent
                return None

        @run_agent
        def run(agent: MofaAgent):
            try:
                # 1. Load Config & Secrets
                load_dotenv(dotenv_path=project_root / '.env.secret') # Load secrets
                config_path = project_root / 'configs' / 'image_generator_config.yml'
                config = read_yaml(config_path)
                if not config or 'IMAGE_GENERATOR' not in config:
                    agent.logger.error("Failed to load image_generator_config.yml")
                    raise ValueError("Config not loaded")
                agent_config = config['IMAGE_GENERATOR']

                # --- Kling Config --- (Extract from env vars and agent_config)
                kling_config_dict = {
                    'access_key': os.getenv('KLING_ACCESS_KEY'),
                    'secret_key': os.getenv('KLING_SECRET_KEY'),
                    'api_base_url': os.getenv('KLING_API_BASE_URL', 'https://api.klingai.com'),
                    'timeout': agent_config.get('KLING_TIMEOUT', 60),
                    'max_retries': agent_config.get('KLING_MAX_RETRIES', 3)
                }
                output_dir = project_root / agent_config.get('OUTPUT_DIR', 'workflow/outputs/images')
                output_dir.mkdir(parents=True, exist_ok=True)

                # 2. Initialize Core Logic Component
                # Pass necessary config to your original class
                image_gen_instance = ImageGenerator(kling_config_dict, output_dir)

                # 3. Receive Input from Upstream Agent
                # The key 'keyframe_info_in' must match dataflow.yml input mapping
                keyframe_data_dict = agent.receive_parameter('keyframe_info_in')
                agent.logger.info(f"Received keyframe data for frame ID: {keyframe_data_dict.get('frame_id', 'N/A')}")

                # 4. Execute Core Agent Logic (using async if needed)
                # Your original generate logic likely returns the image path
                # The `run_agent` decorator might manage the event loop for async calls
                # inside this function. If not, you might need explicit asyncio.run or ensure
                # the underlying library calls handle it.
                # Let's assume generate is async:
                image_path = asyncio.run(image_gen_instance.generate(
                    prompt=keyframe_data_dict['prompt'],
                    model_name=agent_config.get('KLING_MODEL_NAME', 'kling-v1-5'),
                    negative_prompt=keyframe_data_dict.get('negative_prompt', ''),
                    aspect_ratio=keyframe_data_dict.get('aspect_ratio', '16:9'),
                    seed=keyframe_data_dict.get('seed'),
                    frame_id=keyframe_data_dict['frame_id'] # Pass frame_id
                ))
                # Note: Using asyncio.run directly inside might be problematic if
                # @run_agent is already managing a loop. Test this carefully.
                # If ImageGenerator.generate isn't async, just call it directly.

                # 5. Prepare and Send Output
                if image_path:
                    result_payload = {
                        "frame_id": keyframe_data_dict['frame_id'],
                        "image_path": str(image_path),
                        # Pass necessary original info downstream
                        "original_prompt": keyframe_data_dict['prompt'],
                        "original_keyframe_data": keyframe_data_dict # Or specific fields
                    }
                    # The key 'image_result_out' must match dataflow.yml output name
                    agent.send_output(
                        agent_output_name='image_result_out',
                        agent_result=result_payload # Must be serializable (dict is fine)
                    )
                    agent.logger.info(f"Sent image result for frame ID: {keyframe_data_dict['frame_id']}")
                else:
                    agent.logger.error(f"Image generation failed for frame ID: {keyframe_data_dict['frame_id']}")
                    # Decide whether to send an error message or just log

            except Exception as e:
                agent.logger.error(f"Error in image-generator agent: {str(e)}", exc_info=True)
                # Optionally send an error output if needed by downstream logic
                # agent.send_output('error_output', {'frame_id': keyframe_data_dict.get('frame_id'), 'error': str(e)})


        def main():
            # Agent name must match the directory name or id in dataflow.yml
            agent = MofaAgent(agent_name='image-generator')
            run(agent=agent)

        if __name__ == "__main__":
            main()
        ```

    *   **`keyframe_parser/agent/main.py`:**
        *   Receives trigger parameters (including keyframes file path).
        *   Parses the keyframes file using your `KeyframeProcessor` logic.
        *   **Crucial Change:** Iterates through the list of parsed `KeyframeData`. Inside the loop, for **each** keyframe:
            *   Convert `KeyframeData` object to a serializable dictionary.
            *   Assign a unique `frame_id` if not present.
            *   Call `agent.send_output('keyframe_data_out', keyframe_dict)`. This will send multiple messages downstream, one per keyframe.
    *   **`video_generator/agent/main.py`:**
        *   Receives `image_result_in` (containing image path, frame_id, original prompt).
        *   Loads its config, including `USE_DIFY`.
        *   Initializes `VideoGenerator` and `DifyEnhancer` (if needed).
        *   Conditionally enhances prompt using Dify logic.
        *   Calls `VideoGenerator.generate_from_image` (handle async).
        *   Sends `video_result_out` containing `frame_id`, `image_path`, `video_path`.
    *   **`music_generator/agent/main.py`:**
        *   Receives trigger parameters (extract `music_prompt`).
        *   If `music_prompt` exists:
            *   Loads config.
            *   Initializes `MusicGenerator`.
            *   Calls `MusicGenerator.generate` (handle async).
            *   Sends `music_result_out` containing `music_path`.
        *   If no `music_prompt`, it simply finishes without sending output.
    *   **`result_logger/agent/main.py`:**
        *   Receives inputs `'video_frame_in'` and `'music_track_in'`. The `@run_agent` will likely call `run` separately for each input received.
        *   Inside `run`, check which input arrived (`agent.receive_parameter('video_frame_in')` vs `agent.receive_parameter('music_track_in')`).
        *   Log the received data. For simple logging, no state needed. If aggregation is desired later, you'd need to store partial results in `self.*` attributes.

5.  **Execution Steps:**
    1.  **Setup:**
        *   Install Rust and `dora-cli`.
        *   Install Python >= 3.10.
        *   Install `uv`: `pip install uv`.
        *   Clone your project (or the new structure).
        *   Install dependencies: `cd /path/to/your/project && uv pip install -r requirements.txt`. Ensure `mofa` framework itself and your libraries (klingdemo, beatoven-ai, etc.) are included.
    2.  **Configure:** Create/Edit `.env.secret` and YAML files in `configs/`.
    3.  **Run DORA Daemon:** `dora up` (in project root or where accessible).
    4.  **Build Dataflow:** `dora build video_gen_dataflow.yml`. This builds the agents specified.
    5.  **Start Dataflow:** `dora start video_gen_dataflow.yml`.
    6.  **Trigger:** Use `terminal-input` (if configured as `start-input`) or another method to send the initial parameters (keyframes path, music prompt). For `terminal-input`, you'd likely need to format the input as a JSON string representing the dictionary of parameters.
        ```bash
        # Example if using terminal-input
        terminal-input
        # Then paste JSON like:
        # {"keyframes_file": "path/to/your/keyframes.txt", "music_prompt": "epic background music", "use_dify": true}
        ```
    7.  **Monitor:** Check `dora logs <agent_id>` and the output from `result-logger`.

**Key MoFA Adaptations:**

*   **Agent Structure:** Using `agents/` directory and `main.py` per agent.
*   **`@run_agent`:** Simplifies the event loop and basic error handling in `main.py`.
*   **`MofaAgent` API:** Using `agent.receive_parameter()`, `agent.send_output()`, `agent.logger`.
*   **Secrets:** Using `.env.secret`.
*   **Build Process:** Using `dora build` which understands the `build:` instructions in the YAML.

This refined plan leverages MoFA's conventions for a potentially simpler and more standardized implementation compared to raw DORA operators. Remember to test the async call handling within the synchronous `run` function carefully.