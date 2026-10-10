"""Offline passive-update routing tests; no WinMM endpoint or device is opened."""
import ctypes
from itertools import product
import unittest
from unittest.mock import patch

import update_mode as mode


def pair(name):
    return [{'direction': direction, 'name': name} for direction in ('in', 'out')]


class ClassificationTests(unittest.TestCase):
    def classify(self, serial=None, disks=None, midi=None, error=None):
        result = mode.classify_update_mode(serial or [], disks or [], midi or [], error)
        self.assertEqual(set(result), {'mode', 'app_entry_method', 'official_available', 'reason'})
        self.assertIs(type(result['official_available']), bool)
        self.assertTrue(result['reason'])
        return result

    def test_exact_stock_names_and_ota_pair_select_only_vendor_handoff(self):
        for incoming, outgoing in product(('FM-1', 'FM-1 Midi'), repeat=2):
            with self.subTest(incoming=incoming, outgoing=outgoing):
                result = self.classify(midi=[{'direction': 'in', 'name': incoming},
                                           {'direction': 'out', 'name': outgoing}])
                self.assertEqual(result['mode'], 'sysex')
                self.assertTrue(result['official_available'])
                self.assertIsNone(result['app_entry_method'])
        result = self.classify(midi=pair('ota-FM-1'))
        self.assertEqual(result['mode'], 'ota_sysex')
        self.assertTrue(result['official_available'])
        self.assertIsNone(result['app_entry_method'])

    def test_one_cdc_or_uboot_candidate_selects_only_protected_app_route(self):
        for fields, expected, entry in (({'serial': [{'port': 'COM_fixture'}]}, 'serial', 'serial'),
                                      ({'disks': [{'DeviceID': 'fixture'}]}, 'uboot', 'already_uboot')):
            with self.subTest(mode=expected):
                result = self.classify(**fields)
                self.assertEqual(result['mode'], expected)
                self.assertEqual(result['app_entry_method'], entry)
                self.assertFalse(result['official_available'])

    def test_unrecognized_similar_names_never_select_a_route(self):
        for name in ('FM-1 MIDI', 'fm-1', 'FM1', 'FM-1 2', 'FM-1 Midi ', 'OTA-FM-1', 'ota-fm-1'):
            with self.subTest(name=name):
                result = self.classify(midi=pair(name))
                self.assertEqual(result['mode'], 'unknown')
                self.assertIsNone(result['app_entry_method'])
                self.assertFalse(result['official_available'])

    def test_missing_half_of_midi_pair_fails_closed(self):
        for name, direction in product(('FM-1', 'FM-1 Midi', 'ota-FM-1'), ('in', 'out')):
            with self.subTest(name=name, direction=direction):
                result = self.classify(midi=[{'direction': direction, 'name': name}])
                self.assertEqual(result['mode'], 'unknown')
                self.assertFalse(result['official_available'])

    def test_duplicate_same_direction_midi_or_multiple_devices_are_ambiguous(self):
        fixtures = [{'serial': [{}, {}]}, {'disks': [{}, {}]}]
        fixtures.extend({'midi': pair(name) + [{'direction': direction, 'name': name}]}
                        for name, direction in product(('FM-1', 'FM-1 Midi', 'ota-FM-1'), ('in', 'out')))
        for fields in fixtures:
            with self.subTest(fields=fields):
                result = self.classify(**fields)
                self.assertEqual(result['mode'], 'ambiguous')
                self.assertIsNone(result['app_entry_method'])
                self.assertFalse(result['official_available'])

    def test_conflicting_serial_uboot_and_midi_families_are_ambiguous(self):
        fixtures = [{'serial': [{}], 'disks': [{}]},
                    {'midi': pair('FM-1') + pair('ota-FM-1')}]
        fixtures.extend({kind: [{}], 'midi': pair(name)}
                        for kind, name in product(('serial', 'disks'), ('FM-1', 'ota-FM-1')))
        for fields in fixtures:
            with self.subTest(fields=fields):
                result = self.classify(**fields)
                self.assertEqual(result['mode'], 'ambiguous')
                self.assertFalse(result['official_available'])

    def test_any_inventory_failure_prevents_even_known_mode_selection(self):
        for fields in ({'serial': [{}]}, {'disks': [{}]}, {'midi': pair('FM-1')}):
            with self.subTest(fields=fields):
                result = self.classify(**fields, error='Synthetic inventory failure')
                self.assertEqual(result['mode'], 'unknown')
                self.assertIsNone(result['app_entry_method'])
                self.assertFalse(result['official_available'])

    def test_malformed_inventory_metadata_fails_closed(self):
        fixtures = [(None, [], []), ([], {}, []), ([], [], 'FM-1'),
                    (['COM_fixture'], [], []), ([], ['disk'], []),
                    ([], [], [None]), ([], [], [{'direction': 'send', 'name': 'FM-1'}]),
                    ([], [], [{'direction': 'in', 'name': None}])]
        for serial, disks, midi in fixtures:
            with self.subTest(serial=serial, disks=disks, midi=midi):
                result = mode.classify_update_mode(serial, disks, midi)
                self.assertEqual(result['mode'], 'unknown')
                self.assertIsNone(result['app_entry_method'])
                self.assertFalse(result['official_available'])

    def test_unrelated_midi_endpoints_do_not_count_as_fm1_devices(self):
        result = self.classify(midi=pair('Other synthesizer'))
        self.assertEqual(result['mode'], 'disconnected')
        self.assertFalse(result['official_available'])
        result = self.classify(serial=[{}], midi=pair('Other synthesizer'))
        self.assertEqual(result['mode'], 'serial')


