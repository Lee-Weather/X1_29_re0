"""exp1.9 镜像翻补测：摆动相踝 roll 实际/期望、贴限幅边界率、逐代镜像翻期望演化。"""
import numpy as np
import pandas as pd

DATA = '/home/robot/czy/X1_29_re0/czy/data'
WALK = (5.0, 15.0)
CLIP = 0.35


def load(exp):
    df = pd.read_csv(f'{DATA}/exp{exp}/isaac_diag.csv')
    return df[(df.time_s >= WALK[0]) & (df.time_s <= WALK[1])].reset_index(drop=True)


def main():
    print('== 逐代：镜像翻期望(支撑相均值, 外滚为正: 左+右-) / 摆动相实际 ==')
    for exp in ['1.7', '1.8', '1.9']:
        w = load(exp)
        sl, sr = w.foot_force_l > 5, w.foot_force_r > 5
        dL, dR = w.pos_des_raw_left_ankle_roll_joint, w.pos_des_raw_right_ankle_roll_joint
        aL, aR = w.pos_left_ankle_roll_joint, w.pos_right_ankle_roll_joint
        # 镜像外滚量: 左取+, 右取-
        ev_st_L, ev_st_R = dL[sl].mean(), -dR[sr].mean()
        ev_sw_L, ev_sw_R = aL[~sl].mean(), -aR[~sr].mean()
        print(f'exp{exp} 支撑期望外滚: 左 {np.degrees(ev_st_L):+6.1f}°  右 {np.degrees(ev_st_R):+6.1f}°   '
              f'摆动实际外滚: 左 {np.degrees(ev_sw_L):+6.1f}°  右 {np.degrees(ev_sw_R):+6.1f}°')
    print()

    w = load('1.9')
    sl, sr = w.foot_force_l > 5, w.foot_force_r > 5
    for side, sw, des, act in [('左', ~sl, w.pos_des_raw_left_ankle_roll_joint, w.pos_left_ankle_roll_joint),
                               ('右', ~sr, w.pos_des_raw_right_ankle_roll_joint, w.pos_right_ankle_roll_joint)]:
        d, a = des[sw], act[sw]
        at_clip = (np.abs(np.abs(d) - CLIP) < 0.01).mean() * 100
        beyond = (np.abs(d) > CLIP + 0.01).mean() * 100
        # 期望符号分布
        print(f'exp1.9 摆动相 {side}踝: 实际 mean {np.degrees(a.mean()):+6.1f}°  p95|{np.degrees(a.abs().quantile(0.95)):5.1f}°  '
              f'max|{np.degrees(a.abs().max()):5.1f}° | 期望 p95|{np.degrees(d.abs().quantile(0.95)):5.1f}°  '
              f'贴限幅边 {at_clip:.0f}%  超限幅 {beyond:.0f}%')
    print()

    # 期望值超出 URDF 关节限位(±0.64)的帧占比（支撑相不 clip 的后果）
    sl, sr = w.foot_force_l > 5, w.foot_force_r > 5
    for side, st, des in [('左', sl, w.pos_des_raw_left_ankle_roll_joint),
                          ('右', sr, w.pos_des_raw_right_ankle_roll_joint)]:
        over = (des[st].abs() > 0.64).mean() * 100
        print(f'exp1.9 支撑相 {side}踝期望超 URDF 限位 ±0.64: {over:.1f}% 帧  (max {des[st].abs().max():.3f} rad)')


if __name__ == '__main__':
    main()
