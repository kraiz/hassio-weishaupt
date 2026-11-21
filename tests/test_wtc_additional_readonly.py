"""Regression tests for additional read-only WTC sensor definitions."""
import unittest
# Reuse the Home Assistant stubs and module loaders from existing tests.
from test_api import api
from test_sensor_device_info import sensors

ALL_SENSORS = sensors.ALL_SENSORS
POLLED_SENSORS = sensors.POLLED_SENSORS
WTC_SENSORS = sensors.WTC_SENSORS
WeishauptDeviceGroup = sensors.WeishauptDeviceGroup

build_read_vg = api.build_read_vg
parse_vg_response = api.parse_vg_response

EXPECTED = {
    "wtc_geblaesedrehzahl": (0x07, 0, 0x2540, 0, 2, None, 1),
    "wtc_pumpe_intern_elektrische_leistung": (0x09, 1, 0x261B, 2, 1, 2, 1),
    "wtc_kessel_vorlauf_rohwert": (0x07, 0, 0x2536, 0, 2, None, 1),
    "wtc_brenner_sollleistung": (0x07, 0, 0x2542, 0, 2, None, 0.01),
    "wtc_geblaese_ansteuerung": (0x07, 0, 0x257E, 0, 2, None, 0.01),
    "wtc_brennertaktsperre_rohwert": (0x07, 0, 0x250A, 0, 1, None, 1),
    "wtc_schaltdifferenz_heizbetrieb_rohwert": (0x07, 0, 0x250D, 2, 2, None, 1),
    "wtc_brennerleistung_max_heizbetrieb_rohwert": (0x07, 0, 0x2523, 2, 2, None, 1),
    "wtc_pumpenleistung_min_heizbetrieb": (0x07, 0, 0x256B, 2, 1, None, 1),
    "wtc_pumpenleistung_max_heizbetrieb": (0x07, 0, 0x256C, 2, 1, None, 1),
    "wtc_pumpenregelungsart_rohwert": (0x09, 1, 0x266A, 2, 1, None, 1),
    "wtc_vpt_max_volumenstrom_rohwert": (0x09, 1, 0x2629, 2, 2, None, 1),
}

class WtcAdditionalSensorTests(unittest.TestCase):
    def test_definitions_unique_and_polled(self):
        keys = [s.key for s in ALL_SENSORS]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(sum(s.ox == 0x2534 and s.mi == 0x07 and s.mx == 0 and s.os == 0 for s in WTC_SENSORS), 1)
        polling = {s.key for s in POLLED_SENSORS}
        self.assertTrue(set(EXPECTED) <= polling)

    def test_registers_and_scaling(self):
        sensors = {s.key: s for s in WTC_SENSORS}
        for key, fields in EXPECTED.items():
            with self.subTest(key=key):
                s = sensors[key]
                self.assertEqual((s.mi, s.mx, s.ox, s.os, s.vs, s.request_vs, s.scale), fields)
                self.assertEqual(s.group, WeishauptDeviceGroup.WTC)
                self.assertTrue(s.poll)
                self.assertIsNone(s.value_map)
                self.assertIsNone(s.entity_category)

    def test_pump_request_vs_2_response_vs_1(self):
        s = next(s for s in WTC_SENSORS if s.key == 'wtc_pumpe_intern_elektrische_leistung')
        request = build_read_vg(s.mi, s.mx, s.ox, s.os, s.request_vs or s.vs)
        self.assertEqual(request, '010901261b0200020000')
        response = parse_vg_response('020901261b020001000b')
        self.assertEqual((response['mi'], response['mx'], response['ox'], response['os'], response['vs'], response['value_int']), (9,1,0x261b,2,1,11))

    def test_known_unit_and_scale(self):
        sensors = {s.key: s for s in WTC_SENSORS}
        self.assertEqual(sensors['wtc_brenner_sollleistung'].unit, '%')
        self.assertAlmostEqual(1569 * sensors['wtc_brenner_sollleistung'].scale, 15.69)
        self.assertAlmostEqual(1042 * sensors['wtc_geblaese_ansteuerung'].scale, 10.42)
        self.assertEqual(sensors['wtc_pumpe_intern_elektrische_leistung'].unit, 'W')
        self.assertEqual(sensors['wtc_pumpenleistung_min_heizbetrieb'].unit, '%')
        for key in EXPECTED:
            if 'rohwert' in key:
                self.assertIsNone(sensors[key].unit)
                self.assertEqual(sensors[key].scale, 1)

if __name__ == '__main__':
    unittest.main()
