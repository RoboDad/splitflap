"""
flap_tester — controlled-sequence tester for splitflap modules.

Commands flaps by INDEX over the serial proto protocol, so it can exercise
the full 62-flap PVV set including the lowercase custom/color codes that the
web app's text input uppercases away.

Modes:
  tour     Step through every flap one position at a time (slow tour).
  seq      Step through an explicit character sequence (case-sensitive).
  jumps    Random multi-flap jumps (stress test for dynamic step loss).
  spin     Repeated forced full revolutions of a single flap (home-drift
           measurement; pairs with the chainlink_pvv62_diag firmware build,
           which logs "DIAG: ... home blip at raw step N" lines).
  monitor  Just connect and print state changes + firmware logs.

Any change to the module's missed/unexpected home counters is reported
immediately, tagged with the move during which it happened.

Examples (run from the repo root, venv active):
  python -m pvv_tools.flap_tester tour --port COM5 --dwell 1.5 --confirm
  python -m pvv_tools.flap_tester seq --port COM5 --chars "$hjnsbkedct'"
  python -m pvv_tools.flap_tester jumps --port COM5 --count 40 --seed 1
  python -m pvv_tools.flap_tester spin --port COM5 --revs 10
"""
import argparse
import logging
import random
import re
import sys
import threading
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / 'software' / 'chainlink'))

from splitflap_proto import (  # noqa: E402
    ask_for_serial_port,
    splitflap_context,
)
from proto_gen import splitflap_pb2  # noqa: E402

STATE_NORMAL = splitflap_pb2.SplitflapState.ModuleState.State.NORMAL
LEGACY_ALPHABET_LEN = 40

DIAG_RE = re.compile(r'DIAG: m(\d+) home blip at raw step (\d+)')
STEPS_PER_REVOLUTION = 2048


class DiagCollector:
    """Collects home-blip arrival steps from the diag firmware's DIAG log
    lines, tagged with the current test phase, so per-revolution loss can be
    computed and attributed."""

    def __init__(self, splitflap, module_index):
        self._m = module_index
        self._lock = threading.Lock()
        self.samples = []  # list of (tag, signed_error_steps)
        self.tag = None
        splitflap.add_handler('log', self._on_log)

    def _on_log(self, msg):
        match = DIAG_RE.search(msg.msg)
        if match and int(match.group(1)) == self._m:
            step = int(match.group(2))
            err = step - STEPS_PER_REVOLUTION if step >= STEPS_PER_REVOLUTION // 2 else step
            with self._lock:
                self.samples.append((self.tag, err))

    def set_tag(self, tag):
        with self._lock:
            self.tag = tag

    def deltas_for(self, tag):
        """Per-revolution loss: differences between consecutive same-tag
        samples. A delta outside [-6, 60] means a re-home resynced the
        reference in between; those are discarded (counted separately)."""
        with self._lock:
            samples = list(self.samples)
        deltas, discarded = [], 0
        prev = None
        for sample_tag, err in samples:
            if sample_tag != tag:
                prev = None
                continue
            if prev is not None:
                delta = err - prev
                if -6 <= delta <= 60:
                    deltas.append(delta)
                else:
                    discarded += 1
            prev = err
        return deltas, discarded


class ModuleWatch:
    """Tracks one module's reported state and home-error counters."""

    def __init__(self, splitflap, module_index):
        self._s = splitflap
        self._m = module_index
        self._lock = threading.Lock()
        self._latest = None
        self.move_label = 'startup'
        self.counter_events = []  # (move_label, counter_name, new_value)
        splitflap.add_handler('splitflap_state', self._on_state)

    def _on_state(self, msg):
        if self._m >= len(msg.modules):
            return
        mod = msg.modules[self._m]
        with self._lock:
            prev = self._latest
            self._latest = mod
            label = self.move_label
        if prev is not None:
            for name in ('count_missed_home', 'count_unexpected_home'):
                new = getattr(mod, name)
                if new != getattr(prev, name):
                    self.counter_events.append((label, name, new))
                    print(f'  *** {name} -> {new} (during: {label})')

    def snapshot(self):
        with self._lock:
            return self._latest

    def set_label(self, label):
        with self._lock:
            self.move_label = label

    def go_to(self, index, force=False):
        positions = [None] * self._m + [index]
        force_list = ([False] * self._m + [True]) if force else None
        self._s.set_positions(positions, force_list)

    def wait_settle(self, target_index, timeout=60.0, require_motion=False):
        """Wait until the module reports NORMAL, not moving, at target_index.

        require_motion: wait to observe movement first — needed for forced
        full revolutions, where the target index equals the start index.
        """
        deadline = time.time() + timeout
        last_request = 0.0
        seen_motion = False
        while time.time() < deadline:
            if time.time() - last_request > 0.5:
                self._s.request_state()
                last_request = time.time()
            st = self.snapshot()
            if st is not None:
                if st.moving or st.state != STATE_NORMAL:
                    seen_motion = True
                elif st.flap_index == target_index and (seen_motion or not require_motion):
                    return st
            time.sleep(0.05)
        return None


