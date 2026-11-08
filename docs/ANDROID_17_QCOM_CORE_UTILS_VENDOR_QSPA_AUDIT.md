# Stage 196 — Qualcomm core-utils-vendor, QSPA and topology audit

**Date:** 2026-11-08. **Scope:** PixelExperience-Reborn on Google AOSP android-17.0.0_r1. Current work is building a complete independent platform/source graph, not implementing SM8475 trees or adding optional functions.

## Historical Qualcomm source and inheritance

- Repository: https://github.com/PixelExperience-Reborn/vendor_qcom_opensource_core-utils-vendor
- Historical seventeen HEAD cbc8262034d43671f1e698efc640b01c525731e3 (2024-01-04); root tree 2a3c1485414055c4be45a949fbe793e1f2dc2649. Historical Qualcomm tag LA.VENDOR.13.2.0.r1-21400-KAILUA.0. Last change configured the QSPA NDK Binder maximum threadpool count to eight.
- Original source subtrees: cpu-core-info 5dd74108828814ed03784a922e9682d7cf8a1cd9; fwk-detect 317c1c7b6411d1304ea36efab21b929af873311c; qspaservice 6b2397b7f8ee4911a27e8e86bad00087a5fae268. All original Git objects preserved.
- Six declared Soong modules: libcpu_core_info, libqti_vndfwk_detect_vendor, vndfwk-test-vendor, libvndfwk_detect_jni.qti_vendor, vndfwk.detect_vendor, and vendor.qti.qspa-service.

## Directly verified build/API dependencies

1. libcpu_core_info is a vendor C++ library that reads CPU topology from proc/device-tree and does not define a platform or device product.
2. The vendor fwk-detect component reads ro.vendor.qti.va_aosp.support and ro.vendor.qti.va_odm.support and defaults both to false. Its source C blob equals the one from the separately audited system_ext core-utils-sys, but their module names and partitions differ. Avoid dual installation without a real consumer.
3. QSPA is a genuine Qualcomm NDK Binder HAL service. Its Soong module depends on libbinder_ndk and vendor.qti.hardware.qspa-V1-ndk, registers vendor.qti.hardware.qspa.IQspa/default, and installs an init rc and vendor VINTF AIDL v1 fragment. However the QSPA AIDL interface declaration or generated module provider is **not present in this checkout**. Do not assume the provider is unavailable everywhere: it may exist in an appropriately pinned separate Qualcomm interface project.
4. AOSP17 official build/soong, hardware/interfaces and system/libvintf remain selected. Do NOT blindly import Qualcomm vendor services into the platform build. Modern Stable AIDL/NDK Binder is a legitimate technical direction only with verified frozen versions, providers, VINTF/FCM/SELinux and a real product requirement.

## Historical source risks, not tested device failures

- qspaservice/src/Qspa.cpp constructs path1 by appending /physical_package_id to a string, then constructs path2 by appending /cluster_id to that **same** mutated string. The resulting fallback path is wrong.
- QSPA extracts the total CPU count by stripping a literal 0- prefix. It cannot reliably parse sparse CPU-list ranges. Its related-CPU conversion uses stoi(..., 16), even though the sysfs CPU indices are normally decimal, and the code lacks exception handling for malformed numeric data.
- cpu-core-info/cpu_core_info.cpp reads CPU_INFO_PATH proc/device-tree/cpus/ without an absolute leading slash; it takes only the first character after @ for the CPU index and uses a fixed MAX_CORES 16 array without a proven bounds check.
- These are directly observed source-level limitations. No Android17 runtime, device QSPA service or kernel behavior was tested. Do not modify the historic HAL or manufacture working AIDL interface files to silence a build error.

## Implemented test and manifest gates

- 12 Git/source-only checks preserve original source trees, verify complete Soong module names, QSPA AIDL provider gap, VINTF fragment and Binder registration, init service, CPU topology issues, vendor-vs-system fwk-detector ownership, independent Google AOSP17 source graph and active default.xml.
- A host Clang C test compiles and runs the original Qualcomm fwk-detect/vndfwk-detect.c with a test-only cutils/properties.h mock. Four ODM/system truth-table combinations must pass. This proves only isolated C logic behavior, not Android compatibility.
- GitHub Actions pins a specific manifest commit and the system-ext core-utils-sys counterpart Android.bp at immutable SHA. It validates 135 repository paths and all manifest tests; no LF52406 or LineageOS device tree is fetched.
- Companion Manifest Draft PR #2: exclude this specific old repo path and known aliases from active/candidate source graphs until a real consumer and closed AIDL provider graph are established; add 2 negative tests and update matrix stage 196. Historic seventeen, frozen HAL code and AOSP17 default.xml are unchanged.

## Future qualification outside stage 196

A real dependency on QSPA must be demonstrated, together with a matched frozen AIDL interface, corrected CPU parsing and topology paths, proper C++ module linking, SELinux/sysfs access, VINTF/FCM/partition ownership and actual target compilation. These are later hardware-qualification steps. Right now the platform must first pass full repo sync and Soong/Make compilation using reviewed AOSP17 sources.

**Not performed:** complete AOSP17 sync, Android17 ROM/Soong build, QSPA AIDL build, device tree creation, kernel build, device flash or boot. CI host testing does not prove any of these.
