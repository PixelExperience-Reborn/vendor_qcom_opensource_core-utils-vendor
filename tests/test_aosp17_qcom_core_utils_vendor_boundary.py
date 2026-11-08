#!/usr/bin/env python3
"""PE-Reborn stage 196: QTI vendor core-utils source/AIDL provider boundary.

Only immutable source, Soong and manifest contracts are tested. No Android17
Soong/HAL/device build is claimed. Do not import device trees or extensions.
"""
import os
from pathlib import Path
import re
import subprocess
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_COMMIT = "cbc8262034d43671f1e698efc640b01c525731e3"
ARCHIVE_TREE = "2a3c1485414055c4be45a949fbe793e1f2dc2649"
OLD_PATH = "vendor/qcom/opensource/core-utils-vendor"
OLD_NAME = "vendor_qcom_opensource_core-utils-vendor"
QSPA_MODULE = "vendor.qti.hardware.qspa-service"
QSPA_AIDL = "vendor.qti.hardware.qspa-V1-ndk"


def git(*args):
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def entry(ref, path):
    found = git("ls-tree", ref, "--", path)
    if not found:
        raise AssertionError("Git entry missing " + path)
    obj, path_back = found.split("\t", 1)
    if path_back != path:
        raise AssertionError("returned wrong Git path " + path_back)
    mode, kind, sha = obj.split()
    return (mode, kind, sha)


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def pinned_source(name):
    path = os.environ.get(name)
    if not path or not Path(path).is_file():
        raise AssertionError("missing SHA-pinned text " + name)
    return Path(path).read_text(encoding="utf-8")


