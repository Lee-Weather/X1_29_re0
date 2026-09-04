"""exp1.9 踝 roll 内翻深度分析（含 exp1.7/1.8 对照）。

符号约定（FK 实证，physically_mirrored URDF）：
  hip_roll:  左/右世界轴均为 -x；左+=内收，右+=外展
  ankle_roll: 左/右世界轴均为 +x；左+=外翻，右+=内翻
世界系脚底横滚（+x 感，脚底法向 +y 偏 = 左脚外翻 / 右脚内翻）：
  foot_roll_L ≈ base_euler_x - hip_roll_L + ankle_roll_L   (<0 为左脚内翻)
  foot_roll_R ≈ base_euler_x - hip_roll_R + ankle_roll_R   (>0 为右脚内翻)
"""
import numpy as np
import pandas as pd

DATA = '/home/robot/czy/X1_29_re0/czy/data'
WALK = (5.0, 15.0)  # 行走段


def load(exp):
    df = pd.read_csv(f'{DATA}/exp{exp}/isaac_diag.csv')
    m = (df.time_s >= WALK[0]) & (df.time_s <= WALK[1])
    return df, df[m].reset_index(drop=True)


def synth(w):
    out = pd.DataFrame()
    out['t'] = w.time_s
    out['stance_l'] = w.foot_force_l > 5
    out['stance_r'] = w.foot_force_r > 5
    out['base_roll'] = w.base_euler_x
    out['hipL'] = w.pos_left_hip_roll_joint
    out['hipR'] = w.pos_right_hip_roll_joint
    out['ankL_des'] = w.pos_des_raw_left_ankle_roll_joint
    out['ankR_des'] = w.pos_des_raw_right_ankle_roll_joint
    out['ankL'] = w.pos_left_ankle_roll_joint
    out['ankR'] = w.pos_right_ankle_roll_joint
    out['yaw'] = w.base_euler_z
    out['wyaw'] = w.base_ang_vel_z
    out['fyawL'] = w.pos_left_hip_yaw_joint
    out['fyawR'] = w.pos_right_hip_yaw_joint
    out['effL'] = w.effort_left_ankle_roll_joint
    out['effR'] = w.effort_right_ankle_roll_joint
    # 世界系脚底横滚（实际 & 期望合成）
    out['frL'] = out.base_roll - out.hipL + out.ankL
    out['frR'] = out.base_roll - out.hipR + out.ankR
    out['frL_des'] = out.base_roll - out.hipL + out.ankL_des
    out['frR_des'] = out.base_roll - out.hipR + out.ankR_des
    # 内翻量（>0 表示视觉内翻，单位 rad）
    out['invL'] = -out.frL
    out['invR'] = +out.frR
    return out


def stats_block(s, name, val, cond=None):
    v = val[cond] if cond is not None else val
    pct5 = lambda th: (v.abs() > np.radians(th)).mean() * 100
    print(f'  {name:24s} mean {np.degrees(v.mean()):+7.2f}°  p95 {np.degrees(v.abs().quantile(0.95)):6.2f}°  '
          f'max|{np.degrees(v.abs().max()):6.2f}°|  >5° {pct5(5):4.1f}%  >10° {pct5(10):4.1f}%')


def intervals(mask, min_len=10):
    idx = np.where(mask)[0]
    if len(idx) == 0:
        return []
    sp = np.where(np.diff(idx) > 1)[0]
    st = np.r_[idx[0], idx[sp + 1]]
    en = np.r_[idx[sp], idx[-1]]
    return [(s, e) for s, e in zip(st, en) if e - s >= min_len]


