0.clone代码
```powershell
git clone https://github.com/betasecond/euterpe --recursive
cd euterpe
```

1.uv安装环境
```powershell
uv venv

# windows
 .\.venv\Scripts\activate
# linux
source ./.venv/bin/activate

uv sync
uv pip install -e . 

cd .\lib\BeatovenDemo\
uv pip install -e .
cd ..\KlingDemo\
uv pip install -e .
```
2.进入目录
```powershell
cd ../../workflow

```
3.运行
```powershell
python ../main.py --keyframes-file ./keyframes.txt --model-name kling-v1-5 --env-file ./.env --beatoven-env-file ./.env.beatoven --use-dify --music-prompt "一个优美的钢琴旋律，带有轻微的弦乐伴奏，适合深思和冥想" --music-filename piano_meditation
```