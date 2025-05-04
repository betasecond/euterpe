1.uv安装环境
```powershell
uv pip install -e . 

```
2.进入目录
```powershell
cd ./workflow

```
3.运行
```powershell
python workflow.py --keyframes-file ./keyframes.txt --model-name kling-v1-5 --env-file ./.env --beatoven-env-file ./.env.beatoven --use-dify --music-prompt "一个优美的钢琴旋律，带有轻微的弦乐伴奏，适合深思和冥想" --music-filename piano_meditation
```