def main():
    for exp in ['1.7', '1.8', '1.9']:
        _, w = load(exp)
        s = synth(w)
        print(f'===== exp{exp} 行走段 t={WALK[0]}~{WALK[1]}s, {len(s)} 帧 =====')
        yaw0, yaw1 = s.yaw.iloc[0], s.yaw.iloc[-1]
        print(f'  偏航漂移 {np.degrees(yaw1 - yaw0):+.1f}°  | base_roll mean {np.degrees(s.base_roll.mean()):+.2f}°')
        # ---- 世界系内翻统计（分支撑相）----
        print('  [世界系脚底内翻（视觉所见）]')
        stats_block(s, '左脚(左支撑)', s.invL, s.stance_l)
        stats_block(s, '右脚(右支撑)', s.invR, s.stance_r)
        # ---- 各分量贡献（单支撑中段）----
        print('  [分量归因: base_roll / -hip / +ankle 之均值（内翻为正贡献：左=-分量, 右=+分量）]')
        for side, st, hip, ank, ank_des in [('左', s.stance_l, s.hipL, s.ankL, s.ankL_des),
                                            ('右', s.stance_r, s.hipR, s.ankR, s.ankR_des)]:
            c_base = -s.base_roll[st].mean()
            # 左脚内翻贡献: -base_roll, +hipL(-x轴,+q=脚往-y=左脚内翻方向), -ankL
            # 右脚内翻贡献: +base_roll, -hipR(+q=脚往-y=右脚外翻), +ankR
            if side == '左':
                c_base, c_hip, c_ank = -s.base_roll[st].mean(), +hip[st].mean(), -ank[st].mean()
                c_ank_des = -ank_des[st].mean()
            else:
                c_base, c_hip, c_ank = +s.base_roll[st].mean(), -hip[st].mean(), +ank[st].mean()
                c_ank_des = +ank_des[st].mean()
            print(f'    {side}支撑: base {np.degrees(c_base):+6.2f}°  hip {np.degrees(c_hip):+6.2f}°  '
                  f'ankle(实际) {np.degrees(c_ank):+6.2f}°  | 合成 {np.degrees(c_base + c_hip + c_ank):+6.2f}°'
                  f'  ankle(期望) {np.degrees(c_ank_des):+6.2f}°')
        # ---- 逐步分解：支撑期踝期望 vs 偏航增量 ----
        print('  [逐步: 支撑期踝 roll 期望(解剖学: 左-内/右+内) vs 该支撑段偏航增量]')
        for side, st_c, des, fyaw in [('左支撑', s.stance_l, s.ankL_des, s.fyawL),
                                      ('右支撑', s.stance_r, s.ankR_des, s.fyawR)]:
            iv = intervals(st_c.values)
            rows = []
            for a, b in iv:
                des_inv = (-des.iloc[a:b + 1].mean()) if side == '左支撑' else (+des.iloc[a:b + 1].mean())
                rows.append((des_inv, np.degrees(s.yaw.iloc[b] - s.yaw.iloc[a]),
                             np.degrees(fyaw.iloc[a:b + 1].mean())))
            if rows:
                arr = np.array(rows)
                if len(arr) > 2:
                    r1 = np.corrcoef(arr[:, 0], arr[:, 1])[0, 1]
                else:
                    r1 = np.nan
                print(f'    {side} n={len(rows)}: 踝期望内翻均值 {np.degrees(arr[:, 0].mean()):+.1f}°  '
                      f'段内偏航增量 {arr[:, 1].mean():+.2f}°  相关r={r1:+.2f}  髋yaw均值 {arr[:, 2].mean():+.1f}°')
        # ---- 落地瞬间 ----
        print('  [落地瞬间 (force 上升沿) 脚底世界内翻角]')
        for side, force, fr in [('左', s.stance_l, s.invL), ('右', s.stance_r, s.invR)]:
            rise = []
            m = force.values
            for i in range(2, len(m)):
                if m[i] and not m[i - 1] and not m[i - 2]:
                    rise.append(i)
            if rise:
                v = fr.iloc[rise]
                print(f'    {side}脚 n={len(rise)}: 落地内翻 mean {np.degrees(v.mean()):+.1f}°  '
                      f'max {np.degrees(v.max()):+.1f}°')
        # ---- 踝 effort 饱和 ----
        print(f'  [踝 roll 力矩] 左支撑|eff| p95 {s.effL[s.stance_l].abs().quantile(0.95):.1f}  '
              f'右支撑|eff| p95 {s.effR[s.stance_r].abs().quantile(0.95):.1f} Nm')
        print()


if __name__ == '__main__':
    main()