class NativeFunction:
    def __init__(self, invoke):
        self.invoke = invoke

    def __call__(self, *arguments):
        return self.invoke(*arguments)


class PassiveWinMM:
    """Expose only capabilities APIs; opening or sending would fail the test."""
    def __init__(self, inputs=('FM-1',), outputs=('FM-1 Midi',), fail=None, count=None):
        self.calls = []
        self.functions = {}
        for prefix, names, structure in (('midiIn', inputs, mode.MIDIINCAPSW),
                                         ('midiOut', outputs, mode.MIDIOUTCAPSW)):
            def get_count(prefix=prefix, names=names):
                self.calls.append(prefix + 'GetNumDevs')
                return len(names) if count is None else count
            def get_caps(index, pointer, size, prefix=prefix, names=names, structure=structure):
                self.calls.append(prefix + 'GetDevCapsW')
                if prefix == fail:
                    return 1
                assert size == ctypes.sizeof(structure)
                ctypes.cast(pointer, ctypes.POINTER(structure)).contents.szPname = names[index]
                return 0
            self.functions[prefix + 'GetNumDevs'] = NativeFunction(get_count)
            self.functions[prefix + 'GetDevCapsW'] = NativeFunction(get_caps)

    def __getattr__(self, name):
        if name not in self.functions:
            raise AssertionError('Device-open or sender API requested: ' + name)
        return self.functions[name]


class PassiveInventoryTests(unittest.TestCase):
    def test_only_system_dll_capabilities_queries_are_used_and_handles_are_not_exposed(self):
        api = PassiveWinMM()
        with patch.object(mode.sys, 'platform', 'win32'), \
             patch.object(mode.ctypes, 'WinDLL', return_value=api, create=True) as library:
            result = mode.enumerate_midi_endpoints()
        library.assert_called_once_with('winmm.dll', winmode=0x800)
        self.assertEqual(result, {'endpoints': [{'direction': 'in', 'name': 'FM-1'},
                                              {'direction': 'out', 'name': 'FM-1 Midi'}], 'error': None})
        self.assertEqual(api.calls, ['midiInGetNumDevs', 'midiInGetDevCapsW',
                                    'midiOutGetNumDevs', 'midiOutGetDevCapsW'])

    def test_caps_failure_discards_partial_inventory(self):
        with patch.object(mode.sys, 'platform', 'win32'), \
             patch.object(mode.ctypes, 'WinDLL', return_value=PassiveWinMM(fail='midiOut'), create=True):
            result = mode.enumerate_midi_endpoints()
        self.assertEqual(result['endpoints'], [])
        self.assertIsInstance(result['error'], str)
        self.assertEqual(mode.classify_update_mode([], [], [], result['error'])['mode'], 'unknown')

    def test_endpoint_count_is_bounded_before_any_caps_iteration(self):
        api = PassiveWinMM(count=257)
        with patch.object(mode.sys, 'platform', 'win32'), \
             patch.object(mode.ctypes, 'WinDLL', return_value=api, create=True):
            result = mode.enumerate_midi_endpoints()
        self.assertEqual(result['endpoints'], [])
        self.assertTrue(result['error'])
        self.assertEqual(api.calls, ['midiInGetNumDevs'])

    def test_missing_windows_or_dll_reports_unavailable_without_opening_anything(self):
        with patch.object(mode.sys, 'platform', 'linux'), \
             patch.object(mode.ctypes, 'WinDLL', side_effect=AssertionError('No DLL load'), create=True):
            result = mode.enumerate_midi_endpoints()
        self.assertEqual(result['endpoints'], [])
        self.assertTrue(result['error'])
        with patch.object(mode.sys, 'platform', 'win32'), \
             patch.object(mode.ctypes, 'WinDLL', side_effect=OSError('Private error'), create=True):
            result = mode.enumerate_midi_endpoints()
        self.assertEqual(result, {'endpoints': [], 'error': 'Windows MIDI capabilities enumeration failed'})


if __name__ == '__main__':
    unittest.main()
