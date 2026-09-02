# 云端回放编排：运行时下载 checkpoint → play.py 回放 → 诊断 CSV 打包上传。
#
# 背景：Isaac Gym 镜像中 /personal checkpoint 挂载不可靠，回放任务使用
# trainType=1 + 运行时下载。签名 URL 含 '&'，不能直接拼入平台 startScript，
# 故以 URL-safe Base64 形式传入。
#
# 注意：参数解析为手动扫描（而非 argparse），因为 argparse 的 allow_abbrev
# 会把 --checkpoint 缩写匹配到 --checkpoint_url_b64，导致后者丢失。
#
# 用法（Isaac Gym 镜像内）：
#   python scripts/play_gm.py --task=x1_dh_stand --headless --num_envs=1 \
#       --run_name exp1_4_rerun --load_run exp1_4_ankle_smooth --checkpoint 17996 \
#       --checkpoint_url_b64 <URL_SAFE_BASE64>
#
# 流程：
#   1. 解码 --checkpoint_url_b64 得到签名 URL，下载 checkpoint 到
#      <repo>/logs/<experiment>/exported_data/<load_run>/model_<checkpoint>.pt
#      （与 humanoid.LEGGED_GYM_ROOT_DIR=仓库根 一致）
#   2. 调用 play.py 完成回放（视频 + 诊断 CSV 输出到 <repo>/logs/<experiment>/play_output/）
#   3. 将最新诊断 CSV 打包为 <repo>/logs/<experiment>/gm_play/model_isaac_csv.pt（SDK PT 上传目录）
#   4. 保留 60 秒，等待 SDK 完成扫描与上传

import base64
import glob
import os
import pickle
import subprocess
import sys
import time
import zipfile
from pathlib import Path

# 仓库根（play.py 通过 humanoid.LEGGED_GYM_ROOT_DIR 引用的是这一级，logs 在此之下）
REPO_ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = "x1_dh_stand"
GM_PLAY_DIR = REPO_ROOT / "logs" / EXPERIMENT / "gm_play"


def parse_args(argv):
    """手动扫描 --checkpoint_url_b64，其余参数原样透传给 play.py。"""
    b64 = None
    rest = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--checkpoint_url_b64":
            b64 = argv[i + 1]
            i += 2
        elif arg.startswith("--checkpoint_url_b64="):
            b64 = arg.split("=", 1)[1]
            i += 1
        else:
            rest.append(arg)
            i += 1
    assert b64, "缺少 --checkpoint_url_b64"
    return b64, rest


def extract_kv(rest):
    """从透传参数中提取 --key value / --key=value 对（兼容两种写法混用）。"""
    d = {}
    i = 0
    while i < len(rest):
        a = rest[i]
        if a.startswith("--"):
            if "=" in a:
                k, v = a.split("=", 1)
                d[k] = v
                i += 1
            elif i + 1 < len(rest):
                d[a] = rest[i + 1]
                i += 2
            else:
                i += 1
        else:
            i += 1
    return d


def download_checkpoint(url: str, dest: Path):
    import urllib.request

    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"[play_gm] 下载 checkpoint -> {dest}")
    urllib.request.urlretrieve(url, dest)
    size = dest.stat().st_size
    print(f"[play_gm] 下载完成: {size} bytes")
    assert size > 1_000_000, "checkpoint 过小，下载可能失败"


def package_csv():
    csvs = sorted(glob.glob(str(REPO_ROOT / "logs" / EXPERIMENT / "play_output" / "*isaac_diag.csv")))
    assert csvs, "未找到诊断 CSV"
    latest = csvs[-1]
    print(f"[play_gm] 打包 {os.path.basename(latest)} -> model_isaac_csv.pt")
    data = {"bytes": open(latest, "rb").read()}
    os.makedirs(GM_PLAY_DIR, exist_ok=True)
    out = os.path.join(GM_PLAY_DIR, "model_isaac_csv.pt")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("model_isaac_csv/data.pkl", pickle.dumps(data))
    print(f"[play_gm] 打包完成: {os.path.getsize(out)} bytes")


def main():
    b64, passthrough = parse_args(sys.argv[1:])
    url = base64.urlsafe_b64decode(b64).decode()

    # 从透传参数中提取 load_run / checkpoint，确定下载目标路径
    args_dict = extract_kv(passthrough)
    load_run = args_dict.get("--load_run", "exported_data")
    checkpoint = args_dict.get("--checkpoint", "model_latest")
    dest = REPO_ROOT / "logs" / EXPERIMENT / "exported_data" / load_run / f"model_{checkpoint}.pt"
    download_checkpoint(url, dest)

    script = Path(__file__).resolve().parent / "play.py"
    cmd = [sys.executable, str(script)] + passthrough
    print("[play_gm] 启动回放:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=str(REPO_ROOT))
    if result.returncode != 0:
        # Isaac Gym 在解释器退出销毁 CUDA 上下文时 SEGV 属已知现象；
        # 产物（CSV/视频）已写盘即可继续，由 package_csv 的 assert 兜底校验
        print(f"[play_gm] 警告: play.py 退出码 {result.returncode}，继续检查产物")

    package_csv()
    print("[play_gm] 保留 60s 等待 SDK 扫描上传...")
    time.sleep(60)
    print("[play_gm] done")


if __name__ == "__main__":
    main()