def wait_for_alphabet(splitflap, timeout=8.0):
    """The firmware broadcasts its flap character set every ~2s; wait for it
    so we aren't stuck with the legacy 40-char fallback."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        alphabet = splitflap.get_alphabet()
        if len(alphabet) != LEGACY_ALPHABET_LEN:
            return alphabet
        time.sleep(0.2)
    logging.warning('Flap character set not received from firmware; '
                    'falling back to the legacy 40-char set')
    return splitflap.get_alphabet()


def describe(alphabet, index):
    return f'{index:2d} {alphabet[index]!r}'


def run_step(watch, alphabet, index, dwell, confirm, mismatches, force=False):
    label = f'move to {describe(alphabet, index)}'
    watch.set_label(label)
    watch.go_to(index, force=force)
    st = watch.wait_settle(index, require_motion=force)
    if st is None:
        print(f'  !!! TIMEOUT waiting to settle at {describe(alphabet, index)}')
        mismatches.append((index, alphabet[index], '<timeout>'))
        return
    print(f'  commanded {describe(alphabet, index)}  reported {describe(alphabet, st.flap_index)}'
          f'  missed={st.count_missed_home} unexpected={st.count_unexpected_home}')
    if dwell > 0:
        time.sleep(dwell)
    if confirm:
        answer = input('      [Enter]=shown correctly, or type the char actually shown: ').strip()
        if answer:
            mismatches.append((index, alphabet[index], answer))
            print(f'      recorded mismatch: expected {alphabet[index]!r} saw {answer!r}')


def run_sector_phase(watch, collector, alphabet, tag, slow_start, slow_end,
                     cycles, step_dwell):
    """One phase of the sector-isolation test: each cycle single-steps
    through [slow_start..slow_end] (drum never leaves the low-speed part of
    the acceleration ramp), then makes one long cruise move back to
    slow_start through the rest of the revolution. Net travel per cycle is
    exactly one revolution, so consecutive DIAG blips give loss-per-rev for
    a revolution in which ONLY the slow sector was crossed slowly."""
    span = f'{slow_start}..{slow_end} ({alphabet[slow_start]!r}..{alphabet[slow_end]!r})'
    print(f'--- Phase {tag}: single-stepping {span}, cruising the rest, {cycles} cycles ---')
    watch.set_label(f'{tag}: position at {slow_start}')
    watch.go_to(slow_start)
    if watch.wait_settle(slow_start) is None:
        print('  !!! TIMEOUT positioning at sector start')
        return
    collector.set_tag(tag)
    for cycle in range(cycles):
        for index in range(slow_start + 1, slow_end + 1):
            watch.set_label(f'{tag} cycle {cycle + 1}: slow step to {index}')
            watch.go_to(index)
            if watch.wait_settle(index) is None:
                print(f'  !!! TIMEOUT at slow step {describe(alphabet, index)}')
            time.sleep(step_dwell)
        watch.set_label(f'{tag} cycle {cycle + 1}: cruise back to {slow_start}')
        watch.go_to(slow_start)
        if watch.wait_settle(slow_start) is None:
            print('  !!! TIMEOUT on cruise move')
        print(f'  cycle {cycle + 1}/{cycles} done')
    collector.set_tag(None)


def summarize_sector(collector, suspect_span, control_span):
    print()
    print('=== Sector isolation summary (loss per revolution, steps) ===')
    results = {}
    for tag, span in (('SUSPECT-SLOW', suspect_span), ('CONTROL-SLOW', control_span)):
        deltas, discarded = collector.deltas_for(tag)
        mean = sum(deltas) / len(deltas) if deltas else float('nan')
        results[tag] = mean
        print(f'  {tag:13s} (slow {span}): deltas={deltas} mean={mean:.1f} '
              f'(n={len(deltas)}, resyncs discarded={discarded})')
    print()
    a, b = results.get('SUSPECT-SLOW'), results.get('CONTROL-SLOW')
    if a != a or b != b:  # NaN check
        print('  Not enough DIAG samples — is the chainlink_pvv62_diag firmware flashed?')
        return
    print('  Interpretation:')
    print('   - SUSPECT-SLOW measures loss with the suspect sector crossed SLOWLY')
    print('     (everything else at cruise). CONTROL-SLOW crosses the suspect')
    print('     sector at CRUISE instead.')
    if b - a >= 4 and a <= 4:
        print(f'   -> Loss concentrated in the suspect sector at speed '
              f'({a:.1f} vs {b:.1f} steps/rev): the sector IS the culprit.')
    elif abs(b - a) < 3:
        print(f'   -> No significant difference ({a:.1f} vs {b:.1f} steps/rev): '
              f'loss is NOT specific to the suspect sector.')
    else:
        print(f'   -> Partial difference ({a:.1f} vs {b:.1f} steps/rev): the '
              f'sector contributes but is not the whole story.')
    print('  (Thermal caveat: phases run in sequence; for a careful result,')
    print('   re-run with --control-first and check the conclusion holds.)')


def summarize(watch, alphabet, mismatches, moves):
    print()
    print(f'=== Summary: {moves} moves ===')
    if mismatches:
        print('Operator-observed mismatches:')
        for index, expected, seen in mismatches:
            print(f'  idx {index:2d}: expected {expected!r}, saw {seen!r}')
    else:
        print('No operator-observed mismatches recorded.')
    if watch.counter_events:
        print('Home-counter changes:')
        for label, name, value in watch.counter_events:
            print(f'  {name} -> {value}  ({label})')
    else:
        print('No missed/unexpected home counter changes.')


def add_common_args(p, suppress_defaults=False):
    """Common options, attached to the main parser AND each subcommand so
    they are accepted both before and after the mode name. Subcommand copies
    use SUPPRESS defaults so an unset option never clobbers a value parsed
    from the main parser."""
    sup = argparse.SUPPRESS
    p.add_argument('--port', '-p', default=(sup if suppress_defaults else None),
                   help='Serial port (e.g. COM5); interactive picker if omitted')
    p.add_argument('--module', '-m', type=int, default=(sup if suppress_defaults else 0),
                   help='Module index to test (default 0)')
    p.add_argument('--verbose', '-v', action='store_true',
                   default=(sup if suppress_defaults else False),
                   help='Verbose protocol logging')


def main():
    parser = argparse.ArgumentParser(description='Controlled-sequence splitflap module tester')
    add_common_args(parser)
    sub = parser.add_subparsers(dest='mode', required=True)

    p_tour = sub.add_parser('tour', help='Step through every flap one position at a time')
    p_tour.add_argument('--start', type=int, default=0, help='Start index (default 0)')
    p_tour.add_argument('--loops', type=int, default=1, help='Number of full passes (default 1)')
    p_tour.add_argument('--dwell', type=float, default=1.5, help='Seconds to pause on each flap (default 1.5)')
    p_tour.add_argument('--confirm', action='store_true',
                        help='Prompt after each flap to record what is physically shown')

    p_seq = sub.add_parser('seq', help='Step through an explicit character sequence (case-sensitive)')
    p_seq.add_argument('--chars', required=True,
                       help="Characters to show in order, e.g. \"NOPQ\" or \"$hjnsbkedct\"")
    p_seq.add_argument('--dwell', type=float, default=1.5)
    p_seq.add_argument('--confirm', action='store_true')

    p_jumps = sub.add_parser('jumps', help='Random multi-flap jumps (dynamic stress test)')
    p_jumps.add_argument('--count', type=int, default=30, help='Number of jumps (default 30)')
    p_jumps.add_argument('--seed', type=int, default=None, help='Random seed for a repeatable sequence')
    p_jumps.add_argument('--dwell', type=float, default=1.0)
    p_jumps.add_argument('--confirm', action='store_true')

    p_spin = sub.add_parser('spin', help='Forced full revolutions (home-drift measurement)')
    p_spin.add_argument('--revs', type=int, default=10, help='Number of revolutions (default 10)')
    p_spin.add_argument('--flap', type=int, default=0, help='Flap index to return to each rev (default 0)')

    p_sector = sub.add_parser(
        'sector',
        help='A/B test: is per-rev step loss concentrated in one flap sector? '
             '(requires chainlink_pvv62_diag firmware)')
    p_sector.add_argument('--suspect-start', type=int, default=42,
                          help='Suspect sector first index (default 42 = $, start of customs)')
    p_sector.add_argument('--suspect-end', type=int, default=53,
                          help="Suspect sector last index (default 53 = ', end of customs)")
    p_sector.add_argument('--control-start', type=int, default=10,
                          help='Control sector first index (default 10 = J)')
    p_sector.add_argument('--control-end', type=int, default=21,
                          help='Control sector last index (default 21 = U)')
    p_sector.add_argument('--cycles', type=int, default=8,
                          help='Revolutions per phase (default 8)')
    p_sector.add_argument('--step-dwell', type=float, default=0.15,
                          help='Pause between slow single-flap steps (default 0.15s)')
    p_sector.add_argument('--control-first', action='store_true',
                          help='Run the control phase before the suspect phase (thermal check)')

    sub.add_parser('monitor', help='Connect and print state changes + firmware logs')

    for p in (p_tour, p_seq, p_jumps, p_spin, p_sector, sub.choices['monitor']):
        add_common_args(p, suppress_defaults=True)

    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s')

    port = args.port or ask_for_serial_port()

    with splitflap_context(port) as s:
        alphabet = wait_for_alphabet(s)
        num_flaps = len(alphabet)
        print(f'Connected. {s.get_num_modules()} modules, {num_flaps} flaps: {"".join(alphabet)!r}')
        watch = ModuleWatch(s, args.module)
        s.request_state()

        mismatches = []
        moves = 0
        try:
            if args.mode == 'tour':
                for loop in range(args.loops):
                    start = args.start if loop == 0 else 0
                    print(f'--- Tour pass {loop + 1}/{args.loops} ---')
                    for index in range(start, num_flaps):
                        run_step(watch, alphabet, index, args.dwell, args.confirm, mismatches)
                        moves += 1

            elif args.mode == 'seq':
                indexes = []
                for c in args.chars:
                    if c not in alphabet:
                        parser.error(f'Character {c!r} is not in the flap set {"".join(alphabet)!r}')
                    indexes.append(alphabet.index(c))
                for index in indexes:
                    run_step(watch, alphabet, index, args.dwell, args.confirm, mismatches)
                    moves += 1

            elif args.mode == 'jumps':
                rng = random.Random(args.seed)
                current = None
                for _ in range(args.count):
                    index = rng.randrange(num_flaps)
                    while index == current:
                        index = rng.randrange(num_flaps)
                    run_step(watch, alphabet, index, args.dwell, args.confirm, mismatches)
                    current = index
                    moves += 1

            elif args.mode == 'sector':
                if not (0 <= args.suspect_start < args.suspect_end < num_flaps
                        and 0 <= args.control_start < args.control_end < num_flaps):
                    parser.error('sector bounds must satisfy 0 <= start < end < num_flaps')
                collector = DiagCollector(s, args.module)
                suspect_span = (f'{args.suspect_start}..{args.suspect_end} '
                                f'({alphabet[args.suspect_start]!r}..{alphabet[args.suspect_end]!r})')
                control_span = (f'{args.control_start}..{args.control_end} '
                                f'({alphabet[args.control_start]!r}..{alphabet[args.control_end]!r})')
                phases = [
                    ('SUSPECT-SLOW', args.suspect_start, args.suspect_end),
                    ('CONTROL-SLOW', args.control_start, args.control_end),
                ]
                if args.control_first:
                    phases.reverse()
                for tag, start, end in phases:
                    run_sector_phase(watch, collector, alphabet, tag, start, end,
                                     args.cycles, args.step_dwell)
                summarize_sector(collector, suspect_span, control_span)

            elif args.mode == 'spin':
                run_step(watch, alphabet, args.flap, 0.5, False, mismatches)
                for rev in range(args.revs):
                    print(f'--- Revolution {rev + 1}/{args.revs} ---')
                    run_step(watch, alphabet, args.flap, 0.5, False, mismatches, force=True)
                    moves += 1

            elif args.mode == 'monitor':
                print('Monitoring (Ctrl+C to stop)...')
                last = None
                while True:
                    s.request_state()
                    st = watch.snapshot()
                    if st is not None:
                        key = (st.state, st.flap_index, st.moving,
                               st.count_missed_home, st.count_unexpected_home)
                        if key != last:
                            last = key
                            flap = alphabet[st.flap_index] if st.flap_index < num_flaps else '?'
                            print(f'  state={st.state} flap={st.flap_index}({flap!r}) moving={st.moving}'
                                  f' missed={st.count_missed_home} unexpected={st.count_unexpected_home}')
                    time.sleep(0.25)

        except KeyboardInterrupt:
            print('\nInterrupted.')

        if args.mode != 'monitor':
            summarize(watch, alphabet, mismatches, moves)


if __name__ == '__main__':
    main()
