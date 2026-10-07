#!/usr/bin/env python3
"""Host simulation of original AI spline path following at Vita frame rates.

Pure math transcribed from the staged original sources (no engine build):

* staging/wwphys/Path.cpp Initialize_Human_Spline / Initialize_Spline
  (cardinal keys timed by cumulative distance, tightness 0.3 or 1.0 for
  tightened action nodes, ASSUMED_FPS = 30, DEF_HUMAN_VELOCITY = 2.5,
  m_LookAheadTime = 8 / approx_frames, m_LookAheadDist = 2.5 * 4 / 30,
  m_MovementRadius = 0.1).
* staging/wwmath/cardinalspline.cpp Update_Tangents and
  hermitespline.cpp Evaluate / curve.cpp Find_Interval.
* staging/wwphys/Path.cpp Evaluate_Next_Point (advance gate, end clamp,
  action-node snap; MOVE_X | MOVE_Y as set by action.cpp Traverse_Path).
* staging/combat/action.cpp Move_To_Absolute / Human_Move_To_Relative /
  Clamped_Units (40 degree bearing gate, deadbeat clamp by
  NormSpeed * MoveSpeed * dt) and Get_Distance_From_Goal.
* staging/combat/soldier.cpp Set_Targeting AI turn limit (TurnRate 360 deg/s,
  0.3x below 20 degrees; heading is applied immediately through
  Phys3Class::Set_Heading, so the move vector is rotated by the same heading
  as phys3.cpp User_Move).
* staging/combat/timemgr.cpp SLOWEST_FPS = 5 (frame clamp 0.2 s).

Collision is not modelled: the trajectory is the AI's commanded motion, and
clearance is measured against the wall points of each scenario.  Vehicles
(VehicleCurveClass / VehicleDriverClass) are analysed analytically in the
report, not simulated here.
"""
import argparse
import json
import math
import sys

ASSUMED_FPS = 30.0
DEF_HUMAN_VELOCITY = 2.5
MOVEMENT_RADIUS = 0.1
TURN_RATE = math.radians(360.0)
SLOWEST_DT = 1.0 / 5.0
BODY_RADIUS = 0.3   # approximate soldier collision radius for clearance


def wrap(a):
    while a > math.pi:
        a -= 2 * math.pi
    while a < -math.pi:
        a += 2 * math.pi
    return a


class Spline:
    """CardinalSpline3DClass -> HermiteSpline3DClass, 2D."""

    def __init__(self, nodes):
        # nodes: list of (x, y, tighten)
        total = 0.0
        last = nodes[0][:2]
        for x, y, _ in nodes:
            total += math.hypot(x - last[0], y - last[1])
            last = (x, y)
        self.total = total
        self.keys = []
        dist = 0.0
        last = nodes[0][:2]
        self.tight = []
        for x, y, tighten in nodes:
            dist += math.hypot(x - last[0], y - last[1])
            self.keys.append((dist / total, (x, y)))
            self.tight.append(1.0 if tighten else 0.3)
            last = (x, y)
        n = len(self.keys)
        tin = [(0.0, 0.0)] * n
        tout = [(0.0, 0.0)] * n
        k = self.keys
        end = n - 1
        f = 1.0 - self.tight[0]
        tout[0] = (f * (k[1][1][0] - k[0][1][0]), f * (k[1][1][1] - k[0][1][1]))
        tin[end] = (f * (k[end][1][0] - k[end - 1][1][0]), f * (k[end][1][1] - k[end - 1][1][1]))
        total_time = (k[1][0] - k[0][0]) + (k[end][0] - k[end - 1][0])
        inf = 2.0 * (k[end][0] - k[end - 1][0]) / total_time
        outf = 2.0 * (k[1][0] - k[0][0]) / total_time
        tin[end] = (tin[end][0] * inf, tin[end][1] * inf)
        tout[0] = (tout[0][0] * outf, tout[0][1] * outf)
        for i in range(1, n - 1):
            f = 1.0 - self.tight[i]
            t = (f * (k[i + 1][1][0] - k[i - 1][1][0]), f * (k[i + 1][1][1] - k[i - 1][1][1]))
            span = k[i + 1][0] - k[i - 1][0]
            a = 2.0 * (k[i][0] - k[i - 1][0]) / span
            b = 2.0 * (k[i + 1][0] - k[i][0]) / span
            tin[i] = (t[0] * a, t[1] * a)
            tout[i] = (t[0] * b, t[1] * b)
        self.tin, self.tout = tin, tout

    def evaluate(self, time):
        k = self.keys
        if time < k[0][0]:
            return k[0][1]
        if time > k[-1][0]:
            return k[-1][1]
        i = 0
        while time > k[i + 1][0]:
            i += 1
        t = (time - k[i][0]) / (k[i + 1][0] - k[i][0])
        t2, t3 = t * t, t * t * t
        h0 = 2 * t3 - 3 * t2 + 1
        h1 = -2 * t3 + 3 * t2
        h2 = t3 - 2 * t2 + t
        h3 = t3 - t2
        p0, p1 = k[i][1], k[i + 1][1]
        return (h0 * p0[0] + h1 * p1[0] + h2 * self.tout[i][0] + h3 * self.tin[i + 1][0],
                h0 * p0[1] + h1 * p1[1] + h2 * self.tout[i][1] + h3 * self.tin[i + 1][1])


