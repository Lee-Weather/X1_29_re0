# 实验记录

## 实验索引

| 编号 | 日期 | 摘要 | 状态 | Task ID | GM账号 | checkpoint |
| --- | --- | --- | --- | --- | --- | --- |
| exp0 | 2026-08-28 | 基线：切换 physically_mirrored URDF + 右踝 pitch 符号修复后本机从零训练 6000 轮；回放全程稳定行走、起停正常，速度跟踪 71% 未达标 | ⚠️部分达标（已测试） | 本机训练（RTX A6000） | 无（本机训练） | model_6000.pt |

---

## 实验 exp0：physically_mirrored URDF 切换 + 右踝符号修复基线

### 1. 上一实验结果与教训

> 本轮为 exp 系列首个实验（基线），无上一轮数据。
> 背景：检查发现 `X1DHStandCfg.asset.file` 指向不存在的 `x1.urdf`，仓库实际提供 `X1_12DOF.urdf`（旧约定）与 `X1_12DOF_physically_mirrored.urdf`（新约定）两个 URDF；后者右踝 pitch 轴已翻转（`0 0 1` → `0 0 -1`），与 skill post-201-5 记录的"dof10 符号约定反转"一致。
>
> **本轮要解决的具体问题**：
> - 修复资源引用缺失，统一训练/回放/sim2sim 的 URDF 约定
> - 验证右踝 pitch 符号修复后策略能否正常学得稳定行走

### 2. 本轮修改目标

- 目标1：修复 URDF 引用缺失，切换到 `X1_12DOF_physically_mirrored.urdf`
- 目标2：右踝 pitch 符号取反适配新 URDF 轴约定，保证默认位姿与参考步态左右物理对称
- 目标3：本机（非远程服务器）完成从零训练并回放验收
- 验收标准：全程不摔倒、起停正常；前进 0.6 m/s 跟踪 ≥ 80%；Mean reward ≥ 120，Mean episode length ≥ 2100

### 3. 修改内容

### 修改一：URDF 资源路径修复

| 参数 | 旧值 | 新值 | 说明 |
| --- | --- | --- | --- |
| `asset.file` | `.../x1/urdf/x1.urdf`（不存在） | `.../x1/urdf/X1_12DOF_physically_mirrored.urdf` | 新 URDF 引用 `../../meshes/`，已建软链接 `resources/robots/meshes` → `Models-meshes/SSOT/Models/meshes` |

**理由**：旧路径文件不存在，训练无法加载资源；新旧 URDF 全量数值对比确认唯一功能差异为右踝 pitch 轴翻转（FK 验证世界轴点积 +0.998 → -0.998）。

### 修改二：右踝 pitch 符号取反（核心）

| 参数 | 旧值 | 新值 | 说明 |
| --- | --- | --- | --- |
| `default_joint_angles['right_ankle_pitch_joint']` | -0.21 | **+0.21** | 保持物理位姿不变（FK 验证：不改则右踝物理旋转误差 24.06°） |
| `final_swing_joint_delta_pos[10]` | -0.16 | **+0.16** | 保持右踝摆动参考与左踝物理方向对称 |

**理由**：轴翻转后 `q_new = -q_old` 才是同一物理角；参考步态（`compute_ref_state`）依赖左右对称的物理摆动方向。

### 修改三：训练轮数

| 参数 | 旧值 | 新值 | 说明 |
| --- | --- | --- | --- |
| `max_iterations` | 20000 | 6000 | 本机单卡训练时长控制（实测 ~4.5 h） |

### 4. 修改文件

- `humanoid/envs/x1/x1_dh_stand_config.py`：修改一、二、三
- `resources/robots/meshes`：新增软链接（mesh 路径解析）
- `humanoid/envs/base/base_task.py`：新增 `enable_headless_render` 支持（headless 相机离屏录制，仅影响回放）
- `humanoid/scripts/play.py`：速度阶梯 0→0.6→0、诊断 CSV 输出、视频叠加 y/z 速度（回放工具，不影响训练）

### 5. 训练参数

| 参数 | 值 |
| --- | --- |
| 训练方式 | 从零 |
| GM账号 | 无（本机训练） |
| max_iterations | 6000 |
| save_interval | 100 |
| num_envs | 4096 |
| seed | 5 |
| learning_rate | 1e-5（fixed） |
| 算力 | NVIDIA RTX A6000 51GB，本机 ThinkStation P720 |
| 镜像 | 无（conda env F1：python3.8 / torch 1.12.1+cu113 / isaacgym preview4） |
| 代码仓库 | 本地 `/home/robot/czy/X1_29_re0`（pip install -e .） |
| 启动命令 | `python humanoid/scripts/train.py --task=x1_dh_stand --run_name=ankle_mirror_6000 --headless` |

