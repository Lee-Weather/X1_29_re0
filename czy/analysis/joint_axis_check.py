"""FK 判定 hip_roll / ankle_roll 正角的世界轴向与方向学含义（内翻/外翻），
并用对角验证：FK 下 toe 接触点世界坐标随关节角的变化。"""
import numpy as np
import xml.etree.ElementTree as ET

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


def rot_axis(ax, q):
    c, s = np.cos(q), np.sin(q)
    K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
    return np.eye(3) + s * K + (1 - c) * K @ K


def axis_angle(R):
    ang = np.arccos(np.clip((np.trace(R) - 1) / 2, -1, 1))
    if ang < 1e-9:
        return np.zeros(3), 0.0
    v = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]])
    return v / (2 * np.sin(ang)), ang


def load_joints():
    root = ET.parse(URDF).getroot()
    joints = {}
    for j in root.findall('joint'):
        o = j.find('origin')
        xyz = np.fromstring(o.get('xyz', '0 0 0'), sep=' ') if o is not None else np.zeros(3)
        rpy = np.fromstring(o.get('rpy', '0 0 0'), sep=' ') if o is not None else np.zeros(3)
        ax_el = j.find('axis')
        ax = np.fromstring(ax_el.get('xyz'), sep=' ') if ax_el is not None else None
        joints[j.get('name')] = (xyz, rpy, ax)
    return joints


def fk(joints, side, q_over):
    """q_over: {joint_short: value}; 返回链上每步后的世界变换"""
    T = np.eye(4)
    for jn in _CHAIN:
        xyz, rpy, ax = joints[f'{side}_{jn}_joint']
        To = np.eye(4)
        To[:3, :3] = rpy_to_R(*rpy)
        To[:3, 3] = xyz
        T = T @ To
        q = q_over.get(jn, 0.0)
        if ax is not None and q != 0.0:
            Tj = np.eye(4)
            Tj[:3, :3] = rot_axis(ax, q)
            T = T @ Tj
    return T


def main():
    joints = load_joints()
    for side in ['left', 'right']:
        for jn in ['hip_roll', 'ankle_roll']:
            T0 = fk(joints, side, {})
            T1 = fk(joints, side, {jn: 0.2})
            v, ang = axis_angle(T1[:3, :3] @ T0[:3, :3].T)
            # 该关节后下方一点（脚原点）在 +0.2 下的世界位移
            p0 = T0[:3, 3]
            p1 = T1[:3, 3]
            dp = p1 - p0
            # 链末端 -z 方向(脚向下的近似)在旋转后的变化
            dn = (T1[:3, :3] - T0[:3, :3]) @ np.array([0, 0, -1.0])
            print(f'{side}_{jn} +0.2: 世界轴 {v.round(3)} | 脚位移 {dp.round(4)} | 末端-z 变化 {dn.round(3)}')
        print()


if __name__ == '__main__':
    main()
