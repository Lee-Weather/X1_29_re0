"""exp1.9 镜像踝 roll：摆动相实际角 + 期望时序形态 + 三代对照。"""
import numpy as np
import pandas as pd

DATA = '/home/robot/czy/X1_29_re0/czy/data'
WALK = (5.0, 15.0)


def load(exp):
    df = pd.read_csv(f'{DATA}/exp{exp}/isaac_diag.csv')
    m = (df.time_s >= WALK[0]) & (df.time_s <= WALK[1])
    return df[m].reset_index(drop=True)


for exp in ['1.7', '1.8', '1.9']:
    w = load(exp)
    sw_l = ~(w.foot_force_l > 5)
    sw_r = ~(w.foot_force_r > 5)
    dl = w.pos_des_raw_left_ankle_roll_joint
    dr = w.pos_des_raw_right_ankle_roll_joint
    al = w.pos_left_ankle_roll_joint
    ar = w.pos_right_ankle_roll_joint
    print(f'===== exp{exp} =====')
    for tag, des, act, sw in [('左', dl, al, sw_l), ('右', dr, ar, sw_r)]:
        print(f'  {tag}踝 摆动相: 实际 mean {np.degrees(act[sw].mean()):+6.2f}° p95|{np.degrees(act[sw].abs().quantile(0.95)):.1f}° '
              f'max {np.degrees(act[sw]).max():+.1f}° min {np.degrees(act[sw]).min():+.1f}°')
        print(f'  {tag}踝 摆动相: 期望 mean {np.degrees(des[sw].mean()):+6.2f}° max {np.degrees(des[sw]).max():+.1f}° '
              f'min {np.degrees(des[sw]).min():+.1f}°  |期望|>0.34 占比 {(des[sw].abs() > 0.34).mean() * 100:.0f}%')
    # 期望时序形态：与步态相位的相关性（常值偏置 vs 随相位摆动）
    ph = np.arctan2(w.phase_sin, w.phase_cos)  # 步态相位角
    for tag, des in [('左', dl), ('右', dr)]:
        c1 = np.corrcoef(des, np.sin(ph))[0, 1]
        c2 = np.corrcoef(des, np.cos(ph))[0, 1]
        c3 = np.corrcoef(des, w.base_ang_vel_z)[0, 1]
        print(f'  {tag}踝期望: corr(sin ph)={c1:+.2f} corr(cos ph)={c2:+.2f} corr(yaw_rate)={c3:+.2f} '
              f'std {np.degrees(des.std()):.1f}° (std 小=常值偏置)')
    print()

# exp1.9 逐秒期望（支撑相均值）演化 + 同期髋roll/base_roll 代偿
w = load('1.9')
print('===== exp1.9 逐秒（左/右支撑相期望° | 实际° | 髋roll° | base_roll°）=====')
for t0 in range(5, 15):
    m = (w.time_s >= t0) & (w.time_s < t0 + 1)
    sl = m & (w.foot_force_l > 5)
    sr = m & (w.foot_force_r > 5)
    print(f'  t{t0:2d}: L期望 {np.degrees(w.pos_des_raw_left_ankle_roll_joint[sl].mean()):+6.1f}° '
          f'R期望 {np.degrees(w.pos_des_raw_right_ankle_roll_joint[sr].mean()):+6.1f}° | '
          f'L实际 {np.degrees(w.pos_left_ankle_roll_joint[sl].mean()):+5.1f}° '
          f'R实际 {np.degrees(w.pos_right_ankle_roll_joint[sr].mean()):+5.1f}° | '
          f'髋L {np.degrees(w.pos_left_hip_roll_joint[sl].mean()):+5.1f}° '
          f'髋R {np.degrees(w.pos_right_hip_roll_joint[sr].mean()):+5.1f}° | '
          f'base {np.degrees(w.base_euler_x[m].mean()):+5.1f}°')