### 6. 预期与验收

**目标指标**（训练日志，6000 轮）：

| 指标 | 上一轮 | 本轮目标 | 异常信号 |
| --- | --- | --- | --- |
| Mean reward | —（首个） | ≥ 120 | < 80 |
| Mean episode length | —（首个） | ≥ 2100 | < 1500 |
| 回放前进跟踪（0.6 m/s） | —（首个） | ≥ 80% | < 60% |
| 回放全程 | —（首个） | 不摔倒、起停正常 | 中途摔倒 |

### 7. 实验结果

> 训练任务：本机后台训练，2026-08-28 11:17 ~ 15:5x（约 4.5 h），run 目录 `2026-08-28_11-17-24ankle_mirror_6000`
> 最终 checkpoint：`model_6000.pt`（9.9 MB，已归档 `czy/data/exp0/`）

#### 最终结果（iter 5999 / 回放 model_6000）

| 指标 | 目标 | 实测 | 判定 |
| --- | --- | --- | --- |
| Mean reward | ≥ 120 | 147.8 | ✅ |
| Mean episode length | ≥ 2100 | 2210（上限 2400） | ✅ |
| 全程不摔倒/起停正常 | 是 | 全程最低高度 0.590 m，起停干净 | ✅ |
| 前进 0.6 m/s 跟踪 | ≥ 80% | 稳态 0.426 m/s（**71%**） | ❌ |

#### 训练趋势

| iter | Mean reward | Mean episode length |
| --- | --- | --- |
| 99 | 14.2 | 465 |
| 600 | 48.1 | 1268 |
| 1200 | 78.0 | 1844 |
| 2400 | 114.6 | 2233 |
| 3600 | 132.8 | 2244 |
| 4800 | 147.8 | 2242 |
| 5400 | 146.5 | 2179 |
| 5999 | 147.8 | 2210 |

#### 各奖励项最终值

| 奖励项 | 权重 | 最终值 | 说明 |
| --- | --- | --- | --- |
| tracking_lin_vel | 1.8 | 1.030 | 速度跟踪良好 |
| feet_contact_number | 2.0 | 1.628 | 步态接触时序符合参考 |
| ref_joint_pos | 2.2 | 1.162 | 参考关节跟踪良好 |

#### 回放分段数据（速度阶梯 0→0.6→0，各 10s，`isaac_diag.csv`）

| 阶段 | 实际 vx | \|vy\| | \|vz\| | 身体高度 | 偏航漂移 |
| --- | --- | --- | --- | --- | --- |
| 站立 10s | +0.002 m/s | 0.008 | 0.021 | 0.612±0.009 m | +1.0° |
| 前进 0.6 m/s | +0.396 m/s（稳态 0.426，71%） | 0.146 | 0.108 | 0.612±0.007 m | +5.7° |
| 减速 10s | +0.026 m/s | 0.018 | 0.011 | 0.610±0.002 m | -1.3° |

**结论**：⚠️ 部分达标——右踝符号修复后策略成功学得稳定行走（不摔倒、站立精准、起停干净、偏航漂移 < 6°），但前进速度跟踪 71% 未达 80% 目标；对比中途 model_4800 回放（稳态 0.446 m/s，74%），4800→6000 轮速度跟踪未继续提升，疑似 reward 已在该配置下进入平台期。

**根因分析**（速度跟踪未达标）：

- Mean reward 于 ~4800 轮进入平台期（143~150 震荡），继续训练无增益
- 训练指令范围 `lin_vel_x ∈ [-0.4, 1.2]` 均匀采样，0.6 m/s 处样本密度有限；且 `tracking_lin_vel` 用 exp(-error²·5)，0.17 m/s 误差时该项仍有 0.87，梯度不足以逼平误差
- 侧向速度 |vy|≈0.14 偏大，说明部分推进分量耗散在横向，与步宽/髋 roll 控制相关
- 本轮 armature 仍为旧配置（统一 [0.0001, 0.05]），真机辨识的对齐值（膝 0.25 等）尚未参与训练

**下一轮方向**：

- exp0.1（微调）：加载 model_6000 续训，收紧 `commands.ranges.lin_vel_x` 上限至 0.6 或提高 `tracking_sigma`/`tracking_lin_vel` 权重，强化速度精度
- 引入真机辨识的 armature 逐关节配置（已改好 config，本实验未包含），预期改善动力学保真与速度响应
- 观察侧向速度：如仍 ~0.14，考虑提高 `feet_distance`/`orientation` 权重