class QcomCoreUtilsVendorBoundary(unittest.TestCase):
    def test_historical_vendor_caf_branch_unchanged(self):
        p = subprocess.run(
            ["git", "-C", str(ROOT), "merge-base", "--is-ancestor",
             ARCHIVE_COMMIT, "HEAD"], capture_output=True, text=True,
        )
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(git("rev-parse", ARCHIVE_COMMIT + "^{tree}"), ARCHIVE_TREE)

    def test_original_vendor_source_git_objects_immutable(self):
        expected = {
            ".gitupstream": ("100644", "blob", "75088d71e1e9e051fe4ce7f65757f62ed9295edc"),
            "cpu-core-info": ("040000", "tree", "5dd74108828814ed03784a922e9682d7cf8a1cd9"),
            "fwk-detect": ("040000", "tree", "317c1c7b6411d1304ea36efab21b929af873311c"),
            "qspaservice": ("040000", "tree", "6b2397b7f8ee4911a27e8e86bad00087a5fae268"),
        }
        for path, pin in expected.items():
            with self.subTest(path=path):
                self.assertEqual(entry("HEAD", path), pin)
                self.assertEqual(entry(ARCHIVE_COMMIT, path), pin)

    def test_exact_six_vendor_qti_soong_modules(self):
        files = ["cpu-core-info/Android.bp", "fwk-detect/Android.bp",
                 "qspaservice/Android.bp"]
        names = []
        for path in files:
            names += re.findall(r'\bname:\s*"([^"]+)"', read(path))
        self.assertEqual(names, [
            "libcpu_core_info",
            "libqti_vndfwk_detect_vendor",
            "vndfwk-test-vendor",
            "libvndfwk_detect_jni.qti_vendor",
            "vndfwk.detect_vendor",
            QSPA_MODULE,
        ])
        self.assertIn("vendor: true", read(files[0]))
        self.assertIn("vendor: true", read(files[1]))
        self.assertIn("vendor:true", read(files[2]))

    def test_real_qspa_service_is_ndk_aidl_but_provider_missing(self):
        bp = read("qspaservice/Android.bp")
        self.assertIn('"libbinder_ndk"', bp)
        self.assertIn('"' + QSPA_AIDL + '"', bp)
        self.assertIn('vintf_fragments: ["vendor.qti.qspa-service.xml"]', bp)
        self.assertIn('init_rc: ["vendor.qti.qspa-service.rc"]', bp)
        self.assertFalse(any(ROOT.rglob("*.aidl")),
                         "QSPA .aidl source must be separately provided and pinned")
        self.assertIn("#include <aidl/vendor/qti/hardware/qspa/BnQspa.h>",
                      read("qspaservice/src/Qspa.h"))
        # V1-ndk import is an unresolved source dependency from this archive
        # alone, NOT proof that the interface does not exist elsewhere.

    def test_qspa_vintf_and_binder_instance_match(self):
        root = ET.fromstring(read("qspaservice/vendor.qti.qspa-service.xml"))
        self.assertEqual(root.tag, "manifest")
        self.assertEqual(root.get("type"), "device")
        hal = root.find("hal")
        self.assertIsNotNone(hal)
        self.assertEqual(hal.get("format"), "aidl")
        self.assertEqual(hal.findtext("name"), "vendor.qti.hardware.qspa")
        self.assertEqual(hal.findtext("version"), "1")
        self.assertEqual(hal.findtext("interface/name"), "IQspa")
        self.assertEqual(hal.findtext("interface/instance"), "default")
        cpp = read("qspaservice/src/main.cpp")
        self.assertIn('Qspa::descriptor + "/default"', cpp)
        self.assertIn("AServiceManager_addService(", cpp)
        self.assertIn("ABinderProcess_setThreadPoolMaxThreadCount(8)", cpp)
        self.assertIn("ABinderProcess_joinThreadPool()", cpp)

    def test_qspa_init_is_vendor_hal_not_framework_default(self):
        rc = read("qspaservice/vendor.qti.qspa-service.rc")
        self.assertIn("service vendor.qspa-service /vendor/bin/vendor.qti.qspa-service", rc)
        self.assertIn("class hal", rc)
        self.assertIn("user system", rc)
        self.assertIn("group system", rc)
        self.assertFalse((ROOT / "frameworks").exists())
        self.assertFalse((ROOT / "build").exists())
        # Do not install optional vendor service in platform base.

    def test_qspa_cpu_topology_path_mutation_needs_review(self):
        cpp = read("qspaservice/src/Qspa.cpp")
        self.assertIn('string path1 = cpu_cluster_map_path.append("/physical_package_id")', cpp)
        self.assertIn('string path2 = cpu_cluster_map_path.append("/cluster_id")', cpp)
        # The *same string* is appended twice: path2 is path1 + /cluster_id.
        # This is a source-level bug in fallback path construction.
        self.assertIn('"/sys/devices/system/cpu/cpu" + to_string(i)', cpp)

    def test_qspa_cpu_list_parser_assumes_contiguous_decimal_range(self):
        cpp = read("qspaservice/src/Qspa.cpp")
        self.assertIn('std::regex_replace(line, std::regex("0-"), "")', cpp)
        self.assertIn("stoi(intermediate,0,16)", cpp)
        self.assertIn("getline(data, intermediate, ' ')", cpp)
        self.assertNotIn("catch (const std::invalid_argument", cpp)
        # Linux sysfs cpulists may be sparse; base16 is incorrect for CPU
        # indices represented as decimal, e.g. "10" -> 16.
        # No Android runtime test; error paths need a future targeted fix.

    def test_cpu_info_parser_is_not_general_multi_digit_safe(self):
        src = read("cpu-core-info/cpu_core_info.cpp")
        self.assertIn('#define CPU_INFO_PATH "proc/device-tree/cpus/"', src)
        self.assertIn("#define MAX_CORES 16", src)
        self.assertIn("filename.at(filename.find('@')+1) - '0'", src)
        self.assertIn("cores[core] = 1", src)
        self.assertNotIn("core >= MAX_CORES", src)
        # Relative proc path and single-character CPU-id interpretation are
        # source-level limitations. Never assume host/device topology works.

    def test_vendor_fwk_detect_duplicates_system_detector_behavior(self):
        src = read("fwk-detect/vndfwk-detect.c")
        self.assertIn('"ro.vendor.qti.va_aosp.support"', src)
        self.assertIn('"ro.vendor.qti.va_odm.support"', src)
        self.assertEqual(
            entry("HEAD", "fwk-detect/vndfwk-detect.c")[2],
            "1ff1aa70d2c4c1a0ef5d8e7950fc3a906fb9e5eb")
        system_bp = pinned_source("PE_QCOM_SYSTEM_DETECT_BP")
        vendor_bp = read("fwk-detect/Android.bp")
        self.assertIn('name: "libqti_vndfwk_detect_system"', system_bp)
        self.assertIn('name: "libqti_vndfwk_detect_vendor"', vendor_bp)
        self.assertIn("system_ext_specific: true", system_bp)
        self.assertIn("vendor: true", vendor_bp)
        # Same detector code but distinct module/partition/JNI ownership.
        # Never enable both reflexively.

    def test_aosp17_graph_does_not_include_archived_qspa_provider(self):
        root = ET.fromstring(pinned_source("PE_AOSP17_REFERENCE"))
        self.assertEqual(root.find("default").get("revision"),
                         "refs/tags/android-17.0.0_r1")
        projects = {e.get("path"): e.get("name") for e in root.iter("project")}
        self.assertEqual(projects["build/soong"], "platform/build/soong")
        self.assertEqual(projects["hardware/interfaces"], "platform/hardware/interfaces")
        self.assertEqual(projects["system/libvintf"], "platform/system/libvintf")
        self.assertNotIn(OLD_PATH, projects)
        self.assertNotIn(OLD_NAME, projects.values())

    def test_active_manifest_stays_clean_and_no_device_tree_changed(self):
        root = ET.fromstring(pinned_source("PE_AOSP17_DEFAULT"))
        self.assertEqual(
            [e.get("name") for e in root.findall("include")],
            ["aosp17_pe_p2_kernel_configs.xml"],
        )
        self.assertFalse(any(e.get("path") == OLD_PATH or
                             e.get("name") == OLD_NAME
                             for e in root.iter("project")))
        for path in ("device.mk", "BoardConfig.mk", "AndroidProducts.mk",
                     "init.mondrian.rc", "aidl", "frameworks", "device"):
            self.assertFalse((ROOT / path).exists())

if __name__ == "__main__":
    unittest.main(verbosity=2)