class PathFollower:
    """PathClass::Evaluate_Next_Point state for a non-looping human path."""

    def __init__(self, spline, action_indices):
        self.spline = spline
        approx_frames = (spline.total * ASSUMED_FPS) / DEF_HUMAN_VELOCITY
        self.look_time = 8.0 / approx_frames
        self.look_dist = (DEF_HUMAN_VELOCITY * 4.0) / ASSUMED_FPS
        self.time = 0.0
        self.end_time = 1.0
        self.expected = spline.keys[0][1]
        self.state = 'TRAVERSING'
        self.actions = []
        for idx in action_indices:
            node_time = spline.keys[idx][0]
            next_time = spline.keys[idx + 1][0] if idx + 1 < len(spline.keys) else 1.0
            self.actions.append((node_time, next_time))
        self.current_action = -1
        self.visited = []

    def evaluate(self, curr):
        if self.state == 'COMPLETE':
            return self.expected
        dx = self.expected[0] - curr[0]
        dy = self.expected[1] - curr[1]
        delta_len = math.hypot(dx, dy) - MOVEMENT_RADIUS
        self.state = 'TRAVERSING'
        if delta_len < self.look_dist:
            new_time = self.time + self.look_time
            if new_time > (self.end_time - self.look_time * 0.5):
                new_time = self.end_time
            if new_time >= self.end_time:
                self.state = 'COMPLETE'
                self.time = self.end_time
                self.current_action = -1
            else:
                if self.current_action + 1 < len(self.actions):
                    node_time, next_time = self.actions[self.current_action + 1]
                    if abs(node_time - self.time) < self.look_time * 0.5:
                        self.state = 'ACTION_REQUIRED'
                        self.current_action += 1
                        new_time = next_time
                self.time = new_time
            self.expected = self.spline.evaluate(self.time)
            self.visited.append(round(self.time, 9))
        return self.expected


def frame_profile(name, count):
    if name.startswith('fps'):
        fps = float(name[3:])
        return [min(1.0 / fps, SLOWEST_DT)] * count
    if name == 'jitter15':           # alternating 50 / 100 ms frames
        return [0.05 if i % 2 == 0 else 0.1 for i in range(count)]
    raise ValueError(name)


