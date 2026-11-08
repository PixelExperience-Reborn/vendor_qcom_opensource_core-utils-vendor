/* Compile original, unmodified fwk-detect/vndfwk-detect.c on the CI host.
 * This proves its two-property four-case truth table only, not Android ABI.
 */
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <cutils/properties.h>
#include "vndfwk-detect.h"

static bool sys_enhanced;
static bool odm_enhanced;
static int property_calls;
static int invalid_key_or_default;

bool property_get_bool(const char *name, bool default_value) {
    ++property_calls;
    if (default_value)
        ++invalid_key_or_default;
    if (strcmp(name, "ro.vendor.qti.va_aosp.support") == 0)
        return sys_enhanced;
    if (strcmp(name, "ro.vendor.qti.va_odm.support") == 0)
        return odm_enhanced;
    ++invalid_key_or_default;
    return default_value;
}

int main(void) {
    for (int odm = 0; odm < 2; ++odm) {
        for (int sys = 0; sys < 2; ++sys) {
            odm_enhanced = (odm != 0);
            sys_enhanced = (sys != 0);
            property_calls = 0;
            invalid_key_or_default = 0;
            int combined = getVendorEnhancedInfo();
            int individual = isRunningWithVendorEnhancedFramework();
            if (combined != (odm | (sys << 1)) ||
                individual != sys || property_calls != 3 ||
                invalid_key_or_default != 0) {
                fprintf(stderr, "Failed QTI vendor fwk detect: "
                        "odm=%d sys=%d mask=%d direct=%d calls=%d errors=%d\n",
                        odm, sys, combined, individual, property_calls,
                        invalid_key_or_default);
                return 1;
            }
        }
    }
    puts("PASS: vendor Qualcomm fwk-detector original source, four mock-property cases");
    return 0;
}
