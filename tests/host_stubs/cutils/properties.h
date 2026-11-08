#ifndef PE_REBORN_QTI_VENDOR_TEST_PROPERTIES_H
#define PE_REBORN_QTI_VENDOR_TEST_PROPERTIES_H
#include <stdbool.h>
/* Test-only stub. Does not reflect Android property service behavior. */
bool property_get_bool(const char *name, bool default_value);
#endif