def simulate(scenario, speed, dts, action_mode='pass', record=False):
    """Run one follow.  Returns metrics dict.

    action_mode 'pass': an action node is consumed on the frame it fires (the
    PathAction mechanism is outside this model); the frame position of the
    actor relative to the node is recorded.
    """
    spline = Spline(scenario['nodes'])
    path = PathFollower(spline, scenario.get('actions', []))
    dense = [spline.evaluate(i / 4000.0) for i in range(4001)]
    goal = spline.keys[-1][1]
    arrived_dist = scenario.get('arrived', 0.5)
    pos = list(spline.keys[0][1])
    first = spline.keys[1][1]
    heading = math.atan2(first[1] - pos[1], first[0] - pos[0])
    walls = scenario['walls']
    max_dev = 0.0
    min_clear = min(math.hypot(px - wx, py - wy) for px, py in dense for wx, wy in walls)
    spline_clear = min_clear
    min_clear = float('inf')
    backtracks = 0
    gated_frames = 0
    last_move = None
    action_offsets = []
    elapsed = 0.0
    frames = 0
    trace = []
    done = False
    for dt in dts:
        frames += 1
        elapsed += dt
        target = path.evaluate(tuple(pos))
        if path.state == 'ACTION_REQUIRED':
            ax, ay = spline.keys[scenario['actions'][path.current_action]][1]
            action_offsets.append(math.hypot(pos[0] - ax, pos[1] - ay))
            continue
        rx, ry = target[0] - pos[0], target[1] - pos[1]
        rng = math.hypot(rx, ry)
        done_facing = True
        if rng > 0.1:
            facing = math.atan2(ry, rx)
            dif = wrap(facing - heading)
            if abs(dif) > 0.001:
                max_change = TURN_RATE * dt
                if abs(dif) < math.radians(20):
                    max_change *= 0.3
                change = max(-max_change, min(max_change, dif))
                done_facing = change == dif
                heading = wrap(heading + change)
        gdist = math.hypot(pos[0] - goal[0], pos[1] - goal[1])
        if gdist + rng <= arrived_dist and path.state == 'COMPLETE':
            done = True
            break
        c, s = math.cos(-heading), math.sin(-heading)
        lx, ly = c * rx - s * ry, s * rx + c * ry
        bearing = math.atan2(ly, lx)
        if not (done_facing or abs(bearing) < math.radians(40)):
            gated_frames += 1
            continue
        reach = speed * dt
        mx, my = lx / reach, ly / reach
        mlen = math.hypot(mx, my)
        if mlen > 1.0:
            mx, my = mx / mlen, my / mlen
        c, s = math.cos(heading), math.sin(heading)
        wx = (c * mx - s * my) * speed * dt
        wy = (s * mx + c * my) * speed * dt
        if last_move is not None and math.hypot(wx, wy) > 1e-6:
            if wx * last_move[0] + wy * last_move[1] < 0:
                backtracks += 1
        if math.hypot(wx, wy) > 1e-6:
            last_move = (wx, wy)
        # sample the segment for deviation / clearance (straight-line motion)
        steps = max(1, int(math.hypot(wx, wy) / 0.02))
        for k in range(1, steps + 1):
            px = pos[0] + wx * k / steps
            py = pos[1] + wy * k / steps
            dev = min((px - qx) ** 2 + (py - qy) ** 2 for qx, qy in dense[::4])
            max_dev = max(max_dev, math.sqrt(dev))
            for qx, qy in walls:
                min_clear = min(min_clear, math.hypot(px - qx, py - qy))
        pos[0] += wx
        pos[1] += wy
        if record:
            trace.append((round(elapsed, 4), round(pos[0], 4), round(pos[1], 4)))
        if elapsed > 60.0:
            break
    ideal = spline.total / speed
    return {
        'done': done,
        'frames': frames,
        'time': elapsed,
        'ideal': ideal,
        'slowdown': elapsed / ideal,
        'max_dev': max_dev,
        'min_clear': min_clear - BODY_RADIUS,
        'spline_clear': spline_clear - BODY_RADIUS,
        'backtracks': backtracks,
        'gated': gated_frames,
        'action_offsets': action_offsets,
        'visited': path.visited,
        'step_m': path.look_time * spline.total,
        'trace': trace,
    }


SCENARIOS = {
    # 90 degree corridor corner; corridor 2.0 m wide, inner corner at (5, 1).
    'tight_corner': {
        'nodes': [(0, 0, False), (6, 0, False), (6, 6, False)],
        'walls': [(5.0, 1.0)],
        'arrived': 0.5,
    },
    # S-bend through a 1.2 m doorway in a 0.2 m wall at x = 5.
    'doorway': {
        'nodes': [(0, 0, False), (4.2, 2.0, False), (5.8, 2.0, False), (9, 4, False)],
        'walls': [(4.9, 1.4), (5.1, 1.4), (4.9, 2.6), (5.1, 2.6)],
        'arrived': 0.5,
    },
    # Corridor then 90 degree turn into a lift; tightened mechanism entrance
    # node (action) followed by the inside point, door jambs 1.6 m apart.
    'elevator_approach': {
        'nodes': [(0, 0, False), (8, 0, False), (8, 1.0, True), (8, 3.0, False)],
        'actions': [2],
        'walls': [(7.2, 1.0), (8.8, 1.0)],
        'arrived': 0.5,
    },
}

PROFILES = ['fps60', 'fps30', 'fps15', 'jitter15', 'fps10', 'fps5']
SPEEDS = [3.0, 6.0, 10.0]


