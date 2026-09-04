"""URDF FK 判定踝 roll 正角的方向学含义（内翻/外翻）。
物理镜像模型下，右腿上游链轴翻转使 ankle_roll 的世界轴手性需实证。
方法：其余关节置 0，ankle_roll 分别取 0 / +0.2，FK 求脚底法向变化，
法向偏向身体中线(左脚 -y / 右脚 +y) = 内翻(inversion)。
"""
import numpy as np
import xml.etree.ElementTree as ET
from itertools import count

URDF = '/home/robot/czy/X1_29_re0/resources/robots/x1/urdf/X1_12DOF_physically_mirrored.urdf'
_CHAIN = ['hip_pitch', 'hip_roll', 'hip_yaw', 'knee_pitch', 'ankle_pitch', 'ankle_roll']


def rpy_to_R(r, p, y):
    cr, sr = np.cos(r), np.sin(r)
    cp, sp = np.cos(p), np.sin(p)
    cy, sy = np.cos(y), np.sin(y)
    Rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    Ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    Rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    return Rz @ Ry @ Rx


def axis_angle(R):
    ang = np.arccos(np.clip((np.trace(R) - 1) / 2, -1, 1))
    if ang < 1e-9:
        return np.zeros(3), 0.0
    v = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]])
    return v / (2 * np.sin(ang)), ang


def main():
    root = ET.parse(URDF).getroot()
    joints = {}
    for j in root.findall('joint'):
        name = j.get('name')
        o = j.find('origin')
        xyz = np.fromstring(o.get('xyz', '0 0 0'), sep=' ') if o is not None else np.zeros(3)
        rpy = np.fromstring(o.get('rpy', '0 0 0'), sep=' ') if o is not None else np.zeros(3)
        ax_el = j.find('axis')
        ax = np.fromstring(ax_el.get('xyz'), sep=' ') if ax_el is not None else None
        joints[name] = (xyz, rpy, ax)

    for side in ['left', 'right']:
        T = np.eye(4)
        for k, jn in enumerate(_CHAIN):
            name = f'{side}_{jn}_joint'
            xyz, rpy, ax = joints[name]
            To = np.eye(4)
            To[:3, :3] = rpy_to_R(*rpy)
            To[:3, 3] = xyz
            T = T @ To
            q = 0.2 if jn == 'ankle_roll' else 0.0
            c, s = np.cos(q), np.sin(q)
            K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
            Rj = np.eye(3) + s * K + (1 - c) * K @ K
            Tj = np.eye(4)
            Tj[:3, :3] = Rj
            T = T @ Tj

        # 脚底法向：ankle_roll_link 的 -z（脚底朝下）
        n = T[:3, :3] @ np.array([0, 0, -1.0])

        # 对照：ankle_roll = 0
        T0 = np.eye(4)
        for jn in _CHAIN:
            name = f'{side}_{jn}_joint'
            xyz, rpy, ax = joints[name]
            To = np.eye(4)
            To[:3, :3] = rpy_to_R(*rpy)
            To[:3, 3] = xyz
            T0 = T0 @ To
        n0 = T0[:3, :3] @ np.array([0, 0, -1.0])

        dn = n - n0
        mid_dir = -1 if side == 'left' else +1  # 中线方向：左脚 -y / 右脚 +y
        medial = dn[1] * mid_dir
        v, ang = axis_angle(T[:3, :3] @ T0[:3, :3].T)
        verdict = '内翻 inversion' if medial > 0 else '外翻 eversion'
        print(f'{side}_ankle_roll +0.2 rad:')
        print(f'  世界旋转轴 {v.round(3)} (角 {np.degrees(ang):.1f}°)')
        print(f'  脚底法向变化 dn={dn.round(3)}, 中线分量 {medial:+.3f}')
        print(f'  => {side} + = {verdict}')
        print()


if __name__ == '__main__':
    main()