def spike_sweep(scenario, speed, base_fps=30.0, spike=0.2):
    """30 fps with a single 200 ms frame inserted at every possible frame."""
    base = simulate(scenario, speed, [1.0 / base_fps] * 4000)
    worst = None
    for at in range(0, base['frames'] + 1):
        dts = [1.0 / base_fps] * 4000
        dts[at] = spike
        r = simulate(scenario, speed, dts)
        r['spike_at'] = at
        r['delay'] = r['time'] - base['time'] - (spike - 1.0 / base_fps)
        if worst is None:
            worst = {'max_dev': r, 'min_clear': r, 'delay': r, 'done': r}
        if r['max_dev'] > worst['max_dev']['max_dev']:
            worst['max_dev'] = r
        if r['min_clear'] < worst['min_clear']['min_clear']:
            worst['min_clear'] = r
        if r['delay'] > worst['delay']['delay']:
            worst['delay'] = r
        if not r['done']:
            worst['done'] = r
    return base, worst


def run_all():
    rows = []
    invariants = []
    for name, scen in SCENARIOS.items():
        for speed in SPEEDS:
            ref = None
            for prof in PROFILES:
                r = simulate(scen, speed, frame_profile(prof, 4000))
                if ref is None:
                    ref = r
                same_seq = r['visited'] == ref['visited']
                invariants.append(same_seq)
                rows.append({
                    'scenario': name, 'speed': speed, 'profile': prof,
                    'done': r['done'], 'frames': r['frames'],
                    'time_s': round(r['time'], 3), 'ideal_s': round(r['ideal'], 3),
                    'slowdown': round(r['slowdown'], 3),
                    'max_dev_m': round(r['max_dev'], 3),
                    'min_clear_m': round(r['min_clear'], 3),
                    'spline_clear_m': round(r['spline_clear'], 3),
                    'backtracks': r['backtracks'], 'gated': r['gated'],
                    'action_offset_m': [round(v, 3) for v in r['action_offsets']],
                    'carrot_seq_identical': same_seq,
                    'carrot_step_m': round(r['step_m'], 4),
                })
    spikes = []
    for name, scen in SCENARIOS.items():
        for speed in SPEEDS:
            base, worst = spike_sweep(scen, speed)
            spikes.append({
                'scenario': name, 'speed': speed,
                'base_max_dev_m': round(base['max_dev'], 3),
                'base_min_clear_m': round(base['min_clear'], 3),
                'worst_max_dev_m': round(worst['max_dev']['max_dev'], 3),
                'worst_min_clear_m': round(worst['min_clear']['min_clear'], 3),
                'worst_extra_delay_s': round(worst['delay']['delay'], 3),
                'all_done': all(w['done'] for w in worst.values()),
            })
    return rows, spikes, all(invariants)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    rows, spikes, invariant = run_all()
    if args.json:
        json.dump({'rows': rows, 'spikes': spikes, 'carrot_sequence_invariant': invariant},
                  sys.stdout, indent=1)
        print()
        return 0
    print('carrot spline-time sequence identical across all profiles:', invariant)
    hdr = ('scenario', 'V', 'profile', 'done', 'frames', 'time', 'ideal', 'slow',
           'maxdev', 'clear', 'splclr', 'back', 'gated', 'action_off')
    print('%-18s %4s %-8s %-5s %6s %6s %6s %5s %6s %6s %6s %4s %5s %s' % hdr)
    for r in rows:
        print('%-18s %4.1f %-8s %-5s %6d %6.2f %6.2f %5.2f %6.3f %6.3f %6.3f %4d %5d %s' % (
            r['scenario'], r['speed'], r['profile'], r['done'], r['frames'], r['time_s'],
            r['ideal_s'], r['slowdown'], r['max_dev_m'], r['min_clear_m'],
            r['spline_clear_m'], r['backtracks'], r['gated'], r['action_offset_m']))
    print()
    print('single 200 ms frame at every frame index of a 30 fps run:')
    for s in spikes:
        print('%-18s V=%4.1f base dev %.3f clear %.3f | worst dev %.3f clear %.3f '
              'extra delay %.3f s all_done %s' % (
                  s['scenario'], s['speed'], s['base_max_dev_m'], s['base_min_clear_m'],
                  s['worst_max_dev_m'], s['worst_min_clear_m'], s['worst_extra_delay_s'],
                  s['all_done']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
